import warnings
warnings.filterwarnings("ignore")
warnings.simplefilter("ignore")

import os
import subprocess
from glob import glob
from typing import Optional
from bs4 import BeautifulSoup as Soup


def get_runinfo(file: str) -> Optional[str]:
    try:
        with open(file, 'r', encoding='utf-8') as xml_file:
            soup = Soup(xml_file.read(), features='xml')
        reads = soup.find_all('Read')
        index_read = ['Y', 'I', 'Y', 'Y']
        cycles = [read['NumCycles'] for read in reads if 'NumCycles' in read.attrs]
        
        if len(cycles) != len(index_read):
            print(f"⚠️[3.0.3 Demultiplex] Cycle length ({len(cycles)}) != index length ({len(index_read)})")
            return None
        result = ','.join(f"{index}{cycle}" for index, cycle in zip(index_read, cycles))
        print(f"✅[3.0.3 Demultiplex] Flag --use-bases-mask: {result}")
        return result
    except FileNotFoundError:
        print(f"❌[3.0.3 Demultiplex] File not found: {file}")
        return None
    except KeyError as e:
        print(f"❌[3.0.3 Demultiplex] Parse error XML: key zero exist {e}")
        return None
    except Exception as e:
        print(f"❌[3.0.3 Demultiplex] Parse error RunInfo.xml: {e}")
        return None


def bcl2fastq(
        bcl     :   str,
        fastq   :   str) -> Optional[str]:
    if not bcl or not os.path.exists(bcl):
        print(f"❌[3.0.3 Demultiplex] BCL not exist: {bcl}")
        return None
    flowcell = os.path.basename(bcl)
    samplesheet_files = glob(f'{bcl}/*.csv')
    if not samplesheet_files:
        samplesheet_files = glob(f'{bcl}/*.CSV')
    if not samplesheet_files:
        print(f"❌[3.0.3 Demultiplex] Samplesheet not found {bcl}")
        return None
    samplesheet = samplesheet_files[0]
    output_dir = f"{fastq}/{flowcell}"
    os.makedirs(output_dir, exist_ok=True)
    command = [
        "bcl2fastq",
        "-l", "WARNING",
        "--runfolder-dir", bcl,
        "--sample-sheet", samplesheet,
        "--output-dir", output_dir,
        "--stats-dir", f"{output_dir}/Stats",
        "--reports-dir", f"{output_dir}/Reports",
        "--no-lane-splitting",
        "--ignore-missing-bcl",
        "--ignore-missing-filter",
        "--ignore-missing-positions"
    ]
    copy_ss = ['cp', '-f', samplesheet, output_dir]
    log_path = f"{output_dir}/bcl2fastq.log"
    print(f"🕒[3.0.3 Demultiplex] Run bcl2fastq for {flowcell}")
    print(f"🕒[3.0.3 Demultiplex] Samplesheet: {samplesheet}")
    print(f"🕒[3.0.3 Demultiplex] Out dir: {output_dir}")
    try:
        with open(log_path, "w") as log_file:
            result = subprocess.run(
                command,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                check=False
            )
        subprocess.run(copy_ss, check=False, capture_output=True)
        if result.returncode == 0:
            print(f"✅[3.0.3 Demultiplex] bcl2fastq complect {flowcell}")
            fastq_files = glob(f"{output_dir}/*.fastq.gz")
            if fastq_files:
                print(f"✅[3.0.3 Demultiplex] Created {len(fastq_files)} FASTQ files")
                return output_dir
            else:
                print(f"⚠️[3.0.3 Demultiplex] FASTQ files not created, check log: {log_path}")
                return None
        else:
            print(f"❌[3.0.3 Demultiplex] bcl2fastq exist with error (code: {result.returncode})")
            print(f"🕒[3.0.3 Demultiplex] Check logs: {log_path}")
            fastq_files = glob(f"{output_dir}/*.fastq.gz")
            if fastq_files:
                print(f"⚠️[3.0.3 Demultiplex] Find {len(fastq_files)} FASTQ files")
                return output_dir
            return None
        
    except Exception as e:
        print(f"❌[3.0.3 Demultiplex] Ошибка при запуске bcl2fastq: {str(e)}")
        return None


def bcl2fastq_atac(
        bcl     :   str,
        fastq   :   str) -> Optional[str]:
    if not bcl or not os.path.exists(bcl):
        print(f"❌[3.0.3 Demultiplex ATAC] BCL not exist: {bcl}")
        return None
    flowcell = os.path.basename(bcl)
    samplesheet_files = glob(f'{bcl}/*.csv')
    if not samplesheet_files:
        samplesheet_files = glob(f'{bcl}/*.CSV')
    if not samplesheet_files:
        print(f"❌[3.0.3 Demultiplex ATAC] Samplesheet not found  {bcl}")
        return None
    samplesheet = samplesheet_files[0]
    runinfo_files = glob(f'{bcl}/RunInfo.xml')
    if not runinfo_files:
        print(f"❌[3.0.3 Demultiplex ATAC] RunInfo.xml not found {bcl}")
        return None
    runinfo = runinfo_files[0]
    runinfo_mask = get_runinfo(runinfo)
    if not runinfo_mask:
        print(f"❌[3.0.3 Demultiplex ATAC] Mask export error RunInfo.xml")
        return None
    output_dir = f"{fastq}/{flowcell}"
    os.makedirs(output_dir, exist_ok=True)
    
    command = [
        "bcl2fastq",
        "-l", "WARNING",
        f"--use-bases-mask={runinfo_mask}",
        "--runfolder-dir", bcl,
        "--sample-sheet", samplesheet,
        "--output-dir", output_dir,
        "--stats-dir", f"{output_dir}/Stats",
        "--reports-dir", f"{output_dir}/Reports",
        "--create-fastq-for-index-reads",
        "--minimum-trimmed-read-length", "8",
        "--mask-short-adapter-read", "8",
        "--no-lane-splitting",
        "--ignore-missing-bcl",
        "--ignore-missing-filter",
        "--ignore-missing-positions"
    ]
    copy_ss = ['cp', '-f', samplesheet, output_dir]
    log_path = f"{output_dir}/bcl2fastq_atac.log"
    print(f"🕒[3.0.3 Demultiplex ATAC] Start run bcl2fastq for ATAC {flowcell}")
    print(f"🕒[3.0.3 Demultiplex ATAC] Reads mask: {runinfo_mask}")
    print(f"🕒[3.0.3 Demultiplex ATAC] Output dir: {output_dir}")
    try:
        with open(log_path, "w") as log_file:
            result = subprocess.run(
                command,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                check=False
            )
        subprocess.run(copy_ss, check=False, capture_output=True)
        if result.returncode == 0:
            print(f"✅[3.0.3 Demultiplex ATAC] bcl2fastq completed successfully {flowcell}")
            fastq_files = glob(f"{output_dir}/*.fastq.gz")
            if fastq_files:
                print(f"✅[3.0.3 Demultiplex ATAC] Create {len(fastq_files)} FASTQ files")
                return output_dir
            else:
                print(f"⚠️[3.0.3 Demultiplex ATAC] FASTQ files not create, check log: {log_path}")
                return None
        else:
            print(f"❌[3.0.3 Demultiplex ATAC] bcl2fastq exist error (code: {result.returncode})")
            print(f"🕒[3.0.3 Demultiplex ATAC] Check logs: {log_path}")
            fastq_files = glob(f"{output_dir}/*.fastq.gz")
            if fastq_files:
                print(f"⚠️[3.0.3 Demultiplex ATAC] Find {len(fastq_files)} FASTQ files")
                return output_dir
            return None 
    except Exception as e:
        print(f"❌[3.0.3 Demultiplex ATAC] Error bcl2fastq: {str(e)}")
        return None