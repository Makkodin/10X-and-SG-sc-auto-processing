from main._1_PATHs.results import ResultsType
from main._1_PATHs.tools import ToolsType
from glob import glob
import pandas as pd
import os
import shutil
import time
import subprocess
from typing import Dict, List, Any
from main._3_Data.postprocessing.stat import collect_and_save_statistics
from main._3_Data.postprocessing.email_reporter import archive_and_send_report

# Counts the total number of files in a directory and its subdirectories.
def count_files_in_dir(root_dir: str) -> int:
    """
    :param root_dir: Path to the root directory.
    :return: Total number of files.
    """
    return sum(len(files) for _, _, files in os.walk(root_dir))


# Checks for generated reports, renames them, moves to a summary folder, 
# and synchronizes data with remote storage (ceph). Deletes local files after successful transfer.
def check_and_move_reports(
    runsheet: pd.DataFrame,
    runsheet_path: str,
    flowcell: str,
    fastq_res_folder: str,
    password: str,
    sender_email:str, 
    sender_password:str,
    results=ResultsType,
    toolpath=ToolsType,

    work_run: str = '/mnt/raid0/ofateev/projects/SC_auto'
):
    """
    :param runsheet: DataFrame containing sample metadata including Sample_ID and SEQtype.
    :param runsheet_path: Path to the original runsheet file.
    :param flowcell: Flowcell identifier used in result directories.
    :param fastq_res_folder: Path to FASTQ result folder to be removed after transfer.
    :param password: Password for sudo/sshpass command.
    :param results: Object containing result path parameters by sequencing type.
    :param toolpath: Object mapping sequencing types to tool paths.
    :param work_run: Base path where local results are stored. Default is '/mnt/raid0/ofateev/projects/SC_auto'.
    """

    # Initialize dataframe and columns
    samples_parse_df                =   runsheet.copy()
    samples_parse_df['Report_path'] =   "Error"
    samples_parse_df['Stat_path']   =   "Error"
    samples_parse_df['Local_path']  =   "Error"
    samples_parse_df['Ceph_path']   =   "Error"
    res_folder_local = None

    # Loop through each sample to find report paths
    for i in range(len(samples_parse_df)):
        _sample     =   samples_parse_df.iloc[i]['Sample_ID']
        _seq_type   =   samples_parse_df.iloc[i]['SEQtype']

        if pd.isna(_seq_type):
            print(f"❌[Check & move] SEQtype is missing for Sample_ID: {_sample}")
            continue

        try:
            # Get report postfix based on sequencing type
            _postfix_report     =   results[_seq_type]._get_params()['postfix']
            _postfix_stats      =   results[_seq_type]._get_params()['stat']
            
        except KeyError:
            print(f"❌[Check & move] Unknown SEQtype '{_seq_type}' for Sample_ID: {_sample}")
            continue

        # Check for VDJ-type override
        if 'VDJ_type' in samples_parse_df.columns and not pd.isna(samples_parse_df.iloc[i]['VDJ_type']):
            _seq_type                           =   'SC_SeekGene_VDJ'
            samples_parse_df.loc[i, 'SEQtype']  =   "SC_SeekGene_RNA|SC_SeekGene_VDJ"

        # Build paths for local and remote storage
        result_dir      =   f"{work_run}/{results[_seq_type]._get_params()['local']}"
        ceph_res_dir    =   f"{results[_seq_type]._get_params()['ceph']}/{toolpath[_seq_type]._get_params()}"

        if not os.path.exists(ceph_res_dir):
            os.makedirs(ceph_res_dir, exist_ok=True)

        # Search for report file
        report_path =   glob(f'{result_dir}/{flowcell}/{_sample}*/*{_postfix_report}')
        stat_path   =   glob(f'{result_dir}/{flowcell}/{_sample}*/*{_postfix_stats}')

        if report_path:
            samples_parse_df.loc[i, 'Report_path']  =   report_path[0]
            samples_parse_df.loc[i, 'Stat_path']    =   stat_path[0] if stat_path else "Error"
            samples_parse_df.loc[i, 'Local_path']   =   result_dir
            samples_parse_df.loc[i, 'Ceph_path']    =   ceph_res_dir
    
    # Save updated runsheet
    samples_parse_df.to_csv(runsheet_path, index=False)

    # Check for missing reports
    error_samples   =   samples_parse_df[samples_parse_df['Report_path'] == 'Error']
    if not error_samples.empty:
        print(f'❌[Check & move] Not completed report.html for: {error_samples["Sample_ID"].to_list()}')
        return False

    # Create summary folder and copy renamed reports
    set_seq_type    =   samples_parse_df['SEQtype'].drop_duplicates().tolist()
    
    for seq_type in set_seq_type:
        seq_type_res    =   samples_parse_df[samples_parse_df['SEQtype'] == seq_type]
        if seq_type_res.empty:
            continue
            
        result_dir  =   seq_type_res.iloc[0]['Local_path']
        sum_path    =   f"{result_dir}/{flowcell}/{flowcell}-sum"
        os.makedirs(sum_path, exist_ok=True)

        # Collect statistics before copying files
        print(f"🕒[Check & move] Collecting statistics for {seq_type}...")
        collect_and_save_statistics(seq_type_res, sum_path, flowcell)

        # Handle SC_SeekGene_FullRNA specific files
        if seq_type == 'SC_SeekGene_FullRNA':
            full_rna_folders = [
                'bak_multilines', 
                'bak_before_fastp', 
                'bak_before_repair'
            ]
            
            for folder in full_rna_folders:
                folder_path     =   f'{fastq_res_folder}/{folder}'
                if os.path.exists(folder_path):
                    shutil.copytree(folder_path, f'{sum_path}/{folder}', dirs_exist_ok=True)
                    time.sleep(2)
            
            # Copy fastp reports
            for pattern in ["fastp_-l*", "*.log"]:
                for file_path in glob(f"{fastq_res_folder}/{pattern}"):
                    file_name   =   os.path.basename(file_path)
                    shutil.copy2(file_path, f'{sum_path}/{file_name}')
                    time.sleep(1)
            
            # Copy filtered fastq files
            os.makedirs(f"{sum_path}/after_fastp", exist_ok=True)
            for fastq_path in glob(f"{fastq_res_folder}/*_filtered.fastq.gz"):
                file_name       =   os.path.basename(fastq_path)
                shutil.copy2(fastq_path, f'{sum_path}/after_fastp/{file_name}')
                time.sleep(1)
        
        # Copy reports and plots for all samples
        reports_copied  =   0
        plots_copied    =   0
        
        for _, row in seq_type_res.iterrows():
            _sample         =   row['Sample_ID']
            _report_path    =   row['Report_path']
            _stat_path      =   row['Stat_path']

            # Copy annotation plots
            sample_dir = os.path.dirname(_report_path)
            plot_patterns   = [
                                f"{sample_dir}/*.png",
                                f"{sample_dir}/step3/filtered_feature_bc_matrix/*.png"
                            ]
            
            for pattern in plot_patterns:
                for plot_path in glob(pattern):
                    plot_name       =   f'{_sample}_{os.path.basename(plot_path)}'
                    shutil.copy2(plot_path, f'{sum_path}/{plot_name}')
                    plots_copied    +=  1

            # Copy report file
            report_name         =   f'{_sample}-report.html'
            shutil.copy2(_report_path, f'{sum_path}/{report_name}')
            reports_copied      +=  1

        print(f"✅[Check & move] Move to sum dir {seq_type}: {reports_copied}/{len(seq_type_res)} reports")
        print(f"✅[Check & move] Move to sum dir {seq_type}: {plots_copied} plots")

        # Save run sheet locally
        res_folder_local    =   f"{result_dir}/{flowcell}"
        shutil.copy2(runsheet_path, f"{res_folder_local}/{os.path.basename(runsheet_path)}")
        print(f"✅[Check & move] Move SampleSheet to sum dir: {os.path.basename(runsheet_path)}")

        # Email report
        ceph_paths  =   seq_type_res['Ceph_path'].unique()
        email_success = archive_and_send_report(
                    sum_path        =   sum_path,
                    flowcell        =   flowcell,
                    ceph_paths      =   ceph_paths,
                    config_path     =   f'{work_run}/1.Data/Info/email_config.ini',
                    sender_email    =   sender_email,
                    sender_password =   sender_password,
                    dry_run         =   False
                )

        # Sync with remote storage (ceph)
       
        
        if len(ceph_paths) == 1:
            ceph_res_dir = ceph_paths[0]
            load_com = [
                'sshpass', '-p', password,
                'sudo', 'rsync', '-r',
                '--no-links', '--checksum', '--progress',
                res_folder_local,
                f'{ceph_res_dir}/'
            ]
            
            try:
                print(f"🕒[Check & move] Start move results to ceph: {ceph_res_dir}")
                subprocess.run(load_com, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                time.sleep(10)
                print(f"✅[Check & move] Move to {ceph_res_dir} ready!")
                
                # Verify transfer and remove local files
                local_count     =   count_files_in_dir(res_folder_local)
                remote_count    =   count_files_in_dir(f"{ceph_res_dir}/{flowcell}")
                remove_com      =   ['sshpass', '-p', password, 'sudo', 'rm', '-rf', res_folder_local]
                
                if local_count == remote_count:
                    print(f"✅[Check & move] Transfer {local_count}/{remote_count} files.")
                    subprocess.run(remove_com, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    time.sleep(5)
                    print("✅[Check & move] All local files removed!")
                else:
                    print(f"❌[Check & move] Transfer {local_count}/{remote_count} files. Not all files transferred.")
                    
            except subprocess.CalledProcessError as e:
                print(f"❌[Check & move] Move error: {e}")
                return False
        else:
            print(f'❌[Check & move] Error in ceph_res_path: {ceph_paths}')
            return False

    # Clean up temporary files
    
    try:
        remove_com = ['sshpass', '-p', password, 'sudo', 'rm', '-rf', fastq_res_folder, runsheet_path]
        subprocess.run(remove_com, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("✅[Check & move] All FASTQ files and temporary files removed!")
    except subprocess.CalledProcessError as e:
        print(f"❌[Check & move] Error removing temporary files: {e}")
    
    return True