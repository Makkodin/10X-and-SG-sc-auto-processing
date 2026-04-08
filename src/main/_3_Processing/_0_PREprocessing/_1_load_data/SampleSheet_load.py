import os
import subprocess
from glob import glob
from typing import Optional


def load_sample_sheet_flowcell(
        flowcell    :   str,
        user        :   str, 
        password    :   str,
        load_bcl    :   str, 
        save_fastq  :   str,
        ) -> bool:
    ss_flowcell_path = f"{load_bcl}/{flowcell}"
    access_ss = []
    
    if not os.path.exists(ss_flowcell_path):
        ss_flowcell_path    =   f"{user}@cs11:{load_bcl}/{flowcell}/*.csv"
        access_ss           =   ["sshpass", "-p", f"{password}"]
    else:
        ss_flowcell_path    =   f"{ss_flowcell_path}/*.csv"
    os.makedirs(f"{save_fastq}/{flowcell}", exist_ok=True)
    load_ss_cmd = access_ss + [
        "rsync", "--ignore-existing", "--progress",
        ss_flowcell_path, f"{save_fastq}/{flowcell}/"]
    try:
        result = subprocess.run(
            load_ss_cmd,
            check   =   False,
            stdout  =   subprocess.PIPE,
            stderr  =   subprocess.PIPE,
            text    =   True
        )
        samplesheet_files = glob(f"{save_fastq}/{flowcell}/*.csv")
        if len(samplesheet_files) == 1:
            print(f"✅[3.0.1 Load SampleSheet] SampleSheet loaded for {flowcell}")
            return True
        else:
            alt_patterns = [
                f"{save_fastq}/{flowcell}/*.csv"]
            for pattern in alt_patterns:
                samplesheet_files = glob(pattern)
                if len(samplesheet_files) >= 1:
                    print(f"✅[3.0.1 Load SampleSheet] SampleSheet found for {flowcell}")
                    return True
            print(f"❌[3.0.1 Load SampleSheet] No SampleSheet for {flowcell}")
            return False
            
    except Exception as e:
        print(f"❌[3.0.1 Load SampleSheet] Error for {flowcell}: {str(e)}")
        return False