# source /mnt/raid0/ofateev/soft/seeksoultools.1.3.0/external/conda/bin/activate
import os
import warnings

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
from main._3_Data.processing_code                   import process_specific_flowcell, wait_and_retry
from main._3_Data.start_steps                       import get_credentials, get_mail_credentials, update_info_sheet


import traceback
from glob import glob

# Static paths
bcl_save        =   f'{WORKDIR}/1.Data/BCL'
fastq_save      =   f'{WORKDIR}/1.Data/FASTQ'
runsheet_save   =   f'{WORKDIR}/1.Data/RunSheet'
ceph_pars       =   f'{WORKDIR}/1.Data/Info/results_parsing.csv'
img_save        =   f'{WORKDIR}/1.Data/Image'

type_load_data  =   'fastq'


def main():
    # Check command line arguments
    specific_flowcell = None
    if len(sys.argv) > 1 and sys.argv[1].strip():
        specific_flowcell = sys.argv[1].strip()
        print(f"\033[92mSpecific flowcell processing mode: {specific_flowcell}\033[0m")

    # Load initial skip_flowcells list
    skip_flowcells  =   load_skip_flowcells()
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
    #==========================================================================================
    #=======================SPECIFIC=FLOWCELL==================================================
    #==========================================================================================
    if specific_flowcell:
        info_sheet, sorted_list = update_info_sheet()
        success = process_specific_flowcell(info_sheet      =   info_sheet, 
                                            flowcell_name   =   specific_flowcell, 
                                            username        =   username, 
                                            password        =   password, 
                                            sender_email    =   sender_email, 
                                            sender_password =   sender_password,
                                            type_load_data  =   type_load_data)
        if success == True:
            print(f"\033[92mCompleted processing flowcell: {specific_flowcell}\033[0m")
        elif success == 'Ready':
            success
        else:
            print(f"\033[91mFailed to process flowcell: {specific_flowcell}\033[0m")
        return

    #==========================================================================================
    #=======================STANDART=MODE======================================================
    #==========================================================================================
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
                                                        sender_password =   sender_password,
                                                        type_load_data  =   type_load_data)
                    if success:
                        print(f"\033[92mSuccessfully processed flowcell: {flowcell}\033[0m")
                    else:
                        print(f"\033[91mFailed to process flowcell: {flowcell}\033[0m")
                except Exception as e:
                    error_msg = f"ERROR processing flowcell {flowcell}: {str(e)}"
                    print(f"\033[91m{error_msg}\033[0m")
                    print(f"Traceback: {traceback.format_exc()}")
                    
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
            time.sleep(2.5 * 60 * 60)
    #==========================================================================================
    #==========================================================================================
    #==========================================================================================

if __name__ == "__main__":
    main()