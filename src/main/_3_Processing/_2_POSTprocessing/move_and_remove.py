import os
from glob import glob
import subprocess
import shutil
from pathlib import Path
import re
import json
from main._1_Config.main_config import multiome_pattern

import os
from glob import glob
import subprocess
import shutil
from pathlib import Path
import re
import json
from main._1_Config.main_config import multiome_pattern

def move_and_remove(flowcell_sample_processed: dict, 
                    password: str):
    try:
        seqtype_groups = {}
        for sample_id, sample_data in flowcell_sample_processed.items():
            seq_type = sample_data.get('SeqType')
            if not seq_type:
                print(f"❌[3.2 Move and remove] Error: Missing SeqType for sample {sample_id}")
                return False
            
            if seq_type not in seqtype_groups:
                seqtype_groups[seq_type] = {}
            seqtype_groups[seq_type][sample_id] = sample_data
        
        print(f"📊[3.2 Move and remove] Found {len(seqtype_groups)} SeqType groups: {list(seqtype_groups.keys())}")
        all_results = []
        for seq_type, samples_group in seqtype_groups.items():
            print(f"📊[3.2 Move and remove] Processing SeqType: {seq_type} ({len(samples_group)} samples)")
            required_keys = ['Path local sum stat', 'Path ceph results', 
                            'Path local results', 'Path data', 'Flowcell']
            for key in required_keys:
                values = set()
                for sample_data in samples_group.values():
                    value = sample_data.get(key)
                    if value:
                        values.add(value)
                if key in ['Path local sum stat', 'Path ceph results', 'Flowcell']:
                    if len(values) > 1:
                        print(f"❌[3.2 Move and remove] Error: {key} has different values in SeqType {seq_type}: {values}")
                        return False
            first_sample = next(iter(samples_group.values()))
            local_sum_stat_dir  = first_sample.get('Path local sum stat')
            ceph_result_dir     = first_sample.get('Path ceph results')
            res_folder_local    = first_sample.get('Path local results')
            flowcell_name       = first_sample.get('Flowcell')
            for sample_id, sample_data in samples_group.items():
                html_pattern = sample_data.get('Path result html prefix')
                if html_pattern:
                    html_files = glob(html_pattern)
                    if not html_files:
                        print(f"❌[3.2 Move and remove] Error: No HTML files found for pattern: {html_pattern}")
                        return False
                    print(f"✅[3.2 Move and remove] Found {len(html_files)} HTML files for {sample_id} in SeqType {seq_type}")
                
                stat_pattern = sample_data.get('Path result stat prefix')
                if stat_pattern:
                    stat_files = glob(stat_pattern)
                    if not stat_files:
                        print(f"❌[3.2 Move and remove] Error: No stat files found for pattern: {stat_pattern}")
                        return False
                    print(f"✅[3.2 Move and remove] Found {len(stat_files)} stat files for {sample_id} in SeqType {seq_type}")
            if local_sum_stat_dir:
                html_files_in_sum_stat = glob(os.path.join(local_sum_stat_dir, "*.html"))
                if not html_files_in_sum_stat:
                    print(f"❌[3.2 Move and remove] Error: No HTML files found in {local_sum_stat_dir}")
                    return False
                print(f"✅[3.2 Move and remove] Found {len(html_files_in_sum_stat)} HTML files in summary directory for SeqType {seq_type}")
            
            if not all([local_sum_stat_dir, ceph_result_dir, res_folder_local, flowcell_name]):
                print(f"❌[3.2 Move and remove] Error: Missing required paths for flowcell {flowcell_name} in SeqType {seq_type}")
                return False
            try:
                mkdir_cmd = [
                    'sshpass', '-p', password, 
                    'sudo', 'mkdir', '-p', ceph_result_dir
                ]
                result = subprocess.run(mkdir_cmd, 
                                        stdout=subprocess.PIPE, 
                                        stderr=subprocess.PIPE, 
                                        text=True)
                if result.returncode != 0:
                    print(f"❌[3.2 Move and remove] Error creating directory {ceph_result_dir}: {result.stderr}")
                    return False
                
                print(f"✅[3.2 Move and remove] Directory {ceph_result_dir} created/verified for SeqType {seq_type}")
                
                load_com = [
                    'sshpass', '-p', password,
                    'sudo', 'rsync', '-r',
                    '--no-links', '--checksum', '--progress',
                    f"{res_folder_local}/",
                    f'{ceph_result_dir}/'
                ]
                print(f"🕒[3.2 Move and remove] Starting rsync for flowcell {flowcell_name} (SeqType {seq_type})...")
                result = subprocess.run(load_com, 
                                        stdout=subprocess.PIPE, 
                                        stderr=subprocess.PIPE, 
                                        text=True)
                if result.returncode != 0:
                    print(f"❌[3.2 Move and remove] Error during rsync for flowcell {flowcell_name} (SeqType {seq_type}): {result.stderr}")
                    return False
                print(f"✅[3.2 Move and remove] Rsync completed successfully for flowcell {flowcell_name} (SeqType {seq_type})")
            except Exception as e:
                print(f"❌[3.2 Move and remove] Error processing flowcell {flowcell_name} (SeqType {seq_type}): {str(e)}")
                return False
            processed_paths = set()
            if res_folder_local and os.path.exists(res_folder_local):
                try:
                    shutil.rmtree(res_folder_local)
                    print(f"🕒[3.2 Move and remove] Removed local results: {res_folder_local} (SeqType {seq_type})")
                except Exception as e:
                    print(f"❌[3.2 Move and remove] Error removing {res_folder_local}: {str(e)}")
                    return False
                processed_paths.add(res_folder_local)
            for sample_data in samples_group.values():
                path_data = sample_data.get('Path data')
                
                if path_data and path_data not in processed_paths:
                    dir_name = os.path.basename(path_data)
                    if re.search(multiome_pattern, dir_name):
                        flowcell_ids = dir_name.split('-')
                        for flowcell_id in flowcell_ids:
                            flowcell_path = os.path.join(os.path.dirname(path_data), flowcell_id)
                            if os.path.exists(flowcell_path) and flowcell_path not in processed_paths:
                                try:
                                    shutil.rmtree(flowcell_path)
                                    print(f"🕒[3.2 Move and remove] Removed paired flowcell data: {flowcell_path} (SeqType {seq_type})")
                                except Exception as e:
                                    print(f"❌[3.2 Move and remove] Error removing {flowcell_path}: {str(e)}")
                                    return False
                                processed_paths.add(flowcell_path)
                    else:
                        if os.path.exists(path_data):
                            try:
                                shutil.rmtree(path_data)
                                print(f"✅[3.2 Move and remove] Removed data directory: {path_data} (SeqType {seq_type})")
                            except Exception as e:
                                print(f"❌[3.2 Move and remove] Error removing {path_data}: {str(e)}")
                                return False
                            processed_paths.add(path_data)
            count_json_results = len(glob(f'{ceph_result_dir}/flowcell_sample_processed*.json'))
            json_filename = f'{ceph_result_dir}/flowcell_sample_processed_{seq_type}_count-{count_json_results + 1}.json'
            with open(json_filename, 'w') as fp:
                json.dump(samples_group, fp, indent=2)
            print(f"✅[3.2 Move and remove] Saved processing info for SeqType {seq_type} to {json_filename}")
            all_results.append(True)
            print(f"✅[3.2 Move and remove] Completed processing for SeqType: {seq_type}")
        if all_results and len(all_results) == len(seqtype_groups):
            print("✅[3.2 Move and remove] All SeqType groups processed successfully")
            return True
        else:
            print(f"❌[3.2 Move and remove] Some SeqType groups failed to process. Processed: {len(all_results)}/{len(seqtype_groups)}")
            return False
    except Exception as e:
        print(f"❌[3.2 Move and remove] Unexpected error: {str(e)}")
        return False