import scanpy as sc
import warnings
from glob import glob
warnings.simplefilter('ignore')
import scparadise
import matplotlib.pyplot as plt
import sys
import os
import traceback
import logging
from io import StringIO
import multiprocessing
import concurrent.futures
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import Dict, Any, List, Tuple, Optional
import subprocess
import time
import inspect

from main._3_Processing._2_POSTprocessing.scRNA_adata._ann_scparadise 	import process_annotation
from main._3_Processing._0_PREprocessing._4_process_flowcell.resource 	import choose_resources, dynamic_import
def processing_flowcell(
    flowcell_sample_processed:dict,
    core:int            =   None,
    mem:int             =   None,
    work_dir:str        =   None 
) -> tuple[dict, bool]:  # Изменен тип возвращаемого значения
    
    samples_num             =   len(flowcell_sample_processed)
    unique_flowcells        =   list({sample_data['Flowcell'] for sample_data in flowcell_sample_processed.values()})
    unique_organisms_name   =   list({sample_data['Organism'] for sample_data in flowcell_sample_processed.values()})
    unique_typeseqs         =   list({sample_data['SeqType'] for sample_data in flowcell_sample_processed.values()})

    if core == None and mem == None:
        per_sample_core, per_sample_mem     =   choose_resources(samples_num)
    else:
        per_sample_core, per_sample_mem     =   core, mem

    total_core      =   max(per_sample_core * samples_num, 4)   # Minimum 4 cores per sample
    total_memory    =   max(per_sample_mem * samples_num, 40)   # Minimum 40 GB RAM per sample

   
    print( "┌───────────────────────────────────────────────────────────────────────────────────────────────────────────────┐")
    print( "│              3.1.2 Flowcell processing info                                                                   │")
    print( "├───────────────────────────────────────────────────────────────────────────────────────────────────────────────┤")
    print(f"│ ℹ️ Start to processed flowcells_:   {unique_flowcells}")
    print(f"│ ℹ️ Sample number________________:   {samples_num}")
    print(f"│ ℹ️ Organism reference___________:   {unique_organisms_name}")
    print(f"│ ℹ️ Type seq_____________________:   {unique_typeseqs}")
    print(f"│ ⚙️ Total resources allocated____:   {total_core} cores, {total_memory} GB RAM")
    print(f"│ ⚙️ Resources per sample_________:   {per_sample_core} cores, {per_sample_mem} GB RAM")
    print( "└───────────────────────────────────────────────────────────────────────────────────────────────────────────────┘")
    
    processes: List[subprocess.Popen]       =   []
    log_files                               =   []
    ceph_paths: List[str]                   =   []
    sample_log_map: Dict[str, Any]          =   {}
    
    successful_samples: List[str]           =   []
    already_processed_samples: List[str]    =   []
    failed_samples: List[str]               =   [] 
    for key, value in flowcell_sample_processed.items():
        os.makedirs(os.path.dirname(value['Path local results']), 
                    exist_ok=True)
        os.makedirs(value['Path local results'], 
                    exist_ok=True)
        
        sample_id   =   value['Sample_ID']
        # Output : run_process, log_file, ceph_res
        proc, log_file, ceph_path = process_sample(
                    sample_processed            =   value,
                    core                        =   per_sample_core,
                    memory                      =   per_sample_mem
        )
        postfix_path_res    =   value['Path result html prefix']    #
        existing_results    =   glob(postfix_path_res)              # '/mnt/raid0/ofateev/projects/SC_auto/2.Results/SG/scRNA/240411_A01022_0750_AHNFHFDRXY/962000685201_h/*_report.html'
        if existing_results:
            already_processed_samples.append(sample_id)
            print(f"✅[3.1.2 Processing] Results already exist for {sample_id}.")
        if proc != None:
            print(f"🕐[3.1.2 Processing] Process {sample_id} started.")
        if proc and log_file:
            processes.append(proc)
            log_files.append(log_file)
            ceph_paths.append(ceph_path)
        sample_log_map[sample_id] = {
            'log_file'      :   log_file,
            'ceph_path'     :   ceph_path,
            'seq_type'      :   value['SeqType'],
            'flowcell'      :   value['Flowcell'],
            'organism'      :   value['Reference name'],
            'organism_name' :   value['Organism'],
            'tissue'        :   value['Tissue'],
            'row_index'     :   len(processes) - 1}
        time.sleep(2)

    for i, proc in enumerate(processes):
        proc.wait()
        sample_id   =   list(sample_log_map.keys())[i]
        if proc.returncode != 0:
            print(f"❌[3.1.2 Processing] Process {sample_id} failed with code: {proc.returncode}")
            failed_samples.append(sample_id)
        else:
            print(f"✅[3.1.2 Processing] Process {sample_id} completed successfully.")
            successful_samples.append(sample_id)
    
    all_successful_samples = successful_samples + already_processed_samples
    all_processing_successful = len(failed_samples) == 0
    
    print("🔄[3.1.2 Processing] Updating sample status...")
    for sample_id in all_successful_samples:
        for key, sample_data in flowcell_sample_processed.items():
            if sample_data['Sample_ID'] == sample_id:
                if sample_data.get('Processed status') == False:
                    sample_data['Processed status'] = True
                    print(f"ℹ️[3.1.2 Processing] Updated 'Processed status' to True for {sample_id}")
                if 'Annotation status' not in sample_data:
                    sample_data['Annotation status'] = False
                    print(f"ℹ️[3.1.2 Processing] Added 'Annotation status' = False for {sample_id}")
                break

    print("🧬[3.1.2 Processing] Checking samples for annotation...")
    samples_for_annotation = []
    if len(all_successful_samples) != 0:
        print(f"✅[3.1.2 Processing] All successful samples: {all_successful_samples}")
    for sample_id in all_successful_samples:
        for key, sample_data in flowcell_sample_processed.items():
            if sample_data['Sample_ID'] == sample_id:
                seq_type    =   sample_data['SeqType']
                vdj_type    =   sample_data.get('VDJ type', '')
                if seq_type in ['SC_SeekGene_RNA', 'SC_TENX_RNA']:
                    samples_for_annotation.append(sample_data)
                    print(f"🧬[3.1.2 Annotation] Sample {sample_id} added for annotation (SeqType: {seq_type})")
                elif seq_type == 'SC_SeekGene_VDJ' and vdj_type == '5':
                    samples_for_annotation.append(sample_data)
                    print(f"🧬[3.1.2 Annotation] Sample {sample_id} added for annotation (SeqType: {seq_type}, VDJ type: {vdj_type})")
                break

    annotation_successful = True
    annotation_failures = []
    
    if samples_for_annotation:
        print(f"🧬[3.1.2 Annotation] Starting annotation for {len(samples_for_annotation)} samples...")
        max_workers = min(len(samples_for_annotation), multiprocessing.cpu_count())
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for sample_data in samples_for_annotation:
                future = executor.submit(
                    run_annotation_task,
                    sample_data =   sample_data,
                    work_dir    =   work_dir
                )
                futures.append(future)
            annotation_results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    annotation_results.append(result)
                    sample_id, success, message = result
                    for key, sample_data in flowcell_sample_processed.items():
                        if sample_data['Sample_ID'] == sample_id:
                            sample_data['Annotation status'] = success
                            break
                    if success:
                        print(f"✅[3.1.2 Annotation] Successfully annotated {sample_id}")
                    else:
                        print(f"❌[3.1.2 Annotation] Failed to annotate {sample_id}: {message}")
                        annotation_successful = False
                        annotation_failures.append(sample_id)
                except Exception as e:
                    print(f"❌[3.1.2 Annotation] Error in annotation task: {str(e)}")
                    annotation_successful = False
                    annotation_failures.append("Unknown sample - exception")
        if annotation_failures:
            print(f"❌[3.1.2 Annotation] Failed annotations: {annotation_failures}")
        
        print(f"🧬[3.1.2 Annotation] Completed annotation for {len(samples_for_annotation)} samples")
    else:
        print("ℹ️[3.1.2 Annotation] No samples require annotation")
    overall_success = all_processing_successful and annotation_successful
    
    return flowcell_sample_processed, overall_success 


def run_annotation_task(sample_data: Dict[str, Any], 
                        work_dir: str
                        ) -> Tuple[str, bool, str]:
    return process_annotation(sample_processed  =   sample_data, 
                              #work_dir          =   work_dir
                              )


def process_sample(
    sample_processed:dict,
    core:       int = 10,
    memory:     int = 100,
    
) -> Tuple[Optional[subprocess.Popen], Optional[Any], Optional[str]]:
 
    add_args: Dict[str, Any] = {}
    if 'TENX' in sample_processed['SeqType']:
        add_args['memory']          =    memory

    if 'SC_TENX_Visium_FFPE' in sample_processed['SeqType']:
        add_args['probe_set']       =    sample_processed['ProbeSet']
        add_args['img']             =    sample_processed['Image FFPE']
        add_args['area']            =    sample_processed['Area FFPE']
        add_args['slide']           =    sample_processed['Slide FFPE']

    if 'SC_TENX_Multiome'     in sample_processed['SeqType']:
        add_args['mutiome_tenx_path']        =    sample_processed['Multiome 10X sheet']

    if 'SC_SeekGene_VDJ'     in sample_processed['SeqType'] and '5' not in sample_processed['VDJ type']:
        add_args['chain']        =    sample_processed['VDJ type']
        add_args['organism']     =    sample_processed['Organism']
    
    if  'SC_TENX_CellPlex'     in sample_processed['SeqType']:
        add_args['cmo_cellplex']        =   sample_processed['CellPlex_CMO']
        add_args['samples_cellplex']    =   sample_processed['CellPlex_ID']
        add_args['plex_cellplex']       =   sample_processed['CellPlex_PLEX']
    
    postfix_path_res    =   sample_processed['Path result html prefix'] # '/mnt/raid0/ofateev/projects/SC_auto/2.Results/SG/scRNA/240411_A01022_0750_AHNFHFDRXY/962000685201_h/*_report.html'
    result_dir          =   sample_processed['Path local results']      # '/mnt/raid0/ofateev/projects/SC_auto/2.Results/SG/scRNA/240411_A01022_0750_AHNFHFDRXY'
    sample_id           =   sample_processed['Sample_ID']               # '962000685201'
    flowcell            =   sample_processed['Flowcell']                # '240411_A01022_0750_AHNFHFDRXY'
    toolpath            =   sample_processed['Path install tool']       # '/mnt/raid0/ofateev/soft/seeksoultools.1.2.2'
    cmd_path            =   sample_processed['Path cmd run']            # '/mnt/raid0/ofateev/projects/SC_auto/src_new/main/_2_Commands/SG/_SG_scRNA.py'
    ref_dir             =   sample_processed['Path to refs']            # '/mnt/raid0/ofateev/refs/SG_scRNA_GRCh38'
    data_dir            =   sample_processed['Path data']               # '/mnt/raid0/ofateev/projects/SC_auto/1.Data/FASTQ/240411_A01022_0750_AHNFHFDRXY'
    ceph_res            =   sample_processed['Path ceph results']       # '/mnt/cephfs8_rw/functional-genomics/SG_SC_RES/scRNA/seeksoultools.1.2.2/240411_A01022_0750_AHNFHFDRXY'
    existing_results    =   glob(postfix_path_res)                      # [] |  '/mnt/raid0/ofateev/projects/SC_auto/2.Results/SG/scRNA/240411_A01022_0750_AHNFHFDRXY/962000685201_h/*_report.html'
    postfix_org         =   sample_processed['Prefix reference']        # 'h'
    sample_log          =   sample_processed['Path log']                # '/mnt/raid0/ofateev/projects/SC_auto/2.Results/SG/scRNA/240411_A01022_0750_AHNFHFDRXY/962000685201_h.log'

    if existing_results:
        log_file = open(sample_log, "w")
        return None, log_file, ceph_res
    try:        
        module      =    dynamic_import(cmd_path)
        functions   =    inspect.getmembers(module, 
                                           inspect.isfunction)
        if not functions:
            raise RuntimeError(f"❌[3.1.2 Processing] Module {toolpath} contains no functions.")
        func_name, func     =    functions[0]
        args = {
            "flowcell"          :    flowcell,
            "sample"            :    sample_id,
            "ref_dir"           :    ref_dir,
            "result_dir"        :    result_dir,
            "data_dir"          :    data_dir ,
            "core"              :    core,
            "toolpath"          :    toolpath,
            "org_prefix"        :    postfix_org,
            "log_file"          :    sample_log
        }
        args.update(add_args)
        result      =   func(**args)
        log_path    =   result[-1]
        log_file    =   open(log_path, "w")

        run_process = subprocess.Popen(
                                        result[0],
                                        stdout  =   log_file,
                                        stderr  =   subprocess.STDOUT,
                                        cwd     =   result_dir)
        return run_process, log_file, ceph_res
    except Exception as e:
        print(f"❌[3.1.2 Processing] Error processing sample {sample_id}: {e}")
        #traceback.print_exc()
        return None, None, None