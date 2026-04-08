import os
import warnings
import sys
import time
import traceback
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"
from main._1_Config.main_config import  ROOT_DIR,   WORKDIR, \
                                        Paths,      TypeConfig, RefsName,PrefixName,FilterParams,\
                                        SupportedTypes, MAX_diff_date_multiome,\
                                        WORK_data_type
sys.path.insert(0, ROOT_DIR)
from main._3_Processing._0_PREprocessing.skip_flowcells             import load_skip_flowcells, add_to_skip_flowcells
from main._3_Processing._0_PREprocessing.already_process_flowcell   import load_processed_flowcells
from main._3_Processing._0_PREprocessing.start_steps                import get_credentials, get_mail_credentials, update_info_sheet
from main._3_Processing.processing_code                             import full_process_flowcell

BCL_load                =   Paths.BCL_load.value                        # '/mnt/cephfs3_ro/BCL/uvd*'
FASTQ_load              =   Paths.FASTQ_load.value                      # '/mnt/cephfs*_ro/FASTQS/uvd*'
REFS_local_dir          =   Paths.REFS_local_dir.value                  # '/mnt/raid0/ofateev/refs'
SOFT_local_dir          =   Paths.SOFT_local_dir.value                  # '/mnt/raid0/ofateev/soft'
CEPH_sheet_parse_raw    =   Paths.CEPH_sheet_parse_raw.value            # '/mnt/cephfs8_rw/functional-genomics/ofateev/Parse_df/results_parsing.csv'

BCL_save                =   f"{WORKDIR}/{Paths.BCL_save.value}"         # '/mnt/raid0/ofateev/projects/SC_auto/1.Data/BCL'
FASTQ_save              =   f"{WORKDIR}/{Paths.FASTQ_save.value}"       # '/mnt/raid0/ofateev/projects/SC_auto/1.Data/FASTQ'
RUNsheet_save           =   f"{WORKDIR}/{Paths.RUNsheet_save.value}"    # '/mnt/raid0/ofateev/projects/SC_auto/1.Data/RunSheet'
CEPH_sheet_parse        =   f"{WORKDIR}/{Paths.CEPH_sheet_parse.value}" # '/mnt/raid0/ofateev/projects/SC_auto/1.Data/Info/results_parsing.csv'
IMG_save                =   f"{WORKDIR}/{Paths.IMG_save.value}"         # '/mnt/raid0/ofateev/projects/SC_auto/1.Data/Image'
SKIP_list_save          =   f"{WORKDIR}/{Paths.SKIP_list_save.value}"   # '/mnt/raid0/ofateev/projects/SC_auto/src/main/_1_Config'

SUPPORT_types           =   SupportedTypes.SUPPORT_types.value          # ['SC_TENX_RNA','SC_SeekGene_FullRNA','SC_TENX_ATAC','SC_SeekGene_RNA','SC_SeekGene_VDJ','SC_TENX_Multiome_RNA','SC_TENX_Multiome_ATAC','SC_SeekGene_Multiome_RNA','SC_SeekGene_Multiome_ATAC']
CELLPLEX_types          =   SupportedTypes.CELLPLEX_types.value         # ['SC_TENX_CellPlex']
MULTIOME_types          =   SupportedTypes.MULTIOME_types.value         # ['SC_TENX_Multiome_RNA','SC_TENX_Multiome_ATAC','SC_SeekGene_Multiome_RNA','SC_SeekGene_Multiome_ATAC']
REFs_ORG_compare        =   RefsName.organ_dict.value                   # {'human': 'GRCh38', 'mouse': 'MM10', 'mulatta': 'MacMul'}
REFs_ORG_prefix         =   PrefixName.organ_dict.value                 # {'human': 'h','mouse':'m','mulatta':'mmul'}

Filter_fastp_params     =   FilterParams.args.value                     # {'core':16,'min_length':60,'max_len1':150}

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

def main():
    """
    If you want to run specific flowcell, example 240918_A00926_0824_BHT35WDMXY
    """
    specific_flowcell = None
    if len(sys.argv) > 1 and sys.argv[1].strip():
        specific_flowcell = sys.argv[1].strip()
        print(f"\033[92m🕐[Main] Specific flowcell processing mode: {specific_flowcell}\033[0m")
    
    """
    Load list of flowcells who add to skip list by any reason
    """
    skip_flowcells      =   load_skip_flowcells(path_to_file        =   SKIP_list_save)
    print(f"\033[92m✅[Main] Loaded {len(skip_flowcells)} flowcells in skip list\033[0m")
    if skip_flowcells:
        print(f"\033[93m🕐[Main] Skipped flowcells: {len(skip_flowcells)}\033[0m")
        if specific_flowcell in skip_flowcells:
            print(f"\033[93m❌[Main] Flowcell {specific_flowcell} in Skip list!\033[0m")
            return

    processed_flowcells =   load_processed_flowcells(path_to_file   =   SKIP_list_save)
    if processed_flowcells:
        print(f"\033[93m🕐[Main] Processed flowcells: {len(processed_flowcells)}\033[0m")
        if specific_flowcell in processed_flowcells:
            print(f"\033[93m✅[Main] Flowcell {specific_flowcell} in Processed list!\033[0m")
            return
    
    """
    Enter you password and username
    """    
    username, password              =    get_credentials()
    print(f"✅[Login] Using username: {username}")
    print(f"✅[Login] Using password: {'*' * len(password)}")
    sender_email, sender_password   =   get_mail_credentials()
    print(f"✅[Login] Using mail username: {sender_email}")
    print(f"✅[Login] Using mail password: {'*' * len(sender_password)}")
    print("\033[91m" + "=" * 53 + "\033[0m")
    """
    First load Ceph Parse
    """
    info_sheet, sorted_list = update_info_sheet(workdir             =   WORKDIR,
                                                info_sheet          =   CEPH_sheet_parse,
                                                max_date_diff       =   MAX_diff_date_multiome,
                                                cellplex_types      =   CELLPLEX_types,
                                                multiome_types      =   MULTIOME_types,
                                                supported_types     =   SUPPORT_types,
                                                info_sheet_ceph8    =   CEPH_sheet_parse_raw)

    print("\033[91m" + "=" * 53 + "\033[0m")
    """  
    If you want to run specific flowcell, example 240918_A00926_0824_BHT35WDMXY
    """  
    if specific_flowcell:   
        success = full_process_flowcell(info_sheet         =   info_sheet, 
                                        flowcell_name       =   specific_flowcell, 
                                        username            =   username,       password        =   password, 
                                        sender_email        =   sender_email,   sender_password =   sender_password,
                                        type_load_data      =   WORK_data_type,
                                        skip_flowcells      =   skip_flowcells,
                                        processed_flowcells =   processed_flowcells,
                                        TypeConfig          =   TypeConfig,
                                        REFs_ORG_compare    =   REFs_ORG_compare,
                                        REFs_ORG_prefix     =   REFs_ORG_prefix,
                                        SOFT_local_dir      =   SOFT_local_dir,
                                        REFS_local_dir      =   REFS_local_dir,
                                        Fastp_params        =   Filter_fastp_params,
                                        workdir             =   WORKDIR, 
                                        BCL_load            =   BCL_load,
                                        BCL_save            =   BCL_save,
                                        FASTQ_load          =   FASTQ_load,
                                        FASTQ_save          =   FASTQ_save,
                                        processed_skip      =   SKIP_list_save,
                                        email_config        =   f'{SKIP_list_save}/email_config.ini'
                                        )
        if success == True:
            print(f"\033[92m✅[Main] Completed processing flowcell: {specific_flowcell}\033[0m")
            print(f"\033[92m✅[Main] Flowcell add to succesful processing list\033[0m")
        else:
            add_to_skip_flowcells(	path_to_file    =	SKIP_list_save,
							 		flowcell	=	specific_flowcell, 
									reason		=	f"Error in {specific_flowcell} processed")
            print(f"\033[91m❌[Main] Failed to process flowcell: {specific_flowcell}\033[0m")
            print(f"\033[91m❌[Main] Add flowcell {specific_flowcell} to skip list\033[0m")
        return
    
    while True:
        try:
            info_sheet, sorted_list = update_info_sheet(workdir             =   WORKDIR,
                                                info_sheet          =   CEPH_sheet_parse,
                                                max_date_diff       =   MAX_diff_date_multiome,
                                                cellplex_types      =   CELLPLEX_types,
                                                multiome_types      =   MULTIOME_types,
                                                supported_types     =   SUPPORT_types,
                                                info_sheet_ceph8    =   CEPH_sheet_parse_raw)
            
            merge_list  =   processed_flowcells +   skip_flowcells
            sorted_list =   list(
                set(sorted_list)    -   set(merge_list)
            )
            sorted_list     =   sorted(set(sorted_list), 
                                reverse=True)
            if not sorted_list:
                print("\033[93mNo available flowcells for processing.\033[0m")
                if not wait_and_retry(wait_hours    =   5):
                    break
                continue
            for specific_flowcell in sorted_list:
                success = full_process_flowcell(info_sheet         =   info_sheet, 
                                                flowcell_name       =   specific_flowcell, 
                                                username            =   username,       password        =   password, 
                                                sender_email        =   sender_email,   sender_password =   sender_password,
                                                type_load_data      =   WORK_data_type,
                                                skip_flowcells      =   skip_flowcells,
                                                processed_flowcells =   processed_flowcells,
                                                TypeConfig          =   TypeConfig,
                                                REFs_ORG_compare    =   REFs_ORG_compare,
                                                REFs_ORG_prefix     =   REFs_ORG_prefix,
                                                SOFT_local_dir      =   SOFT_local_dir,
                                                REFS_local_dir      =   REFS_local_dir,
                                                Fastp_params        =   Filter_fastp_params,
                                                workdir             =   WORKDIR, 
                                                BCL_load            =   BCL_load,
                                                BCL_save            =   BCL_save,
                                                FASTQ_load          =   FASTQ_load,
                                                FASTQ_save          =   FASTQ_save,
                                                processed_skip      =   SKIP_list_save,
                                                email_config        =   f'{SKIP_list_save}/email_config.ini'
                                                )
                if success == True:
                    print(f"\033[92m✅[Main] Completed processing flowcell: {specific_flowcell}\033[0m")
                    print(f"\033[92m✅[Main] Flowcell add to succesful processing list\033[0m")
                else:
                    add_to_skip_flowcells(	path_to_file    =	SKIP_list_save,
                                            flowcell	=	specific_flowcell, 
                                            reason		=	f"Error in {specific_flowcell} processed")
                    print(f"\033[91m❌[Main] Failed to process flowcell: {specific_flowcell}\033[0m")
                    print(f"\033[91m❌[Main] Add flowcell {specific_flowcell} to skip list\033[0m")
                continue
            if not wait_and_retry(wait_hours    =   5):
                    break
        except Exception as e:
            error_msg = f"ERROR in main loop: {str(e)}"
            print(f"\033[91m{error_msg}\033[0m")
            print(f"Traceback: {traceback.format_exc()}")
            
            print("\033[93mWaiting 1 hour before retry...\033[0m")
            time.sleep(4 * 60 * 60)

if __name__ == "__main__":
    main()