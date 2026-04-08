from    typing import   Dict, List
import  pandas as       pd
import  os


def collect_and_save_statistics_sample(sample_processed: dict, 
                                stat_full_path: str
                                ) -> dict:
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
            'reads_mapped_confidently_to_genome', 'total_genes_detected', 'median_umi_counts_per_cell'
        ],
        'SC_SeekGene_VDJ': [
            'estimated number of cells', 'mean read pairs per cell',
            'number of cells with productive v-j spanning pair', 'number of read pairs',
            'reads mapped to any v(d)j gene', 'reads mapped to tra', 'reads mapped to trb',
            'median tra umis per cell', 'median trb umis per cell', 'q30 bases in umi'
        ],
        'SC_TENX_Multiome': [
            'estimated number of cells',
            'gex fraction of transcriptomic reads in cells', 'gex mean raw reads per cell', 'gex median genes per cell',
            'gex median umi counts per cell', 'gex reads mapped confidently to genome', 'gex total genes detected',
            'atac mean raw read pairs per cell', 'atac median high-quality fragments per cell',
            'atac fraction of high-quality fragments overlapping peaks', 'atac sequenced read pairs', 'atac number of peaks'
        ],
        'SC_SeekGene_Multiome': [
            'estimated_number_of_cells',
            'gex_fraction_of_reads_in_cells', 'gex_mean_raw_reads_per_cell', 'gex_median_genes_per_cell',
            'gex_median_umi_counts_per_cell', 'gex_reads_mapped_confidently_to_genome', 'gex_total_genes_detected',
            'atac_mean_raw_read_pairs_per_cell', 'atac_median_high-quality_fragments_per_cell',
            'atac_fraction_of_genome_in_peaks', 'atac_sequenced_read_pairs', 'atac_number_of_peaks'
        ],
        'SC_TENX_CellPlex' : [
            'cells','number of reads in cells','median genes per cell',
            'total genes detected','median umi counts per cell',
            'confidently mapped to genome'
        ]
    }

    FORMAT_RULES = {
        'SC_TENX_RNA': {
            'int_columns': [
                'estimated number of cells',
                'mean reads per cell',
                'median genes per cell',
                'number of reads',
                'total genes detected',
                'median umi counts per cell'
            ],
            'percent_columns': ['reads mapped confidently to genome']
        },
        'SC_TENX_ATAC': {
            'int_columns': [
                'estimated number of cells',
                'median high-quality fragments per cell',
                'sequenced read pairs',
                'number of peaks'
            ],
            'float_columns': ['mean raw read pairs per cell'],
            'percent_columns': ['fraction of high-quality fragments overlapping peaks']
        },
        'SC_TENX_Visium_FFPE': {
            'int_columns': [
                'number of spots under tissue',
                'mean reads per spot',
                'median genes per spot',
                'number of reads',
                'genes detected',
                'median umi counts per spot'
            ],
            'percent_columns': ['reads mapped confidently to probe set']
        },
        'SC_SeekGene_RNA': {
            'int_columns': [
                'estimated_number_of_cells',
                'mean_reads_per_cell',
                'median_genes_per_cell',
                'number_of_reads',
                'total_genes_detected',
                'median_umi_counts_per_cell'
            ],
            'percent_columns': ['reads_mapped_confidently_to_genome']
        },
        'SC_SeekGene_FullRNA': {
            'int_columns': [
                'estimated_number_of_cells',
                'mean_reads_per_cell',
                'median_genes_per_cell',
                'number_of_reads',
                'total_genes_detected',
                'median_umi_counts_per_cell'
            ],
            'percent_columns': ['reads_mapped_confidently_to_genome']
        },
        'SC_SeekGene_VDJ': {
            'int_columns': [
                'estimated number of cells',
                'mean read pairs per cell',
                'number of read pairs',
                'median tra umis per cell',
                'median trb umis per cell',
                'number of cells with productive v-j spanning pair'
            ],
            'percent_columns': [
                'reads mapped to any v(d)j gene',
                'reads mapped to tra',
                'reads mapped to trb',
                'q30 bases in umi'
            ]
        },
        'SC_TENX_Multiome': {
            'int_columns': [
                'estimated number of cells',
                'gex median genes per cell',
                'gex median umi counts per cell',
                'gex total genes detected',
                'atac median high-quality fragments per cell',
                'atac sequenced read pairs',
                'atac number of peaks'
            ],
            'float_columns': [
                'gex mean raw reads per cell',
                'atac mean raw read pairs per cell'
            ],
            'percent_columns': [
                'gex fraction of transcriptomic reads in cells',
                'gex reads mapped confidently to genome',
                'atac fraction of high-quality fragments overlapping peaks'
            ]
        },
        'SC_SeekGene_Multiome': {
            'int_columns': [
                'estimated_number_of_cells',
                'gex_mean_raw_reads_per_cell',
                'gex_median_genes_per_cell',
                'gex_median_umi_counts_per_cell',
                'gex_total_genes_detected',
                'atac_mean_raw_read_pairs_per_cell',
                'atac_median_high-quality_fragments_per_cell',
                'atac_sequenced_read_pairs',
                'atac_number_of_peaks'
            ],
            'percent_columns': [
                'gex_fraction_of_reads_in_cells',
                'gex_reads_mapped_confidently_to_genome',
                'atac_fraction_of_genome_in_peaks'
            ]
        },
        'SC_TENX_CellPlex': {
            'int_columns': [
                'cells',
                'number of reads in cells',
                'median genes per cell',
                'total genes detected',
                'median umi counts per cell'
            ],
            'percent_columns': ['confidently mapped to genome']
}
    }

    sample_id   = sample_processed['Sample_ID']
    seq_type    = sample_processed['SeqType']
    if seq_type == 'SC_SeekGene_VDJ' and sample_processed['VDJ type'] == '5':
        seq_type    =   'SC_SeekGene_RNA'
    
    
    sample_stat = {}
    try:
        print(stat_full_path)
        if not stat_full_path or not os.path.exists(stat_full_path):
            print(f"⚠️[3.2.r Statistic summary] No statistics file for sample: {sample_id}")
            for col in COLUMN_MAPPINGS.get(seq_type, []):
                sample_stat[col.replace('_', ' ')] = 'N/A'
        else:
            df_stat         =   pd.read_csv(stat_full_path)
            
            if seq_type == 'SC_TENX_CellPlex':
                df_stat = df_stat[df_stat['Category'] == 'Cells'][['Metric Name', 'Metric Value']]
                df_stat = df_stat.set_index('Metric Name').T.reset_index(drop=True)
                df_stat.columns.name = None

            df_stat.columns =   [x.lower() for x in df_stat.columns]
            
            if not df_stat.empty:
                
                columns = COLUMN_MAPPINGS.get(seq_type, [])
                for col in columns:
                    if col in df_stat.columns:
                        value = df_stat[col].iloc[0]
                        if pd.isna(value):
                            sample_stat[col.replace('_', ' ')] = 'N/A'
                            continue
                        
                        def clean_numeric_value(val):
                            if isinstance(val, str):
                                val = val.replace(',', '').strip()
                                if val.startswith('-') or val.lower() in ['nan', 'na', 'n/a']:
                                    return 'N/A'
                                if val.endswith('.0'):
                                    val = val[:-2]
                                if '%' in val:
                                    return val
                            elif isinstance(val, (int, float)):
                                if isinstance(val, float) and val.is_integer():
                                    val = int(val)
                                return str(val)
                            return str(val)
                        
                        formatted_value = value
                        format_rules = FORMAT_RULES.get(seq_type, {})
                        
                        if col in format_rules.get('percent_columns', []):
                            try:
                                cleaned_value = clean_numeric_value(value)
                                if cleaned_value == 'N/A':
                                    formatted_value = 'N/A'
                                elif isinstance(cleaned_value, str) and '%' in cleaned_value:
                                    formatted_value = cleaned_value
                                else:
                                    num_str = str(cleaned_value).replace(',', '').replace('%', '').strip()
                                    num_value = float(num_str)
                                    if num_value < 0:
                                        formatted_value = 'N/A'
                                    elif num_value < 1:
                                        formatted_value = f"{num_value * 100:.2f}%"
                                    elif num_value <= 100:
                                        formatted_value = f"{num_value:.2f}%"
                                    else:
                                        formatted_value = f"{num_value / 100:.2f}%"
                            except (ValueError, TypeError):
                                formatted_value = 'N/A'
                                
                        elif col in format_rules.get('int_columns', []):
                            try:
                                cleaned_value = clean_numeric_value(value)
                                if cleaned_value == 'N/A':
                                    formatted_value = 'N/A'
                                else:
                                    num_str = str(cleaned_value).replace(',', '').strip()
                                    if '.' in num_str:
                                        num_parts = num_str.split('.')
                                        decimal_part = num_parts[1].rstrip('0')
                                        if decimal_part == '':
                                            formatted_value = num_parts[0]
                                        else:
                                            num_value = float(num_str)
                                            if num_value.is_integer():
                                                formatted_value = str(int(num_value))
                                            else:
                                                formatted_value = num_str
                                    else:
                                        try:
                                            num_value = float(num_str)
                                            if num_value.is_integer():
                                                formatted_value = str(int(num_value))
                                            else:
                                                formatted_value = num_str
                                        except:
                                            formatted_value = num_str
                            except (ValueError, TypeError) as e:
                                print(f"Debug: Error processing int column {col}: {e}, value: {value}")
                                formatted_value = 'N/A'
                                
                        elif col in format_rules.get('float_columns', []):
                            try:
                                cleaned_value = clean_numeric_value(value)
                                if cleaned_value == 'N/A':
                                    formatted_value = 'N/A'
                                else:
                                    num_str = str(cleaned_value).replace(',', '').strip()
                                    formatted_value = f"{float(num_str):.2f}"
                            except (ValueError, TypeError):
                                formatted_value = 'N/A'
                        else:
                            cleaned_value = clean_numeric_value(value)
                            if cleaned_value == 'N/A':
                                formatted_value = 'N/A'
                            else:
                                formatted_value = cleaned_value
                        
                        sample_stat[col.replace('_', ' ')] = formatted_value
                    else:
                        sample_stat[col.replace('_', ' ')] = 'N/A'
            else:
                print(f"⚠️[3.2.r Statistic summary] Statistics file is empty for sample: {sample_id}")
                for col in COLUMN_MAPPINGS.get(seq_type, []):
                    sample_stat[col.replace('_', ' ')] = 'N/A'
        sample_processed['Sample stat'] = sample_stat
        print(f"✅[3.2.r Statistic summary] Statistics collected and formatted for sample: {sample_id}")
    except Exception as e:
        print(f"❌[3.2.r Statistic summary] Error processing statistics for {sample_id}: {e}")
        sample_processed['Sample stat'] = {'error': str(e)}
    
    return sample_processed


def create_flowcell_statistics_table(flowcell_sample_processed: dict) -> pd.DataFrame:
    all_rows = []
    for key, value in flowcell_sample_processed.items():
        sample_id   = value.get('Sample_ID', key)
        seq_type    = value.get('SeqType', '')
        vdj_type    = value.get('VDJ type', '')

        sample_stat = value.get('Sample stat', {})
        
        if not sample_stat:
            row_data = {'Sample_ID': sample_id}
            all_rows.append(row_data)
            continue
        
        cleaned_stat = {}
        for stat_key, stat_value in sample_stat.items():
            if isinstance(stat_value, (int, float)):
                if isinstance(stat_value, float) and stat_value.is_integer():
                    cleaned_stat[stat_key] = str(int(stat_value))
                else:
                    cleaned_stat[stat_key] = str(stat_value)
            elif isinstance(stat_value, str):
                if stat_value.endswith('.0'):
                    cleaned_stat[stat_key] = stat_value[:-2]
                else:
                    cleaned_stat[stat_key] = stat_value
            else:
                cleaned_stat[stat_key] = stat_value
        
        if seq_type == 'SC_SeekGene_VDJ':
            prefix = ""
            if vdj_type == '5':
                prefix = "RNA: "
            elif vdj_type == 'TR':
                prefix = "VDJ TR: "
            elif vdj_type == 'IG':
                prefix = "VDJ IG: "
            else:
                prefix = "VDJ: "
            
            row_data = {'Sample_ID': sample_id}
            for stat_key, stat_value in cleaned_stat.items():
                if stat_key != 'Sample_ID':
                    new_key = f"{prefix}{stat_key}"
                    if isinstance(stat_value, str) and stat_value.endswith('.0'):
                        stat_value = stat_value[:-2]
                    row_data[new_key] = stat_value
        else:
            row_data = cleaned_stat.copy()
            row_data['Sample_ID'] = sample_id
        
        all_rows.append(row_data)
    
    if not all_rows:
        return pd.DataFrame()
    
    df = pd.DataFrame(all_rows)
    if 'Sample_ID' in df.columns:
        cols = ['Sample_ID'] + [col for col in df.columns if col != 'Sample_ID']
        df = df[cols]
    for col in df.columns:
        if col != 'Sample_ID':
            df[col] = df[col].apply(
                lambda x: str(x)[:-2] if isinstance(x, str) and str(x).endswith('.0') 
                else (str(int(x)) if isinstance(x, float) and not pd.isna(x) and x.is_integer() 
                     else x)
            )
            df[col] = df[col].apply(
                lambda x: str(int(x)) if hasattr(x, 'is_integer') and hasattr(x, '__class__') 
                and x.__class__.__name__ in ['float64', 'float32', 'float'] 
                and not pd.isna(x) and x.is_integer() 
                else x
            )
    
    return df