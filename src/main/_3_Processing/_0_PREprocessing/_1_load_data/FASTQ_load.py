import os
import subprocess
from glob import glob
from typing import Optional

def load_fastq(
        sample_id   :   str, 
        flowcell    :   str,
        user        :   str, 
        password    :   str,     
        load_fastq  :   str, 
        save_fastq  :   str,
        check_existing: bool = True
        ) -> bool:
    
    fastq_flowcell_path = f"{load_fastq}/{flowcell}_fastq4"
    if check_existing:
        target_patterns = [
            f"{save_fastq}/{flowcell}/{sample_id}_S*.fastq.gz",
            f"{save_fastq}/{flowcell}/{sample_id}_S*_filtered*.fastq.gz",
            f"{save_fastq}/{flowcell}/{sample_id}_S*_filtered_paired*.fastq.gz"
        ]
        for pattern in target_patterns:
            existing_files = [f for f in glob(pattern) 
                            if os.path.basename(f).startswith(f"{sample_id}_S")]
            if existing_files:
                print(f"✅[3.0.1 Load FASTQ] Files already exist for {flowcell}:{sample_id} ({len(existing_files)} files)")
                return True
        backup_dirs = ['bak_multilines', 'bak_before_fastp', 'bak_before_repair']
        for backup_dir in backup_dirs:
            backup_path = f"{save_fastq}/{flowcell}/{backup_dir}"
            if os.path.exists(backup_path):
                backup_pattern = f"{backup_path}/{sample_id}_S*.fastq.gz"
                backup_files = [f for f in glob(backup_pattern) 
                              if os.path.basename(f).startswith(f"{sample_id}_S")]
                if backup_files:
                    print(f"✅[3.0.1 Load FASTQ] Files exist in {backup_dir} for {flowcell}:{sample_id}")
                    return True
    access_fastq = []
    if not os.path.exists(fastq_flowcell_path):
        fastq_flowcell_path = f"{user}@cs11:{load_fastq}/{flowcell}_fastq4/{sample_id}_S*.fastq.gz"
        access_fastq = ["sshpass", "-p", password]
    else:
        fastq_flowcell_path = f"{fastq_flowcell_path}/{sample_id}_S*.fastq.gz"
    os.makedirs(f"{save_fastq}/{flowcell}", exist_ok=True)
    load_fastq_cmd = access_fastq + [
        "rsync", "-r", "--ignore-existing", "--progress",
        fastq_flowcell_path, f"{save_fastq}/{flowcell}/"
    ]
    try:
        print(f"🕒[3.0.1 Load FASTQ] Loading files for {flowcell}:{sample_id}")
        result = subprocess.run(
            load_fastq_cmd,
            check   =   False,
            stdout  =   subprocess.PIPE,
            stderr  =   subprocess.PIPE,
            text    =   True)
        pattern = f"{save_fastq}/{flowcell}/{sample_id}_S*.fastq.gz"
        count_fastq_files = [f for f in glob(pattern) 
                           if os.path.basename(f).startswith(f"{sample_id}_S")]
        if len(count_fastq_files) > 0:
            print(f"✅[3.0.1 Load FASTQ] Loaded {len(count_fastq_files)} files for {flowcell}:{sample_id}")
            return True
        else:
            print(f"❌[3.0.1 Load FASTQ] No files found for {flowcell}:{sample_id}")
            return False
            
    except Exception as e:
        print(f"❌[3.0.1 Load FASTQ] Error for {flowcell}:{sample_id}: {str(e)}")
        return False