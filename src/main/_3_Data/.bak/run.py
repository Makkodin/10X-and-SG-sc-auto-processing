from _3_Data._1_load_ceph_parse_sheet import load_airflow_parse
from _3_Data._2_load_data import load_flowcell
from _3_Data._3_create_flowcell_sheet import  create_run_sheet
from _3_Data._4_processing import processing_flowcell
from _3_Data._5_check_over_and_create_sumdir import check_and_move_reports

import sys
import pandas as pd

flowcell = sys.argv[1]

info_sheet = load_airflow_parse(info_sheet_ceph8 = '/mnt/cephfs8_rw/functional-genomics/ofateev/Parse_df/results_parsing.csv',
                                info_sheet  =   '/mnt/raid0/ofateev/projects/SC_auto/1.Data/Info/results_parsing.csv')

info_sheet  =   pd.read_csv(info_sheet)
df_flowcell = info_sheet[info_sheet['Flowcell'] == flowcell]
type_seq    =   df_flowcell['Desct_TYPE'].to_list()[0]
bcl_save    =   '/mnt/raid0/ofateev/projects/SC_auto/1.Data/BCL'
fastq_save  =   '/mnt/raid0/ofateev/projects/SC_auto/1.Data/FASTQ'
bcl_load    =   '/mnt/cephfs3_ro/BCL/uvd*'
fastq_load  =   '/mnt/cephfs*_ro/FASTQS/uvd*'
username    =   'ofateev'
password    =   '112358Iop24???'
type_load_data  =   'fastq'


fastq_res_folder    =   load_flowcell( type_seq = type_seq,
    flowcell = flowcell,
    bcl_save = bcl_save,
    fastq_save = fastq_save,
    bcl_load = bcl_load,
    fastq_load = fastq_load,
    username = username,
    password = password,
    type_load_data = type_load_data)

sample_sheet_info_path, samples_parse_df = create_run_sheet(fastq_save = fastq_res_folder,
                                                            infosheet   =   '/mnt/raid0/ofateev/projects/SC_auto/1.Data/Info/results_parsing.csv',
                                                            runsheet_save   =   '/mnt/raid0/ofateev/projects/SC_auto/1.Data/RunSheet')

res_folder_local    =   processing_flowcell(runsheet=samples_parse_df)