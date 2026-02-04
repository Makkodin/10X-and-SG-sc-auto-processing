# source /mnt/raid0/ofateev/soft/seeksoultools.1.3.0/external/conda/bin/activate
import os
import warnings

import sys
import time
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"

current_dir     =   os.path.dirname(os.path.abspath(__file__))
if current_dir.endswith('/src'):
    ROOT_DIR    =   os.path.dirname(current_dir)
else:
    ROOT_DIR    =   current_dir
WORKDIR     =   ROOT_DIR.split('/src')[0]
sys.path.insert(0, ROOT_DIR)
from main._3_Data._0_skip_flowcells                 import load_skip_flowcells, add_to_skip_flowcells
from main._3_Data._2_load_data                      import load_flowcell
from main._3_Data._3_create_flowcell_sheet          import create_run_sheet
from main._3_Data._4_processing                     import processing_flowcell
from main._3_Data._5_check_over_and_create_sumdir   import check_and_move_reports
from main._1_PATHs.tools                            import ToolsType
from main._3_Data.start_steps                       import supported_types
from main._1_PATHs.paths                            import bcl_load, fastq_load, refs_dir, soft_dir
from main._3_Data.preprocess.check_data_multiome_flowcell   import check_flowcells_by_date
import traceback
from glob import glob
import re
import pandas as pd

# Static paths
bcl_save        =   f'{WORKDIR}/1.Data/BCL'
fastq_save      =   f'{WORKDIR}/1.Data/FASTQ'
runsheet_save   =   f'{WORKDIR}/1.Data/RunSheet'
ceph_pars       =   f'{WORKDIR}/1.Data/Info/results_parsing.csv'
img_save        =   f'{WORKDIR}/1.Data/Image'



def process_specific_flowcell(info_sheet, 
                              flowcell_name, 
                              username, 
                              password,
                              sender_email, 
                              sender_password,
                              type_load_data):
    
    skip_flowcells  =   load_skip_flowcells()

    original_flowcell_name  =   flowcell_name
    if flowcell_name in skip_flowcells:
        print(f"\033[93mFlowcell {flowcell_name} in skip_flowcells list, skipping\033[0m")
        return False
    

    if type(flowcell_name) == str:
        df_flowcell_temp    =   info_sheet[info_sheet['Flowcell'] == flowcell_name]
        seq_types           =   df_flowcell_temp['Desct_TYPE'].unique()

        df_flowcell     =   []
        flowcell_names  =   []
        for seq_type in  seq_types:
            df_flowcell_seq_type    =   df_flowcell_temp[df_flowcell_temp['Desct_TYPE'] == seq_type]
            if 'Multiome' in seq_type:
                df_flowcell_seq_type    =   info_sheet[info_sheet['Sample_ID'].isin(df_flowcell_seq_type['Sample_ID'].unique().tolist())]
                df_flowcell_seq_type    =   df_flowcell_seq_type[df_flowcell_seq_type['Desct_TYPE'].isin([
                                                                    f'{seq_type.rsplit("_", maxsplit=1)[0]}_RNA',
                                                                    f'{seq_type.rsplit("_", maxsplit=1)[0]}_ATAC',
                                                                    ])]
                valid_flowcells         =   check_flowcells_by_date(df=df_flowcell_seq_type, date_column='Flowcell', max_days_diff=10)
                df_flowcell_seq_type    =   df_flowcell_seq_type[df_flowcell_seq_type['Flowcell'].isin(valid_flowcells)]

                rna_flowcell            =   df_flowcell_seq_type[df_flowcell_seq_type['Desct_TYPE'].str.contains('_RNA')]['Flowcell'].unique()[0]
                atac_flowcell           =   df_flowcell_seq_type[df_flowcell_seq_type['Desct_TYPE'].str.contains('_ATAC')]['Flowcell'].unique()[0]
                flowcell_name           =   f'{rna_flowcell}-{atac_flowcell}'
            else:
                flowcell_name           =   original_flowcell_name

            flowcell_names.append(flowcell_name)

            if 'SC_SeekGene_Multiome' in seq_type:
                seq_type    =   'SC_SeekGene_Multiome'
            elif 'SC_TENX_Multiome' in seq_type:
                seq_type    =   'SC_TENX_Multiome'

            toolpath_res    =   f"{soft_dir}/{ToolsType[seq_type]._get_params()}".split('/')[-1]
            if len(glob(f'/mnt/cephfs8_rw/functional-genomics/*_SC_RES/*/{toolpath_res}/{flowcell_name}')) != 0:
                continue
            else:
                if len(df_flowcell) == 0:
                    df_flowcell =   df_flowcell_seq_type
                else: 
                    df_flowcell =   pd.concat([df_flowcell, df_flowcell_seq_type], axis=0)
            
    if df_flowcell.empty:
        print(f"\033[91mFlowcell {flowcell_name} not found in info_sheet\033[0m")
        return False

    ###################################################################################################################
    ############################################# START PROCESSED #####################################################
    ###################################################################################################################
    print("\033[91m" + "=" * 53 + "\033[0m")
    print(f"\033[92mProcessing specified flowcell: {flowcell_name}\033[0m")

    pattern = r'\d{6}_.*-\d{6}_.*'
    try:
        # ✅ 1. Load Flowcell (or pass load if SC_SeekGene_FullRNA and exist filtered_paired.fastq.gz)
        already_loadet      =   []
        fastq_res_folder    =   []
        for flowcell_name in list(set(flowcell_names)): 
            should_load = ('SC_SeekGene_FullRNA' not in seq_types or 
                  len(glob(f"{fastq_save}/{flowcell_name}/*filtered_paired.fastq.gz")) == 0)
            ################################################################
            # ✅ ##### Multiome ############################################
            ################################################################
            if re.match(pattern, flowcell_name):
                
                split_flowcell      =   flowcell_name.split('-')
                df_flowcell_temp    =   df_flowcell[df_flowcell['Flowcell'].isin(split_flowcell)][['Flowcell', 'Desct_TYPE']].drop_duplicates()
                for row_flowcell_temp in df_flowcell_temp['Flowcell'].unique():
                    if row_flowcell_temp not in already_loadet:
                        seq_type_temp   =   df_flowcell_temp[df_flowcell_temp['Flowcell'] == row_flowcell_temp]['Desct_TYPE'].unique()
                        flowcell_temp   =   row_flowcell_temp

                        if 'SC_SeekGene_Multiome' in seq_type_temp:
                            seq_type_temp    =   'SC_SeekGene_Multiome'
                        elif 'SC_TENX_Multiome' in seq_type_temp:
                            seq_type_temp    =   'SC_TENX_Multiome'

                        fastq_res_folders = (
                            load_flowcell(
                                    type_seq        =   seq_type_temp,
                                    flowcell        =   flowcell_temp,
                                    bcl_save        =   bcl_save,
                                    fastq_save      =   fastq_save,
                                    bcl_load        =   bcl_load,
                                    fastq_load      =   fastq_load,
                                    username        =   username,
                                    password        =   password,
                                    type_load_data  =   type_load_data
                                )
                            if should_load
                            else f"{fastq_save}/{flowcell_temp}")
                        fastq_res_folder.append(fastq_res_folders)
                        already_loadet.append(row_flowcell_temp)
                    else:
                        print(f'[Processing] Flowcell {row_flowcell_temp} already load.')
            ################################################################
            # ✅ ##### Single ##############################################
            ################################################################
            else:
                df_flowcell_temp    =   df_flowcell[df_flowcell['Flowcell'].isin([flowcell_name])][['Flowcell', 'Desct_TYPE']].drop_duplicates()
                for row_flowcell_temp in df_flowcell_temp['Flowcell'].unique():
                    if row_flowcell_temp not in already_loadet:
                        seq_type_temp   =   df_flowcell_temp[df_flowcell_temp['Flowcell'] == row_flowcell_temp]['Desct_TYPE'].unique()
                        flowcell_temp   =   row_flowcell_temp
                        fastq_res_folders = (
                                load_flowcell(
                                        type_seq        =   seq_type_temp,
                                        flowcell        =   flowcell_temp,
                                        bcl_save        =   bcl_save,
                                        fastq_save      =   fastq_save,
                                        bcl_load        =   bcl_load,
                                        fastq_load      =   fastq_load,
                                        username        =   username,
                                        password        =   password,
                                        type_load_data  =   type_load_data
                                    )
                                if should_load
                                else f"{fastq_save}/{flowcell_temp}")
                        already_loadet.append(row_flowcell_temp)
                        fastq_res_folder.append(fastq_res_folders)
                    else:
                        print(f'[Processing] Flowcell {row_flowcell_temp} already load.')
        ################################################################
        # ✅ ##### 2. Create run sheet #################################
        ################################################################
        sample_sheet_info_path, samples_parse_df = create_run_sheet(
                        flowcell        =   flowcell_names,
                        fastq_save      =   fastq_res_folder,
                        infosheet       =   df_flowcell,
                        runsheet_save   =   runsheet_save,
                        img_save        =   f"{img_save}/{flowcell_name}", 
                        supported_type  =   supported_types
        )
        ################################################################
        # ✅ ##### 3. Run processing ###################################
        ################################################################
        flowcell_name = processing_flowcell(
                        runsheet        =   samples_parse_df,
                        path_run_sheet  =   sample_sheet_info_path,
                        work_ref        =   refs_dir,
                        work_tools      =   soft_dir,
                        work_run        =   WORKDIR
        )

        # 4. Move reports, sync with ceph and clean up
        for f_n in flowcell_name:
            check_rep = check_and_move_reports(
                 runsheet                   =   samples_parse_df,
                 runsheet_path              =   sample_sheet_info_path,
                 flowcell                   =   flowcell_name,
                 fastq_res_folder           =   fastq_res_folder,
                 password                   =   password,
                 sender_email               =   sender_email,
                 sender_password            =   sender_password
             )
    
        check_rep   = True
        if check_rep != False:
            print(f"\033[92mSuccessfully processed flowcell: {flowcell_name}\033[0m")
            print("\033[91m" + "=" * 53 + "\033[0m")
            return True
        else:
            add_to_skip_flowcells(flowcell_name, f"Processing error")
            print(f"\033[91mError processing flowcell: {flowcell_name}\033[0m")
            print("\033[91m" + "=" * 53 + "\033[0m")
            return False

    except Exception as e:
        error_msg = f"ERROR processing flowcell {flowcell_name}: {str(e)}"
        print(f"\033[91m{error_msg}\033[0m")
        print(f"Traceback: {traceback.format_exc()}")
        
        # Add problematic flowcell to skip list
        add_to_skip_flowcells(flowcell_name, f"Processing error: {str(e)}")
        return False

def wait_and_retry(wait_hours=3):
    wait_seconds = wait_hours * 60 * 60
    
    print(f"\n\033[93m{'='*60}\033[0m")
    print(f"\033[93mAll flowcells processed. Waiting {wait_hours} hours...\033[0m")
    print(f"\033[93mNext check: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + wait_seconds))}\033[0m")
    print(f"\033[93mPress Ctrl+C to exit\033[0m")
    print(f"\033[93m{'='*60}\033[0m")
    
    try:
        # Wait with periodic status updates
        for remaining in range(wait_seconds, 0, -300):  # Update every 5 minutes
            if remaining % 1800 == 0:  # Every 30 minutes
                hours_left = remaining // 3600
                mins_left = (remaining % 3600) // 60
                print(f"\033[93mTime left: {hours_left}h {mins_left}m\033[0m")
            time.sleep(300)
        
        print("\033[92mWaiting completed. Updating flowcells list...\033[0m")
        return True
        
    except KeyboardInterrupt:
        print("\n\033[91mInterrupted by user. Exiting...\033[0m")
        return False