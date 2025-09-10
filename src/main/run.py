# source /mnt/raid0/ofateev/soft/seeksoultools.1.3.0/external/conda/bin/activate
import os
import warnings
import getpass
import sys
import time
import json
from pathlib import Path
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
from main._3_Data._1_load_ceph_parse_sheet          import load_airflow_parse
from main._3_Data._2_load_data                      import load_flowcell
from main._3_Data._3_create_flowcell_sheet          import create_run_sheet
from main._3_Data._4_processing                     import processing_flowcell
from main._3_Data._5_check_over_and_create_sumdir   import check_and_move_reports
from main._1_PATHs.tools                            import ToolsType
from main._1_PATHs.results                          import ResultsType
from main._3_Data.processing_code                   import wait_and_retry

import pandas as pd
import traceback
from glob import glob

supported_types = [
        'SC_TENX_RNA',
        'SC_SeekGene_FullRNA',
        'SC_TENX_ATAC',
        'SC_SeekGene_RNA',
        'SC_SeekGene_VDJ'
    ]

# Password and user for load raw files and move to ceph
def get_credentials():
    """Get username and password securely"""
    username    =   input("⚙️ [Authorization] Enter username: ")
    password    =   getpass.getpass("⚙️ [Authorization] Enter password: ")
    return username, password
def get_mail_credentials():
    """Get username and password securely"""
    username    =   input("⚙️ [Authorization] Enter user mail: ")
    password    =   getpass.getpass("⚙️ [Authorization] Enter mail password: ")
    return username, password
# Load Parse ceph file and filter by SEQ type 
def update_info_sheet():
    """Update info sheet and return sorted list of flowcells"""
    info_sheet_path         =   load_airflow_parse(
        info_sheet_ceph8    =   '/mnt/cephfs8_rw/functional-genomics/ofateev/Parse_df/results_parsing.csv',
        info_sheet          =   '/mnt/raid0/ofateev/projects/SC_auto/1.Data/Info/results_parsing.csv'
    )
    info_sheet = pd.read_csv(info_sheet_path)
    info_sheet      =   info_sheet[info_sheet['Desct_TYPE'].isin(supported_types)]
    sorted_list     =   sorted(set(info_sheet['Flowcell']), reverse=True)
    return info_sheet, sorted_list

def process_specific_flowcell(info_sheet, flowcell_name, username, password,sender_email, sender_password):
    # load list of skip flowcells
    skip_flowcells  =   load_skip_flowcells()
    if flowcell_name in skip_flowcells:
        print(
            f"\033[93mFlowcell {flowcell_name} in skip_flowcells list, skipping\033[0m"
            )
        return False
    # Parse Info sheet and get flowcell info
    df_flowcell     =   info_sheet[info_sheet['Flowcell'] == flowcell_name]
    if df_flowcell.empty:
        print(
            f"\033[91mFlowcell {flowcell_name} not found in info_sheet\033[0m"
            )
        return False
        
    # Get seqtype, and path to tool
    seq_type        =   df_flowcell['Desct_TYPE'].iloc[0]
    work_tools      =   '/mnt/raid0/ofateev/soft'
    toolpath_res    =   f"{work_tools}/{ToolsType[seq_type]._get_params()}".split('/')[-1]

    # Check if flowcell is already processed
    if len(glob(f'/mnt/cephfs8_rw/functional-genomics/*_SC_RES/*/{toolpath_res}/{flowcell_name}')) != 0:
        print(f"\033[93mFlowcell {flowcell_name} already processed, skipping\033[0m")
        return False

    ###################################################################################################################
    # START PROCESSED 
    ###################################################################################################################
    print("\033[91m" + "=" * 53 + "\033[0m")
    print(f"\033[92mProcessing specified flowcell: {flowcell_name}\033[0m")

    # Static paths
    bcl_save        =   f'{WORKDIR}/1.Data/BCL'
    fastq_save      =   f'{WORKDIR}/1.Data/FASTQ'
    runsheet_save   =   f'{WORKDIR}/1.Data/RunSheet'
    ceph_pars       =   f'{WORKDIR}/1.Data/Info/results_parsing.csv'
    img_save        =   f'{WORKDIR}/1.Data/Image'

    bcl_load        =   '/mnt/cephfs3_ro/BCL/uvd*'
    fastq_load      =   '/mnt/cephfs*_ro/FASTQS/uvd*'
    type_load_data  =   'fastq'

    try:
        # ✅ 1. Load Flowcell (or pass load if SC_SeekGene_FullRNA and exist filtered_paired.fastq.gz)
        should_load = (seq_type != 'SC_SeekGene_FullRNA' or 
              len(glob(f"{fastq_save}/{flowcell_name}/*filtered_paired.fastq.gz")) == 0)
        fastq_res_folder = (
                load_flowcell(
                        type_seq        =   seq_type,
                        flowcell        =   flowcell_name,
                        bcl_save        =   bcl_save,
                        fastq_save      =   fastq_save,
                        bcl_load        =   bcl_load,
                        fastq_load      =   fastq_load,
                        username        =   username,
                        password        =   password,
                        type_load_data  =   type_load_data
                    )
                if should_load
                else f"{fastq_save}/{flowcell_name}")
    
        # ✅ 2. Create run sheet
        sample_sheet_info_path, samples_parse_df = create_run_sheet(
                        flowcell        =   flowcell_name,
                        fastq_save      =   fastq_res_folder,
                        infosheet       =   df_flowcell,
                        runsheet_save   =   runsheet_save,
                        img_save        =   f"{img_save}/{flowcell_name}", 
                        supported_type  =   supported_types
        )

        # ✅  3. Run processing
        res_folder_local = processing_flowcell(
                        runsheet        =   samples_parse_df,
                        path_run_sheet  =   sample_sheet_info_path,
                        work_ref        =   '/mnt/raid0/ofateev/refs',
                        work_tools      =   '/mnt/raid0/ofateev/soft',
                        work_run        =   WORKDIR
        )

        # 4. Move reports, sync with ceph and clean up
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

def main():
    # Check command line arguments
    specific_flowcell = None
    if len(sys.argv) > 1 and sys.argv[1].strip():
        specific_flowcell = sys.argv[1].strip()
        print(f"\033[92mSpecific flowcell processing mode: {specific_flowcell}\033[0m")

    # Load initial skip_flowcells list
    skip_flowcells = load_skip_flowcells()
    print(f"\033[92mLoaded {len(skip_flowcells)} flowcells in skip list\033[0m")
    if skip_flowcells:
        print(f"\033[93mSkipped flowcells: {', '.join(skip_flowcells)}\033[0m")
    
    username, password = get_credentials()
    print(f"✅[Login] Using username: {username}")
    print(f"✅[Login] Using password: {'*' * len(password)}")
    
    sender_email, sender_password = get_mail_credentials()
    print(f"✅[Login] Using mail username: {sender_email}")
    print(f"✅[Login] Using mail password: {'*' * len(sender_password)}")
    print("\033[91m" + "=" * 53 + "\033[0m")


    # If specific flowcell is specified, process only it
    if specific_flowcell:
        info_sheet, sorted_list = update_info_sheet()
        success = process_specific_flowcell(info_sheet      =   info_sheet, 
                                            flowcell_name   =   specific_flowcell, 
                                            username        =   username, 
                                            password        =   password, 
                                            sender_email    =   sender_email, 
                                            sender_password =   sender_password)
        if success:
            print(f"\033[92mCompleted processing flowcell: {specific_flowcell}\033[0m")
        else:
            print(f"\033[91mFailed to process flowcell: {specific_flowcell}\033[0m")
        return

    # Infinite processing loop (original mode)
    while True:
        try:
            # Update flowcells information
            info_sheet, sorted_list = update_info_sheet()
            
            if not sorted_list:
                print("\033[93mNo available flowcells for processing.\033[0m")
                if not wait_and_retry():
                    break
                continue
            
            print(f"\033[92mFound {len(sorted_list)} flowcells for processing\033[0m")
            
            for flowcell in sorted_list:
                try:
                    success = process_specific_flowcell(info_sheet      =   info_sheet, 
                                                        flowcell_name   =   flowcell, 
                                                        username        =   username, 
                                                        password        =   password,
                                                        sender_email    =   sender_email, 
                                                        sender_password =   sender_password)
                    if success:
                        print(f"\033[92mSuccessfully processed flowcell: {flowcell}\033[0m")
                    else:
                        print(f"\033[91mFailed to process flowcell: {flowcell}\033[0m")
                except Exception as e:
                    error_msg = f"ERROR processing flowcell {flowcell}: {str(e)}"
                    print(f"\033[91m{error_msg}\033[0m")
                    print(f"Traceback: {traceback.format_exc()}")
                    
                    # Add problematic flowcell to skip list
                    add_to_skip_flowcells(flowcell, f"Processing error: {str(e)}")
                    continue

            # After processing all flowcells, wait
            if not wait_and_retry():
                break

        except Exception as e:
            error_msg = f"ERROR in main loop: {str(e)}"
            print(f"\033[91m{error_msg}\033[0m")
            print(f"Traceback: {traceback.format_exc()}")
            
            # Wait 1 hour before retry on error
            print("\033[93mWaiting 1 hour before retry...\033[0m")
            time.sleep(7200)

if __name__ == "__main__":
    main()