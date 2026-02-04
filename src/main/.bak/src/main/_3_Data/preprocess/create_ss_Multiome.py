from glob import glob
import pandas as pd
import os

def create_ss_tenx_multiome(
                        sample:str,
                        org_postfix:str,
                        fastq_dir:str,
                        multiome_ss_dir:str,
                        flowcell:str):
    
    flowcell_rna    =   flowcell.split('-')[0]
    flowcell_atac   =   flowcell.split('-')[1]

    files_rna       =   glob(f'{fastq_dir}/{flowcell_rna}/{sample}_S*.gz')
    files_atac      =   glob(f'{fastq_dir}/{flowcell_atac}/{sample}_S*.gz')
 
    samples_rna     =   list(set([x.split('/')[-1].split('_')[0] for x in files_rna if 'Undetermined' not in x]))
    samples_atac    =   list(set([x.split('/')[-1].split('_')[0] for x in files_atac if 'Undetermined' not in x]))

    output_dir      =   f'{multiome_ss_dir}/{flowcell}'
    os.makedirs(output_dir, exist_ok=True)

    if set(samples_rna) == set(samples_atac):
        samples = samples_rna
        print("✅[Multiome 10X SS] Samples match between RNA and ATAC")
    else:
        print( '❌[Multiome 10X SS] Error: RNA and ATAC samples do not match!')
        print(f'❌[Multiome 10X SS] RNA only:   {set(samples_rna) - set(samples_atac)}')
        print(f'❌[Multiome 10X SS] ATAC only:  {set(samples_atac) - set(samples_rna)}')
        samples = None

    if sample is not None:
        columns = ['fastqs', 'sample', 'library_type']
        ss_path = f'{output_dir}/{sample}_{org_postfix}.csv'
        if not os.path.exists(ss_path):
            rna_row     =   [f'{fastq_dir}/{flowcell_rna}', sample, 'Gene Expression'] 
            atac_row    =   [f'{fastq_dir}/{flowcell_atac}', sample, 'Chromatin Accessibility'] 
            ss_df       =   pd.DataFrame([rna_row, atac_row], columns=columns)
            ss_df.to_csv(ss_path, index=False)
        else:
            print(f'✅[Multiome 10X SS] Sample sheet already exists!')

        return ss_path
    else:
        return None