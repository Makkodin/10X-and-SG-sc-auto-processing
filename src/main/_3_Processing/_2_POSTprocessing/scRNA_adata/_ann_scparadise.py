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
from main._3_Processing._2_POSTprocessing.scRNA_adata.create_adata_SG import create_anndata_from_mtx
from main._1_Config.main_config import  WORKDIR


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
    work_run    =   WORKDIR,
):
    logging.basicConfig(level=logging.INFO)
    logger  =   logging.getLogger(__name__)
    
    try:
        logger.info(f"🧬[3.2.sc Annotation] Loading data from {input_file}")
        if input_file.endswith('.h5ad'):
            adata   =   sc.read_h5ad(input_file)
        else:
            adata   =   sc.read_10x_h5(input_file)
        logger.info(f"🧬[3.2.sc Annotation] Loaded {adata.n_obs} cells and {adata.n_vars} genes")
        logger.info("🧬[3.2.sc Annotation] Preprocessing data...")
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
        df              =   scparadise.scadam.available_models()
        df_temp_org     =   df[df['Tissue/Model name'].str.contains(f'{species}_', case=False)]
        df_temp_tiss    =   df_temp_org[(df_temp_org['Tissue/Model name'].str.contains(tissue_type.split(';')[0], case=False))]
        df_temp_susp    =   df_temp_tiss[(df_temp_tiss['Suspension'].str.contains(tissue_type.split(';')[1], case=False))]
        if len(df_temp_susp) != 0 :
            MODEL   =   df_temp_susp.iloc[0]['Tissue/Model name']
            if len(glob(f'{work_run}/1.Data/Models/{MODEL}_scAdam')) == 0:
                scparadise.scadam.download_model(MODEL, 
                                                 save_path  =   f'{work_run}/1.Data/Models')
            logger.info("🧬[3.2.sc Annotation] Initializing scParadise...")
            scparadise_buffer = StringIO()
            logger.info("🧬[3.2.sc Annotation] Running annotation...")
            original_stdout = sys.stdout
            try:
                sys.stdout = scparadise_buffer
                adata = scparadise.scadam.predict(adata,
                                                  path_model=f'{work_run}/1.Data/Models/{MODEL}_scAdam')
            finally:
                sys.stdout = original_stdout
            scparadise_output = scparadise_buffer.getvalue()
            if scparadise_output.strip():
                logger.info(f"🧬[3.2.sc scParadise Output]:\n{scparadise_output}")
            if output_file:
                logger.info(f"🧬[3.2.sc Annotation] Saving results to {output_file}")
                adata.write(output_file.replace('.h5ad', f'_{MODEL}.h5ad'))
            logger.info("🧬[3.2.sc Annotation] Annotation completed successfully!")
            cell_types = adata.obs['pred_celltype_l2'].value_counts()
            logger.info("\n🧬[3.2.sc Annotation] Cell type distribution:")
            for cell_type, count in cell_types.items():
                logger.info(f"[3.2.sc Annotation] {cell_type}: {count} cells")

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
                    legend_loc          =   'on data',#,
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
            print("❌[3.2.sc Annotation] Error find Model")
            return None
        
    except Exception as e:
        logger.error(f"❌[3.2.sc Annotation] Error during annotation: {str(e)}")
        raise

def process_annotation(sample_processed:dict, 
                       work_dir:str =   WORKDIR
    ) -> Tuple[str, bool, str]:
    sample_id   =   sample_processed['Sample_ID']
    
    try:
        if sample_processed['Reference name'] in ['GRCh38', 'MM10']:
            flowcell        =   sample_processed['Flowcell']
            input_file      =   None
            temp_h5ad_path  =   None

            data_ann_path   =   sample_processed['Path local annotation png'].rsplit('/', maxsplit=1)[0] # /mnt/raid0/ofateev/projects/SC_auto/2.Results/SG/scRNA/240411_A01022_0750_AHNFHFDRXY/962000685201_h/step3/filtered_feature_bc_matrix
            
            # Check exist results
            img_results =   []
            if sample_processed['SeqType'] == 'SC_TENX_RNA':
                img_results =   glob(sample_processed['Path local annotation png'])
            if sample_processed['SeqType'] == 'SC_SeekGene_RNA':
                img_results =   glob(sample_processed['Path local annotation png'])      
            if sample_processed['SeqType'] == 'SC_SeekGene_VDJ' and sample_processed['VDJ type'] == '5':
                img_results =   glob(sample_processed['Path local annotation png'])
            
            if img_results:
                message     =   f"Found PNG file: {img_results[0]}"
                return sample_id, True, message
            
            # Processing if not exist
            if sample_processed['SeqType'] == 'SC_TENX_RNA':
                result_pattern  =   f"{data_ann_path}/filtered_feature_bc_matrix.h5"
                result_files    =   glob(result_pattern)
                if result_files:
                    input_file  =   result_files[0]
                    message     =   f"📁[3.2.sc Annotation] Found 10x h5 file: {input_file}"
                else:
                    message     =   f"⚠️[3.2.sc Annotation] No 10x h5 file found for {sample_id}"
                    return sample_id, False, message       
                
            
            elif sample_processed['SeqType'] == 'SC_SeekGene_RNA' or sample_processed['SeqType'] == 'SC_SeekGene_VDJ':
                mtx_pattern     =   f"{data_ann_path}/"
                mtx_dirs        =   glob(mtx_pattern)
                if not mtx_dirs:
                    message     =   f"⚠️[3.2.sc Annotation] No MTX directory found for {sample_id}"
                    return sample_id, False, message
                mtx_dir     =   mtx_dirs[0]
                if not os.path.isdir(mtx_dir):
                    message =   f"⚠️[3.2.sc Annotation] Path is not a directory: {mtx_dir}"
                    return sample_id, False, message
                required_files  =   ['matrix.mtx.gz', 'barcodes.tsv.gz', 'features.tsv.gz']
                missing_files   =   []
                for f in required_files:
                    file_path = os.path.join(mtx_dir, f)
                    if not os.path.exists(file_path):
                        missing_files.append(f)
                if missing_files:
                    message     =   f"⚠️[3.2.sc Annotation] Missing files in {mtx_dir}: {missing_files}"
                    print(f"❌[3.2.sc Annotation] Debug: Files in {mtx_dir}: {os.listdir(mtx_dir)}")
                    return sample_id, False, message
                temp_h5ad_path  =   os.path.join(mtx_dir, 'temp_adata.h5ad')
                message         =   f"🔨[3.2.sc Annotation] Creating AnnData from MTX files in {mtx_dir}"
                try:
                    adata       =   create_anndata_from_mtx(mtx_dir, temp_h5ad_path)
                    input_file  =   temp_h5ad_path
                    message += f"\n✅[3.2.sc Annotation] Created AnnData with {adata.n_obs} cells and {adata.n_vars} genes"
                except Exception as e:
                    message += f"\n❌[3.2.sc Annotation] Failed to create AnnData: {str(e)}"
                    return sample_id, False, message
                
            if not input_file:
                message     =   f"⚠️[3.2.sc Annotation] No input file found for {sample_id}"
                return sample_id, False, message
            
            if input_file.endswith('.h5ad'):
                output_file     =   input_file.replace('.h5ad', '_annotated_scParadise.h5ad')
                if 'temp_adata' in  output_file:
                    output_file =   output_file.replace('temp_adata', 'filtered_feature_bc_matrix')
            elif input_file.endswith('.h5'):
                output_file = input_file.replace('.h5', '_annotated_scParadise.h5ad')
            else:
                output_file = input_file + '_annotated_scParadise.h5ad'

            message             +=  f"\n🧬[3.2.sc Annotation] Annotating {sample_id} with scParadise from {input_file} to {output_file}"
            log_buffer          =   StringIO()
            log_handler         =   logging.StreamHandler(log_buffer)
            log_handler.setLevel(logging.INFO)
            original_handlers   =   logging.getLogger().handlers[:]
            try:
                logging.getLogger().addHandler(log_handler)
                annotate_single_sample_scparadise(
                    input_file      =   input_file,
                    output_file     =   output_file,
                    species         =   sample_processed['Organism'].lower(),
                    tissue_type     =   sample_processed['Tissue'],
                    batch_key       =   None,
                    use_gpu         =   False,
                    work_run        =   work_dir
                )
                captured_logs = log_buffer.getvalue()
                if captured_logs:
                    message += f"\n{captured_logs}"
                success_msg = f"✅[3.2.sc Annotation] Successfully annotated {sample_id}"
                message += f"\n{success_msg}"
                return sample_id, True, message
            except Exception as e:
                error_msg = f"❌[3.2.sc Annotation] Error during annotation: {str(e)}"
                message += f"\n{error_msg}"
                return sample_id, False, message
            finally:
                logging.getLogger().handlers = original_handlers
                log_handler.close()     
        else: 
            return sample_id, False, f"Skipping annotation for organism: {sample_processed['Organism']}"
    except Exception as e:
        error_msg = f"❌[3.2.sc Annotation] Error annotating {sample_id}: {str(e)}"
        error_details = f"Error details: {traceback.format_exc()}"
        if 'temp_h5ad_path' in locals() and temp_h5ad_path and os.path.exists(temp_h5ad_path):
            try:
                os.remove(temp_h5ad_path)
                error_msg += "\n🧹[3.2.sc Annotation] Cleaned up temporary file after error"
            except:
                pass
        return sample_id, False, f"{error_msg}\n{error_details}"