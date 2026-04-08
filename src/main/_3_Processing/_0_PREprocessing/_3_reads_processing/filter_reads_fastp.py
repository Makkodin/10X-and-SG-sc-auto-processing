import os
import re
import subprocess
from glob import glob
from typing import Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial

def merge_lines(sample: str, fastq_save: str) -> bool:
    merged_pattern = f"{fastq_save}/{sample}_S*_L001_*_001.fastq.gz"
    merged_files = [f for f in glob(merged_pattern) if os.path.basename(f).startswith(sample)]
    if len(merged_files) >= 2:
        print(f"✅[3.0.3 Filter reads] Lines already merged for {sample}")
        return True
    bak_dir = f'{fastq_save}/bak_multilines'
    os.makedirs(bak_dir, exist_ok=True)
    
    def process_read(read: str) -> bool:
        fastq_files = sorted(glob(f"{fastq_save}/{sample}_S*{read}*.gz"))
        fastq_files = [f for f in fastq_files if os.path.basename(f).startswith(sample)]
        if len(fastq_files) <= 1:
            print(f"ℹ️[3.0.3 Filter reads] Only {len(fastq_files)} files for {read} in {sample}, skip merge")
            return True
        print(f"🕒[3.0.3 Filter reads] Merge {len(fastq_files)} files {read} for {sample}")
        
        try:
            basename = os.path.basename(fastq_files[0])
            match = re.search(r"_S(\d+)_", basename)
            if not match:
                print(f"❌[3.0.3 Filter reads] Can't extract _S from {basename}")
                return False
            S_number = match.group(1)
            output_file = f"{fastq_save}/{sample}_S{S_number}_L001_{read}_001.fastq"
            print(f"🕒[3.0.3 Filter reads] Concatenating files to {output_file}")
            with open(output_file, "w") as outfile:
                for file in fastq_files:
                    subprocess.run(["zcat", file], stdout=outfile, check=True)
            for file in fastq_files:
                try:
                    bak_file = f"{bak_dir}/{os.path.basename(file)}"
                    os.rename(file, bak_file)
                    print(f"✅[3.0.3 Filter reads] Moved {os.path.basename(file)} to bak_multilines")
                except Exception as e:
                    print(f"⚠️[3.0.3 Filter reads] Can't move {file}: {e}")
            print(f"🕒[3.0.3 Filter reads] Compressing {output_file}")
            subprocess.run(["pigz", output_file], check=True)
            print(f"✅[3.0.3 Filter reads] Merge {read} completed for {sample}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌[3.0.3 Filter reads] Error merging {read} for {sample}: {e}")
            return False
        except Exception as e:
            print(f"❌[3.0.3 Filter reads] Error merging {read} for {sample}: {e}")
            return False
    results = []
    for read in ['R1', 'R2']:
        result = process_read(read)
        results.append(result)
    return all(results)

def run_fastp_for_sample(
        sample: str, 
        core: int, 
        fastq_save: str, 
        min_length: int, 
        max_len1: int,
        more_arg: List[str]) -> bool:
    filtered_pattern = f"{fastq_save}/{sample}_S*_filtered.fastq.gz"
    filtered_files = [f for f in glob(filtered_pattern) 
                      if os.path.basename(f).startswith(sample)]
    if len(filtered_files) >= 2:
        print(f"✅[3.0.3 Filter reads] FastP already done for {sample}")
        return True
    backup_dir = f'{fastq_save}/bak_before_fastp'
    os.makedirs(backup_dir, exist_ok=True)
    sample_fastq_files = glob(f"{fastq_save}/{sample}_S*.gz")
    r1_files = sorted([x for x in sample_fastq_files 
                      if '_R1_' in x and '_filtered' not in x and os.path.basename(x).startswith(sample)])
    r2_files = sorted([x for x in sample_fastq_files 
                      if '_R2_' in x and '_filtered' not in x and os.path.basename(x).startswith(sample)])
    if not r1_files or not r2_files:
        print(f"❌[3.0.3 Filter reads] Can't find R1/R2 files for {sample}")
        return False
    before_fastp_r1 = r1_files[0]
    before_fastp_r2 = r2_files[0]
    after_fastp_r1 = before_fastp_r1.replace('.fastq.gz', '_filtered.fastq.gz')
    after_fastp_r2 = before_fastp_r2.replace('.fastq.gz', '_filtered.fastq.gz')
    backup_r1 = f"{backup_dir}/{os.path.basename(before_fastp_r1)}"
    backup_r2 = f"{backup_dir}/{os.path.basename(before_fastp_r2)}"
    try:
        if os.path.exists(before_fastp_r1):
            os.rename(before_fastp_r1, backup_r1)
            print(f"✅[3.0.3 Filter reads] Moved {os.path.basename(before_fastp_r1)} to bak_before_fastp")
        if os.path.exists(before_fastp_r2):
            os.rename(before_fastp_r2, backup_r2)
            print(f"✅[3.0.3 Filter reads] Moved {os.path.basename(before_fastp_r2)} to bak_before_fastp")
    except Exception as e:
        print(f"❌[3.0.3 Filter reads] Can't create backup for {sample}: {e}")
        return False
    command = [
        "fastp",
        "-i", backup_r1,
        "-I", backup_r2,
        "-o", after_fastp_r1,
        "-O", after_fastp_r2,
        "-l", str(min_length),
        "--max_len1", str(max_len1),
        "-j", f"{fastq_save}/{sample}_fastp.json",
        "-h", f"{fastq_save}/{sample}_fastp.html",
        "--thread", str(min(core, 8)),
        "--detect_adapter_for_pe",
        "--correction"
    ] + more_arg
    log_file_path = f"{fastq_save}/{sample}_fastp.log"
    print(f"🕒[3.0.3 Filter reads] Running FastP for {sample}")
    try:
        with open(log_file_path, "w") as log_file:
            result = subprocess.run(
                command,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
                check=False)
        if result.returncode == 0:
            print(f"✅[3.0.3 Filter reads] FastP completed successfully for {sample}")
            return True
        else:
            print(f"❌[3.0.3 Filter reads] FastP completed with error for {sample} (code: {result.returncode})")
            try:
                if os.path.exists(backup_r1):
                    os.rename(backup_r1, before_fastp_r1)
                if os.path.exists(backup_r2):
                    os.rename(backup_r2, before_fastp_r2)
            except:
                pass
            return False
    except Exception as e:
        print(f"❌[3.0.3 Filter reads] Error running FastP for {sample}: {str(e)}")
        return False

def run_repair_for_sample(
        sample: str, 
        fastq_save: str) -> bool:
    repair_pattern = f"{fastq_save}/{sample}_S*_filtered_paired.fastq.gz"
    repair_files = [f for f in glob(repair_pattern) 
                    if os.path.basename(f).startswith(sample)]
    if len(repair_files) >= 2:
        print(f"✅[3.0.3 Repair reads] Repair already done for {sample}")
        return True
    backup_dir = f'{fastq_save}/bak_before_repair'
    os.makedirs(backup_dir, exist_ok=True)
    filtered_files = glob(f"{fastq_save}/{sample}_S*_filtered.fastq.gz")
    r1_filtered = sorted([x for x in filtered_files 
                         if '_R1_' in x and os.path.basename(x).startswith(sample)])
    r2_filtered = sorted([x for x in filtered_files 
                         if '_R2_' in x and os.path.basename(x).startswith(sample)])
    if not r1_filtered or not r2_filtered:
        print(f"⚠️[3.0.3 Repair reads] No filtered files for {sample}, skip repair")
        return True
    r1_file = r1_filtered[0]
    r2_file = r2_filtered[0]
    backup_r1 = f"{backup_dir}/{os.path.basename(r1_file)}"
    backup_r2 = f"{backup_dir}/{os.path.basename(r2_file)}"
    try:
        os.rename(r1_file, backup_r1)
        os.rename(r2_file, backup_r2)
        print(f"✅[3.0.3 Repair reads] Moved filtered files to bak_before_repair for {sample}")
    except Exception as e:
        print(f"❌[3.0.3 Repair reads] Can't move files to backup for {sample}: {e}")
        return False
    try:
        r1_decompressed = backup_r1.replace('.gz', '')
        r2_decompressed = backup_r2.replace('.gz', '')
        subprocess.run(["gunzip", "-k", backup_r1], check=True)
        subprocess.run(["gunzip", "-k", backup_r2], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌[3.0.3 Repair reads] Unzip error {sample}: {e}")
        return False
    output_r1 = r1_file.replace('_filtered.fastq.gz', '_filtered_paired.fastq')
    output_r2 = r2_file.replace('_filtered.fastq.gz', '_filtered_paired.fastq')
    singleton_output = f"{backup_dir}/{sample}_singletons.fastq"
    command = [
        "repair.sh",
        f"in1={r1_decompressed}",
        f"in2={r2_decompressed}",
        f"out1={output_r1}",
        f"out2={output_r2}",
        f"outsingle={singleton_output}"]
    log_file_path = f"{fastq_save}/{sample}_repair.log"
    print(f"🕒[3.0.3 Repair reads] Running repair.sh for {sample}")
    try:
        with open(log_file_path, "w") as log_file:
            result = subprocess.run(
                command,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
                check=False)
        if result.returncode == 0:
            subprocess.run(["pigz", output_r1], check=True)
            subprocess.run(["pigz", output_r2], check=True)
            if os.path.exists(r1_decompressed):
                os.remove(r1_decompressed)
            if os.path.exists(r2_decompressed):
                os.remove(r2_decompressed)
            print(f"✅[3.0.3 Repair reads] repair.sh completed successfully for {sample}")
            for pattern in [f"{fastq_save}/{sample}_S*_filtered.fastq.gz"]:
                for file in glob(pattern):
                    if os.path.basename(file).startswith(sample):
                        try:
                            os.remove(file)
                            print(f"✅[3.0.3 Repair reads] Removed intermediate file: {os.path.basename(file)}")
                        except:
                            pass
            return True
        else:
            print(f"❌[3.0.3 Repair reads] repair.sh completed with error for {sample} (code: {result.returncode})")
            if os.path.exists(r1_decompressed):
                os.remove(r1_decompressed)
            if os.path.exists(r2_decompressed):
                os.remove(r2_decompressed)
            return False
    except Exception as e:
        print(f"❌[3.0.3 Repair reads] Error running repair.sh for {sample}: {str(e)}")
        return False

def repair_reads_after_fastp(
        flowcell: str,
        fastq_save: str,
        core: int) -> Optional[str]:
    fastq_flowcell_save = f"{fastq_save}/{flowcell}"
    if not os.path.exists(fastq_flowcell_save):
        print(f"❌[3.0.3 Repair reads] Dir not exist: {fastq_flowcell_save}")
        return None
    filtered_files = glob(f"{fastq_flowcell_save}/*_filtered.fastq.gz")
    samples = list(set([os.path.basename(x).split('_')[0] for x in filtered_files]))
    if not samples:
        print(f"⚠️[3.0.3 Repair reads] Not exist filtered files flowcell {flowcell}")
        return fastq_flowcell_save
    print(f"🕒[3.0.3 Repair reads] Run repair for {len(samples)} samples in {flowcell}")
    with ThreadPoolExecutor(max_workers=min(core, 4)) as executor:
        futures = [executor.submit(run_repair_for_sample, sample, fastq_flowcell_save) 
                  for sample in samples]
        results = []
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"❌[3.0.3 Repair reads] Error in repair: {e}")
                results.append(False)
    success_count = sum(results)
    print(f"✅[3.0.3 Repair reads] Completed: {success_count}/{len(samples)} samples completed successfully")
    return fastq_flowcell_save

def fastp_reads_with_repair(
        fastq_save: str,
        flowcell: str,
        core: int = 16,
        min_length: int = 60,
        max_len1: int = 150,
        more_arg: List[str] = None,
        run_repair: bool = True,
        parallel_samples: int = 3) -> Optional[str]:
    if more_arg is None:
        more_arg = []
    fastq_flowcell_save = f"{fastq_save}/{flowcell}"
    if not os.path.exists(fastq_flowcell_save):
        print(f"❌[3.0.3 Filter reads] Directory does not exist: {fastq_flowcell_save}")
        return None
    fastq_files = [
        x for x in sorted(glob(f'{fastq_flowcell_save}/*.fastq.gz')) 
        if 'Undetermined' not in x and os.path.basename(x).endswith('.fastq.gz')
    ]
    if not fastq_files:
        print(f"❌[3.0.3 Filter reads] No FASTQ files found in {fastq_flowcell_save}")
        return None
    samples = []
    for file_path in fastq_files:
        basename = os.path.basename(file_path)
        match = re.match(r'^(.+?)_S\d+_', basename)
        if match:
            sample_name = match.group(1)
            if sample_name not in samples:
                samples.append(sample_name)
    print(f"🕒[3.0.3 Filter reads] Found {len(samples)} samples in flowcell {flowcell}")
    samples_to_process = []
    samples_already_processed = []
    for sample in samples:
        if run_repair:
            repair_pattern = f"{fastq_flowcell_save}/{sample}_S*_filtered_paired.fastq.gz"
            repair_files = [f for f in glob(repair_pattern) 
                           if os.path.basename(f).startswith(sample)]
            if len(repair_files) >= 2:
                samples_already_processed.append(sample)
                print(f"✅[3.0.3 Filter reads] Sample already processed (with repair): {sample}")
                continue
        else:
            filtered_pattern = f"{fastq_flowcell_save}/{sample}_S*_filtered.fastq.gz"
            filtered_files = [f for f in glob(filtered_pattern) 
                            if os.path.basename(f).startswith(sample)]
            if len(filtered_files) >= 2:
                samples_already_processed.append(sample)
                print(f"✅[3.0.3 Filter reads] Sample already processed (filtered only): {sample}")
                continue
        samples_to_process.append(sample)
    print(f"🕒[3.0.3 Filter reads] Already processed: {len(samples_already_processed)} samples")
    print(f"🕒[3.0.3 Filter reads] Need to process: {len(samples_to_process)} samples")
    print(f"🕒[3.0.3 Filter reads] Parallel processing: up to {parallel_samples} samples at once")
    if not samples_to_process:
        print(f"✅[3.0.3 Filter reads] All samples already processed for flowcell {flowcell}")
        return fastq_flowcell_save
    def process_sample(sample: str) -> bool:
        try:
            r1_files = sorted(glob(f"{fastq_flowcell_save}/{sample}_S*_R1_*.gz"))
            r1_files = [f for f in r1_files if os.path.basename(f).startswith(sample)]
            if len(r1_files) > 1:
                merged_pattern = f"{fastq_flowcell_save}/{sample}_S*_L001_*_001.fastq.gz"
                merged_files = [f for f in glob(merged_pattern) 
                              if os.path.basename(f).startswith(sample)]
                if len(merged_files) < 2:
                    print(f"🕒[3.0.3 Filter reads] Merging lines for {sample} ({len(r1_files)} R1 files)")
                    if not merge_lines(sample, fastq_flowcell_save):
                        print(f"❌[3.0.3 Filter reads] Merge failed for {sample}")
                        return False
                else:
                    print(f"✅[3.0.3 Filter reads] Lines already merged for {sample}")
            print(f"🕒[3.0.3 Filter reads] Running fastp for {sample}")
            fastp_success = run_fastp_for_sample(
                sample=sample,
                core=max(2, core // parallel_samples),
                fastq_save=fastq_flowcell_save,
                min_length=min_length,
                max_len1=max_len1,
                more_arg=more_arg)
            if not fastp_success:
                return False
            if run_repair:
                print(f"🕒[3.0.3 Filter reads] Running repair for {sample}")
                repair_success = run_repair_for_sample(sample, fastq_flowcell_save)
                return repair_success
            return True
        except Exception as e:
            print(f"❌[3.0.3 Filter reads] Error processing {sample}: {str(e)}")
            return False

    results = []
    with ThreadPoolExecutor(max_workers=parallel_samples) as executor:
        future_to_sample = {executor.submit(process_sample, sample): sample 
                          for sample in samples_to_process}
        completed = 0
        for future in as_completed(future_to_sample):
            sample = future_to_sample[future]
            completed += 1
            try:
                result = future.result()
                results.append(result)
                if result:
                    print(f"✅[3.0.3 Filter reads {completed}/{len(samples_to_process)}] Completed: {sample}")
                else:
                    print(f"❌[3.0.3 Filter reads {completed}/{len(samples_to_process)}] Failed: {sample}")
            except Exception as e:
                print(f"❌[3.0.3 Filter reads {completed}/{len(samples_to_process)}] Error: {sample}: {str(e)}")
                results.append(False)
    success_count = sum(results)
    print(f"✅[3.0.3 Filter reads] Completed: {success_count}/{len(samples_to_process)} samples processed successfully")
    return fastq_flowcell_save