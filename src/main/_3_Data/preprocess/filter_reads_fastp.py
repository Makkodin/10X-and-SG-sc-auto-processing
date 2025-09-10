import subprocess
import os
import re
from glob import glob
from typing import Optional
from functools import partial
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ThreadPoolExecutor, as_completed


def merge_lines(sample: str, fastq_save: str):
    """
    Merge multi-line FASTQ.gz files for R1 and R2 in parallel.
    """
    bak_dir = f'{fastq_save}/bak_multilines'
    if not os.path.exists(bak_dir):
        os.makedirs(bak_dir, exist_ok=True)

    def process_read(read):
        fastq_files = glob(f"{fastq_save}/{sample}*{read}*.gz")
        if not fastq_files:
            print(f"❌[Filter reads] Files {sample},{read} not found.")
            return False

        try:
            S_name = re.search(r"_S\d+_", fastq_files[0]).group().replace('_', '')
            output_file = f"{fastq_save}/{sample}_{S_name}_L001_{read}_001_merge.fastq"

            # Merge files
            with open(output_file, "w") as outfile:
                subprocess.run(["zcat", *fastq_files], stdout=outfile, check=True)

            # Move originals to backup
            subprocess.run(["mv", *fastq_files, bak_dir], check=True)

            # Compress and rename
            subprocess.run(["pigz", output_file], check=True)
            new_output = output_file.replace('_merge.fastq', '.fastq') + ".gz"
            os.rename(f"{output_file}.gz", new_output)

            return True

        except subprocess.CalledProcessError as e:
            print(f"❌[Filter reads] Error merging lines for {sample}, {read}: {e}")
            return False

    # Parallel processing of R1 and R2
    results = []
    with ThreadPoolExecutor() as executor:
        future_to_read = {executor.submit(process_read, read): read for read in ['R1', 'R2']}
        for future in as_completed(future_to_read):
            read = future_to_read[future]
            try:
                result = future.result()
                if not result:
                    print(f"❌[Filter reads] Failed to process {read}")
            except Exception as exc:
                print(f"❌[Filter reads] Exception while processing {read}: {exc}")


def run_fastp_for_sample(sample: str, 
                         core:int, 
                         fastq_save: str, 
                         min_length: int, 
                         max_len1: int,
                         more_arg: list):
    backup_dir = f'{fastq_save}/bak_before_fastp'
    os.makedirs(backup_dir, exist_ok=True)

    sample_fastq_files = glob(f"{fastq_save}/{sample}*.gz") + glob(f"{fastq_save}/bak_before_fastp/{sample}*.gz")
    r1_files = [x for x in sample_fastq_files if 'R1' in x]
    r2_files = [x for x in sample_fastq_files if 'R2' in x]

    if not r1_files or not r2_files:
        print(f"❌[Filter reads] Missing R1/R2 files for {sample}.")
        return

    before_fastp_r1 = r1_files[0]
    before_fastp_r2 = r2_files[0]

    after_fastp_r1 = before_fastp_r1.replace('.fastq.gz', '_filtered.fastq.gz')
    after_fastp_r2 = before_fastp_r2.replace('.fastq.gz', '_filtered.fastq.gz')

    backup_r1 = f"{backup_dir}/{os.path.basename(before_fastp_r1)}"
    backup_r2 = f"{backup_dir}/{os.path.basename(before_fastp_r2)}"

    try:
        os.rename(before_fastp_r1, backup_r1)
        os.rename(before_fastp_r2, backup_r2)
    except Exception as e:
        print(f"❌[Filter reads] Could not move files to backup: {e}")
        return

    command = [
        "fastp",
        "-i", backup_r1,
        "-I", backup_r2,
        "-o", after_fastp_r1,
        "-O", after_fastp_r2,
        "-l", str(min_length),
        "-j", f"{fastq_save}/fastp_-l{min_length}.json",
        "-h", f"{fastq_save}/fastp_-l{min_length}.html",
        "--thread", str(core)
    ] + more_arg
            #"-b", str(max_len1),

    log_file_path = f"{fastq_save}/{sample}_fastp.log"
    print(f"🕒[Filter reads] Running FastP for {sample}: {' '.join(command)}")

    try:
        with open(log_file_path, "w") as log_file:
            result = subprocess.run(
                command,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
                check=True
            )
        print(f"✅[Filter reads] FastP completed successfully for {sample}.")
    except subprocess.CalledProcessError as e:
        print(f"❌[Filter reads] FastP failed for {sample}. Return code: {e.returncode}")
        return
    
def run_repair_for_sample(sample: str, fastq_save: str):
    backup_dir_2 = f'{fastq_save}/bak_before_repair'
    os.makedirs(backup_dir_2, exist_ok=True)
    
    # Find filtered files
    filtered_files = glob(f"{fastq_save}/{sample}*_filtered.fastq.gz")
    r1_filtered = [x for x in filtered_files if 'R1' in x]
    r2_filtered = [x for x in filtered_files if 'R2' in x]
    
    if not r1_filtered or not r2_filtered:
        print(f"❌[Repair reads] Missing filtered R1/R2 files for {sample}.")
        return False
    
    r1_file = r1_filtered[0]
    r2_file = r2_filtered[0]
    
    # Move to backup before repair
    backup_r1 = f"{backup_dir_2}/{os.path.basename(r1_file)}"
    backup_r2 = f"{backup_dir_2}/{os.path.basename(r2_file)}"
    
    try:
        os.rename(r1_file, backup_r1)
        os.rename(r2_file, backup_r2)
    except Exception as e:
        print(f"❌[Repair reads] Could not move files to backup: {e}")
        return False
    
    # Decompress files
    try:
        r1_decompressed = backup_r1.replace('.gz', '')
        r2_decompressed = backup_r2.replace('.gz', '')
        
        subprocess.run(["gunzip", "-k", backup_r1], check=True)
        subprocess.run(["gunzip", "-k", backup_r2], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌[Repair reads] Error decompressing files: {e}")
        return False
    
    # Prepare output file names
    output_r1 = r1_file.replace('_filtered.fastq.gz', '_filtered_paired.fastq')
    output_r2 = r2_file.replace('_filtered.fastq.gz', '_filtered_paired.fastq')
    singleton_output = f"{backup_dir_2}/{sample}_singletons.fastq"
    
    # Run repair.sh
    command = [
        "repair.sh",
        f"in1={r1_decompressed}",
        f"in2={r2_decompressed}",
        f"out1={output_r1}",
        f"out2={output_r2}",
        f"outsingle={singleton_output}"
    ]
    
    log_file_path = f"{fastq_save}/{sample}_repair.log"
    print(f"🕒[Repair reads] Running repair.sh for {sample}: {' '.join(command)}")
    
    try:
        with open(log_file_path, "w") as log_file:
            result = subprocess.run(
                command,
                stdout  =   log_file,
                stderr  =   subprocess.STDOUT,
                text    =   True,
                check   =   True
            )
        print(f"✅[Repair reads] repair.sh completed successfully for {sample}.")
        
        # Compress the repaired files
        subprocess.run(["pigz", output_r1], check=True)
        subprocess.run(["pigz", output_r2], check=True)
        
        # Clean up decompressed files
        os.remove(r1_decompressed)
        os.remove(r2_decompressed)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌[Repair reads] repair.sh failed for {sample}. Return code: {e.returncode}")
        # Clean up in case of error
        try:
            os.remove(r1_decompressed)
            os.remove(r2_decompressed)
        except:
            pass
        return False

def repair_reads_after_fastp(
    flowcell: str,
    fastq_save: str,
    core: int
) -> Optional[str]:
    fastq_flowcell_save = f"{fastq_save}/{flowcell}"
    
    # Get all filtered files to identify samples
    filtered_files = glob(f"{fastq_flowcell_save}/*_filtered.fastq.gz")
    samples = list(set([os.path.basename(x).split('_')[0] for x in filtered_files]))
    
    print(f"🕒[Repair reads] Starting repair process for {len(samples)} samples")
    
    # Run repair for each sample in parallel
    with ThreadPoolExecutor(max_workers=core) as executor:
        futures = []
        for sample in samples:
            future = executor.submit(run_repair_for_sample, sample, fastq_flowcell_save)
            futures.append(future)
        
        # Wait for all tasks to complete
        results = []
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"❌[Repair reads] Exception during repair: {e}")
                results.append(False)
    
    success_count = sum(results)
    print(f"✅[Repair reads] Completed: {success_count}/{len(samples)} samples processed successfully")
    
    return fastq_flowcell_save

def fastp_reads_with_repair(
    flowcell:   str,
    fastq_save: str,
    min_length: int,
    max_len1:   int,
    core:       int,
    more_arg: list = [],
    run_repair: bool = True) -> Optional[str]:
    
    fastq_flowcell_save = f"{fastq_save}/{flowcell}"
    fastq_files = [x for x in sorted(glob(f'{fastq_flowcell_save}/*gz')) if 'Undetermined' not in x]
    
    samples = list(set([x.split('/')[-1].split('_S')[0] for x in fastq_files]))
    check_LINES = [True if '_L002_' in x else False for x in fastq_files]

    if True in check_LINES:
        print("🕒[Filter reads] Detected multiple LINEs for samples. Merging...")
        with ThreadPoolExecutor() as executor:
            executor.map(lambda s: merge_lines(s, fastq_flowcell_save), samples)

    print(f"🕒[Filter reads] Start filtering (FastP): min_length={min_length}, max_len_r1={max_len1}")
    
    # Run FastP
    func = partial(run_fastp_for_sample,
                   core         =   core,
                   fastq_save   =   fastq_flowcell_save,
                   min_length   =   min_length,
                   max_len1     =   max_len1,
                   more_arg     =   more_arg)

    with ThreadPoolExecutor() as executor:
        results = list(executor.map(func, samples))
    
    # Run repair after FastP if enabled
    if run_repair:
        print("🕒[Repair reads] Starting repair process after FastP...")
        repair_reads_after_fastp(flowcell, fastq_save, core)
    
    return fastq_flowcell_save