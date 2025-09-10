import scanpy as sc
import warnings
from glob import glob
warnings.simplefilter('ignore')
import scparadise
import matplotlib.pyplot as plt
import sys
import os
import traceback
from glob import glob
import logging
from io import StringIO

import logging
from typing import Dict, Any, Tuple
from main._1_PATHs.referens import RefsType
from main._1_PATHs.tools import ToolsType
from main._1_PATHs.results import ResultsType
from main._3_Data.postprocessing.create_adata_SG import create_anndata_from_mtx

def prepare_directories(
    seq_type: str,
    work_ref: str,
    work_tools: str,
    work_run: str,
    results: ResultsType,
    ref: RefsType,
    tool: ToolsType,
    organism: str
) -> Dict[str, str]:
    """
    Prepares necessary directory paths based on sequencing type and configuration.

    :param seq_type		: Type of sequencing (e.g., SC_TENX_Visium_FFPE).
    :param work_ref		: Path for reference files.
    :param work_tools	: Path for tools.
    :param work_run		: Path for running jobs.
    :param results		: ResultsType instance containing output path configurations.
    :param ref			: RefsType instance with reference genome info.
    :param tool			: ToolsType instance with tool configuration.
    :param organism		: Organism name used in reference selection.

    :return				: Dictionary of prepared paths.
    """
    res_dir_all         =   f"{work_ref}/{ref[seq_type]._get_params()[organism]['ref']}"
    result_dir_all      =   f"{work_run}/{results[seq_type]._get_params()['local']}"
    data_dir_all        =   f"{work_run}/{results[seq_type]._get_params()['fastq']}"
    toolpath_all        =   f"{work_tools}/{tool[seq_type]._get_params()}"
    ceph_res            =   f"{results[seq_type]._get_params()['ceph']}"

    return {
        "res_dir_all"   :   res_dir_all,
        "result_dir_all":   result_dir_all,
        "data_dir_all"  :   data_dir_all,
        "toolpath_all"  :   toolpath_all,
        "ceph_res"      :   ceph_res,
    }

def annotate_single_sample_scparadise(
    input_file, 
    output_file =   None,
    species     =   "human",
    tissue_type =   None,
    batch_key   =   None,
    min_genes   =   200,
    min_cells   =   3,
    max_genes   =   5000,
    max_cells   =   20000,
    n_top_genes =   3000,
    n_pcs       =   20,
    resolution  =   1.0,
    use_gpu     =   False,
    work_run    =   None,
):
    logging.basicConfig(level=logging.INFO)
    logger  =   logging.getLogger(__name__)
    
    try:
        logger.info(f"🧬[Annotation] Loading data from {input_file}")

        # Read ADATA
        if input_file.endswith('.h5ad'):
            adata   =   sc.read_h5ad(input_file)
        else:
            adata   =   sc.read_10x_h5(input_file)
            
        logger.info(f"🧬[Annotation] Loaded {adata.n_obs} cells and {adata.n_vars} genes")
        logger.info("🧬[Annotation] Preprocessing data...")

        # Filter ADATA
        # QC
        adata.var["mt"]     =   adata.var_names.str.startswith("MT-")
        adata.var["ribo"]   =   adata.var_names.str.startswith(("RPS", "RPL"))
        adata.var["hb"]     =   adata.var_names.str.contains("^HB[^(P)]")
        sc.pp.calculate_qc_metrics(adata, 
                                   qc_vars  =   ["mt", "ribo", "hb"], 
                                   inplace  =   True, 
                                   log1p    =   True)
        sc.pp.filter_cells(adata, 
                           min_genes    =   min_genes)
        sc.pp.filter_genes(adata, 
                           min_cells    =   min_cells)
        sc.pp.scrublet(adata)
        adata   =   adata[adata.obs['predicted_doublet'] == False]
        sc.pp.filter_cells(adata, 
                           max_genes    =   max_genes)
        sc.pp.filter_cells(adata, 
                           max_counts   =   max_cells)
        adata   =   adata[adata.obs['pct_counts_mt'] < 15]

        # Normalization, HVG, neighbors, PCA, UMAP
        sc.pp.normalize_total(adata,
                              target_sum=   1e4)
        sc.pp.log1p(adata)
        adata.raw   =   adata
        sc.pp.highly_variable_genes(adata, 
                                    n_top_genes =   n_top_genes)
        sc.tl.pca(adata)
        sc.pp.neighbors(adata, 
                        n_neighbors =   10, 
                        n_pcs       =   n_pcs)
        sc.tl.umap(adata)    

        # Available models 
        df              =   scparadise.scadam.available_models()
        df_temp_org     =   df[df['Tissue/Model name'].str.contains(f'{species}_', case=False)]
        df_temp_tiss    =   df_temp_org[(df_temp_org['Tissue/Model name'].str.contains(tissue_type.split(';')[0], case=False))]
        df_temp_susp    =   df_temp_tiss[(df_temp_tiss['Suspension'].str.contains(tissue_type.split(';')[1], case=False))]

        # Load Model
        if len(df_temp_susp) != 0 :
            MODEL   =   df_temp_susp.iloc[0]['Tissue/Model name']
            if len(glob(f'{work_run}/1.Data/Models/{MODEL}_scAdam')) == 0:
                scparadise.scadam.download_model(MODEL, 
                                                 save_path  =   f'{work_run}/1.Data/Models')
            logger.info("🧬[Annotation] Initializing scParadise...")

            # Create a string buffer to capture scParadise output
            scparadise_buffer = StringIO()
            # Run cell type annotation with output redirected to buffer
            logger.info("🧬[Annotation] Running annotation...")

            # Redirect stdout temporarily to capture scParadise output
            original_stdout = sys.stdout
            try:
                sys.stdout = scparadise_buffer
                adata = scparadise.scadam.predict(adata,
                                                  path_model=f'{work_run}/1.Data/Models/{MODEL}_scAdam')
            finally:
                sys.stdout = original_stdout

            # Log the captured scParadise output
            scparadise_output = scparadise_buffer.getvalue()
            if scparadise_output.strip():
                logger.info(f"🧬[scParadise Output]:\n{scparadise_output}")

            # Save results if output file is specified
            if output_file:
                logger.info(f"🧬[Annotation] Saving results to {output_file}")
                adata.write(output_file.replace('.h5ad', f'_{MODEL}.h5ad'))

            logger.info("🧬[Annotation] Annotation completed successfully!")

            # Print cell type distribution statistics
            cell_types = adata.obs['pred_celltype_l2'].value_counts()
            logger.info("\n🧬[Annotation] Cell type distribution:")
            for cell_type, count in cell_types.items():
                logger.info(f"{cell_type}: {count} cells")

            sc.pl.embedding(adata,
                    color=[
                        'pred_celltype_l1',
                        'prob_celltype_l1',
                        'pred_celltype_l2',
                        'prob_celltype_l2',
                        'pred_celltype_l3',
                        'prob_celltype_l3'
                    ],
                    basis               =   'X_umap',
                    frameon             =   False,
                    add_outline         =   True,
                    legend_loc          =   'upper right',#'on data',
                    legend_fontsize     =   7,
                    legend_fontoutline  =   1,
                    show                =   False,
                    ncols               =   2,
                    wspace              =   0,
                    hspace              =   0.1)
            plt.savefig(output_file.replace('.h5ad', f'_{MODEL}.png'),
                bbox_inches='tight',
                dpi=300)
            plt.close()
        
            return adata
        else: 
            print("❌[Annotation] Error find Model")
            return None
        
    except Exception as e:
        logger.error(f"❌[Annotation] Error during annotation: {str(e)}")
        raise

def process_annotation(sample_info: Dict[str, Any], 
                       work_ref: str, 
                       work_tools: str, 
                       work_run: str, 
                       results: ResultsType, 
                       ref: RefsType, 
                       tool: ToolsType,
                       VDJ_key      = False
    ) -> Tuple[str, bool, str]:
    """
    :param sample_info: row info by sample
    :return: (sample_id, success, message)
    """
    sample_id   =   sample_info['sample_id']
    try:
        if sample_info['organism'] in ['GRCh38', 'MM10']:
            flowcell    =   sample_info['flowcell']
            dirs        = prepare_directories(
                                seq_type    =   sample_info['seq_type'], 
                                work_ref    =   work_ref, 
                                work_tools  =   work_tools, 
                                work_run    =   work_run, 
                                results     =   results, 
                                ref         =   ref, 
                                tool        =   tool, 
                                organism    =   sample_info['organism']
            )
            
            input_file = None
            temp_h5ad_path = None
            # Annotation for 10X
            if sample_info['seq_type'] == 'SC_TENX_RNA':
                result_pattern = f"{dirs['result_dir_all']}/{flowcell}/{sample_id}*/outs/filtered_feature_bc_matrix.h5"
                result_files = glob(result_pattern)
                if result_files:
                    input_file = result_files[0]
                    message = f"📁[Annotation] Found 10x h5 file: {input_file}"
                else:
                    message = f"⚠️[Annotation] No 10x h5 file found for {sample_id}"
                    return sample_id, False, message

            # Annotation for SG     
                 
            elif sample_info['seq_type'] == 'SC_SeekGene_RNA':
                
                mtx_dir_pattern     =   f"{dirs['result_dir_all']}/{flowcell}/{sample_id}*/step3/filtered_feature_bc_matrix/"
                if VDJ_key == True:
                    mtx_dir_pattern =   mtx_dir_pattern.replace('SG/scRNA', 'SG/scVDJ')
                mtx_dirs            =   glob(mtx_dir_pattern)
               
                if mtx_dirs and os.path.isdir(mtx_dirs[0]):
                    mtx_dir         =   mtx_dirs[0]
                    required_files  =   ['matrix.mtx.gz', 'barcodes.tsv.gz', 'features.tsv.gz']
                    missing_files   =   [f for f in required_files if not os.path.exists(f"{mtx_dir}/{f}")]
            
                    if missing_files:
                        message     =   f"⚠️[Annotation] Missing files in {mtx_dir}: {missing_files}"
                        return sample_id, False, message
                    
                    temp_h5ad_path  =   f"{mtx_dir}temp_adata.h5ad"
                    message         =   f"🔨[Annotation] Creating AnnData from MTX files in {mtx_dir}"
                    
                    adata           =   create_anndata_from_mtx(mtx_dir, temp_h5ad_path)
                    input_file      =   temp_h5ad_path
                    message         +=  f"\n✅[Annotation] Created AnnData with {adata.n_obs} cells and {adata.n_vars} genes"
                else:
                    message         =   f"⚠️[Annotation] No MTX directory found for {sample_id}"
                    return sample_id, False, message
            

            if input_file.endswith('.h5ad'):
                output_file     =   input_file.replace('.h5ad', '_annotated_scParadise.h5ad')\
                                                .replace('temp_adata', 'filtered_feature_bc_matrix')
            elif input_file.endswith('.h5'):
                output_file     =   input_file.replace('.h5', '_annotated_scParadise.h5ad')\
                                                .replace('temp_adata', 'filtered_feature_bc_matrix')
            else:
                output_file     =   input_file + '_annotated_scParadise.h5ad'
            
            # Run Annotation scParadise
            message += f"\n🧬[Annotation] Annotating {sample_id} with scParadise from {input_file} to {output_file}"
            
            log_buffer          =   StringIO()
            log_handler         =   logging.StreamHandler(log_buffer)
            log_handler.setLevel(logging.INFO)
            original_handlers   =   logging.getLogger().handlers[:]
            
            try:
                logging.getLogger().addHandler(log_handler)
                annotate_single_sample_scparadise(
                    input_file      =   input_file,
                    output_file     =   output_file,
                    species         =   "human" if sample_info['organism_name'].lower() in ['human', 'hg38', 'hg19'] else "mouse",
                    tissue_type     =   sample_info['tissue'],
                    batch_key       =   None,
                    use_gpu         =   False,
                    work_run        =   work_run
                )

                captured_logs = log_buffer.getvalue()
                if captured_logs:
                    message += f"\n{captured_logs}"
                
                if temp_h5ad_path and os.path.exists(temp_h5ad_path):
                    os.remove(temp_h5ad_path)
                    message += f"\n🧹[Annotation] Cleaned up temporary file: {temp_h5ad_path}"

                success_msg = f"✅[Annotation] Successfully annotated {sample_id}"
                message += f"\n{success_msg}"
                
                return sample_id, True, message

            finally:
                logging.getLogger().handlers = original_handlers
                log_handler.close()
        else: 
            return sample_id, False, f"Skipping annotation for organism: {sample_info['organism']}"
            
    except Exception as e:
        error_msg = f"❌[Annotation] Error annotating {sample_id}: {str(e)}"
        error_details = f"Error details: {traceback.format_exc()}"
        
        if 'temp_h5ad_path' in locals() and temp_h5ad_path and os.path.exists(temp_h5ad_path):
            try:
                os.remove(temp_h5ad_path)
                error_msg += "\n🧹[Annotation] Cleaned up temporary file after error"
            except:
                pass
                
        return sample_id, False, f"{error_msg}\n{error_details}"