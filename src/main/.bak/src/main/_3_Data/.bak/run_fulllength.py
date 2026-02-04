from _3_Data._1_load_ceph_parse_sheet           import  load_airflow_parse
from _3_Data._2_load_data                       import  load_flowcell
from _3_Data._3_create_flowcell_sheet           import  create_run_sheet
from _3_Data._4_processing                      import  processing_flowcell
from _3_Data._5_check_over_and_create_sumdir    import  check_and_move_reports

import pandas as pd
import sys


def main():
    """
    Main function to automate the pipeline for flowcell data processing.
    
    Pipeline steps:
    1. Load and parse info sheet with sample metadata.
    2. Load BCL/FASTQ data from remote storage.
    3. Generate run sheet for current flowcell.
    4. Process flowcell (e.g., alignment, QC).
    5. Check and move reports + sync with ceph + clean up local files.
    """
    
    info_sheet_path = load_airflow_parse(
        info_sheet_ceph8='/mnt/cephfs8_rw/functional-genomics/ofateev/Parse_df/results_parsing.csv',
        info_sheet='/mnt/raid0/ofateev/projects/SC_auto/1.Data/Info/results_parsing.csv'
    )
    
    info_sheet = pd.read_csv(info_sheet_path)

    # Filter by supported sequencing types
    #supported_types = ['SC_TENX_RNA', 'SC_TENX_ATAC', 'SC_SeekGene_RNA', 'SC_SeekGene_VDJ']
    #info_sheet = info_sheet[info_sheet['Desct_TYPE'].isin(supported_types)]

    # Static paths
    bcl_save = '/mnt/raid0/ofateev/projects/SC_auto/1.Data/BCL'
    fastq_save = '/mnt/raid0/ofateev/projects/SC_auto/1.Data/FASTQ'
    runsheet_save = '/mnt/raid0/ofateev/projects/SC_auto/1.Data/RunSheet'
    ceph_pars = '/mnt/raid0/ofateev/projects/SC_auto/1.Data/Info/results_parsing.csv'

    bcl_load = '/mnt/cephfs3_ro/BCL/uvd*'
    fastq_load = '/mnt/cephfs*_ro/FASTQS/uvd*'
    username = 'ofateev'
    password = '112358Iop24???'
    type_load_data = 'fastq'

    # --- Process each flowcell ---
    for flowcell in ['250814_VH00195_210_AAATMY5HV']:
        print("\033[91m" + "=" * 53 + "\033[0m")
        #df_flowcell = info_sheet[info_sheet['Flowcell'] == flowcell]
        #seq_type = df_flowcell['Desct_TYPE'].iloc[0]

        # 1. Load FASTQ or BCL data
        #fastq_res_folder = load_flowcell(
        #    type_seq        =   seq_type,
        #    flowcell        =   flowcell,
        #    bcl_save        =   bcl_save,
        #    fastq_save      =   fastq_save,
        #    bcl_load        =   bcl_load,
        #    fastq_load      =   fastq_load,
        #    username        =   username,
        #    password        =   password,
        #    type_load_data  =   type_load_data,
        #    filter_reads    =   True
        #)

        # 2. Create run sheet
        fastq_res_folder    =   f'/mnt/raid0/ofateev/projects/SC_auto/1.Data/FASTQ/{flowcell}'
        path_run_sheet      =   f'/mnt/raid0/ofateev/projects/SC_auto/1.Data/RunSheet/{flowcell}-run_sheet.csv'
        
        #sample_sheet_info_path, samples_parse_df = create_run_sheet(
        #    fastq_save      =   fastq_res_folder,
        #    infosheet       =   ceph_pars,
        #    runsheet_save   =   runsheet_save
        #)

        # 3. Run processing

        sample_sheet_info_path  =   f'/mnt/raid0/ofateev/projects/SC_auto/1.Data/RunSheet/{flowcell}-run_sheet.csv'
        samples_parse_df        =   pd.read_csv(sample_sheet_info_path)
        res_folder_local        =   processing_flowcell(runsheet=samples_parse_df,
                                               path_run_sheet=sample_sheet_info_path,
                                               core=20,
                                               mem=200)

        # 4. Move reports, sync with ceph and clean up
        check_and_move_reports(
            runsheet=samples_parse_df,
            runsheet_path=sample_sheet_info_path,
            flowcell=flowcell,
            fastq_res_folder=fastq_res_folder,
            password=password
        )
        print("\033[91m" + "=" * 53 + "\033[0m")


if __name__ == "__main__":
    main()