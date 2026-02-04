from main._1_PATHs.results import ResultsType
from main._1_PATHs.tools import ToolsType
from glob import glob
import pandas as pd
import os
import shutil
import time
import subprocess
from typing import Dict, List, Any


def collect_and_save_statistics(samples_parse_df: pd.DataFrame, sum_path: str, flowcell: str) -> None:
    """
    Collects statistics from all samples and saves to a summary CSV file.
    
    :param samples_parse_df: DataFrame with sample information including stat paths
    :param sum_path: Path to the summary directory
    :param flowcell: Flowcell identifier for filename
    """
    # Define column mappings for each sequence type
    COLUMN_MAPPINGS: Dict[str, List[str]] = {
        'SC_TENX_RNA': [
            'estimated number of cells', 'mean reads per cell', 'median genes per cell',
            'number of reads', 'reads mapped confidently to genome', 'total genes detected',
            'median umi counts per cell'
        ],
        'SC_TENX_ATAC': [
            'estimated number of cells', 'mean raw read pairs per cell',
            'median high-quality fragments per cell',
            'fraction of high-quality fragments overlapping peaks',
            'sequenced read pairs', 'number of peaks'
        ],
        'SC_TENX_Visium_FFPE': [
            'number of spots under tissue', 'mean reads per spot',
            'median genes per spot', 'number of reads',
            'reads mapped confidently to probe set', 'genes detected', 'median umi counts per spot'
        ],
        'SC_SeekGene_RNA': [
            'estimated_number_of_cells', 'mean_reads_per_cell',
            'median_genes_per_cell', 'number_of_reads',
            'reads_mapped_confidently_to_genome', 'total_genes_detected', 'median_umi_counts_per_cell'
        ],
        'SC_SeekGene_FullRNA': [
            'estimated_number_of_cells', 'mean_reads_per_cell',
            'median_genes_per_cell', 'number_of_reads',
            'reads_mapped_confidently_to_genome', 'total_genes_detected','median_umi_counts_per_cell'
        ],
        'SC_SeekGene_VDJ': [
            'estimated number of cells', 'mean read pairs per cell',
            'number of cells with productive v-j spanning pair', 'number of read pairs',
            'reads mapped to any v(d)j gene', 'reads mapped to tra','reads mapped to trb',
       		'median tra umis per cell','median trb umis per cell','q30 bases in umi'
        ]
    }

    def process_combined_rna_vdj(sample_dir: str, stats_row: Dict[str, Any]) -> None:
        """Process combined RNA+VDJ statistics"""
        # Process RNA statistics
        
        stat_path = glob(f"{sample_dir}/*_summary.csv")
        if stat_path and os.path.exists(stat_path[0]) and 'outs/metrics_summary.csv' not in stat_path[0]:
            try:
                df_stat = pd.read_csv(stat_path[0])
                df_stat.columns =   [x.lower() for x in df_stat.columns]
                if not df_stat.empty:
                    for col in COLUMN_MAPPINGS['SC_SeekGene_RNA']:
                        stats_row[f"RNA_{col}"] = df_stat[col].iloc[0] if col in df_stat.columns else 'N/A'
                        
            except Exception as e:
                print(f"❌ Error reading RNA stats: {e}")
                for col in COLUMN_MAPPINGS['SC_SeekGene_RNA']:
                    stats_row[f"RNA_{col}"] = 'ERROR'

        if stat_path and os.path.exists(stat_path[0]) and 'outs/metrics_summary.csv' in stat_path[0]:
            try:
                df_stat = pd.read_csv(stat_path[0])
                df_stat.columns =   [x.lower() for x in df_stat.columns]
                if not df_stat.empty:
                    for col in COLUMN_MAPPINGS['SC_SeekGene_VDJ']:
                        stats_row[f"VDJ_{col}"] = df_stat[col].iloc[0] if col in df_stat.columns else 'N/A'
            except Exception as e:
                print(f"❌ Error reading VDJ stats: {e}")
                for col in COLUMN_MAPPINGS['SC_SeekGene_VDJ']:
                    stats_row[f"VDJ_{col}"] = 'ERROR'

    def process_single_stat_file(stat_path: str, seq_type: str, stats_row: Dict[str, Any]) -> None:
        """Process single statistics file"""
        try:
            if not os.path.exists(stat_path):
                raise FileNotFoundError(f"Statistics file not found: {stat_path}")
            
            df_stat = pd.read_csv(stat_path)
            df_stat.columns =   [x.lower() for x in df_stat.columns]
            if df_stat.empty:
                return
            columns = COLUMN_MAPPINGS.get(seq_type, [])

            for col in columns:
                stats_row[col] = df_stat[col].iloc[0] if col in df_stat.columns else 'N/A'
                
        except Exception as e:
            print(f"❌ Error processing stat file {stat_path}: {e}")
            for col in COLUMN_MAPPINGS.get(seq_type, []):
                stats_row[col] = 'ERROR'

    all_stats = []
    processed_count = 0
    error_count = 0

    for _, row in samples_parse_df.iterrows():
        sample_id   =   row['Sample_ID']
        seq_type    =   row['SEQtype']
        stat_path   =   row['Stat_path']
        
        stats_row = {'sample_id':   sample_id, 
                     'seq_type' :   seq_type}
        
        try:
            # Check if statistics file is valid
            if pd.isna(stat_path) or stat_path == 'Error' or not os.path.exists(stat_path):
                print(f"⚠️ No statistics file for sample: {sample_id}")
                # Add N/A for all expected columns
                if seq_type == 'SC_SeekGene_RNA|SC_SeekGene_VDJ':
                    for col in COLUMN_MAPPINGS['SC_SeekGene_RNA']:
                        stats_row[f"RNA_{col}"] = 'N/A'
                    for col in COLUMN_MAPPINGS['SC_SeekGene_VDJ']:
                        stats_row[f"VDJ_{col}"] = 'N/A'
                else:
                    for col in COLUMN_MAPPINGS.get(seq_type, []):
                        stats_row[col] = 'N/A'
            else:
                # Process statistics based on sequence type
                if seq_type == 'SC_SeekGene_RNA|SC_SeekGene_VDJ':
                    sample_dir = os.path.dirname(stat_path)
                    process_combined_rna_vdj(sample_dir, stats_row)
                else:
                    process_single_stat_file(stat_path, seq_type, stats_row)
                
                processed_count += 1
            
            all_stats.append(stats_row)
            
        except Exception as e:
            print(f"❌ Error processing {sample_id}: {e}")
            stats_row['error'] = str(e)
            all_stats.append(stats_row)
            error_count += 1

    # Save results
    if all_stats:
        summary_df  = pd.DataFrame(all_stats)
        if 'SC_SeekGene_RNA|SC_SeekGene_VDJ' in samples_parse_df['SEQtype'].unique():
            summary_df  =   summary_df.sort_values('RNA_estimated_number_of_cells', ascending=False)
        output_path = os.path.join(sum_path, f"{flowcell}_statistics_summary.csv")
        summary_df.to_csv(output_path, index=False, encoding='utf-8')
        
        print(f"✅ Statistics summary saved to: {'2.Results' + output_path.split('/2.Results')[-1]}")
        print(f"📊 Processed {processed_count} samples successfully, {error_count} with errors")
        print(f"📋 Total samples: {len(summary_df)}")
    else:
        print("⚠️ No statistics collected")