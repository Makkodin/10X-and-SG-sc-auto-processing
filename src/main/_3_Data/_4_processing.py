from    typing                              import  Optional, Dict, Any, List, Tuple
from    main._1_PATHs.referens              import  RefsType
from    main._1_PATHs.tools                 import  ToolsType
from    main._1_PATHs.results               import  ResultsType
from    main._3_Data.postprocessing._ann_scparadise    import  process_annotation

import multiprocessing
import concurrent.futures
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import sys
import os
import time
from    glob import glob
import subprocess
import pandas as pd
import importlib.util
import inspect

def choose_resources(sample_count: int) -> Tuple[int, int]:
    """
    Returns total CPU cores and memory (in GB) based on the number of samples.
    
    More samples = fewer resources per sample.

    :param sample_count: Number of samples to process.
    :return: (total_cores, total_memory)
    """
    if sample_count >= 16:
        return 7, 70 
    elif sample_count >= 12:
        return 10, 100 
    elif sample_count >= 8:
        return 15, 200
    elif sample_count >= 4:
        return 20, 200
    elif sample_count >= 2:
        return 20, 300
    elif sample_count == 1:
        return 40, 800

def dynamic_import(script_path: str) -> Any:
    """
    Dynamically imports a Python module from the given file path.

    :param script_path	: Path to the Python script to import as a module.
    :return				: Imported module object.
    """
    module_name = os.path.basename(script_path).replace(".py", "")
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if not spec or not spec.loader:
        raise ImportError(f"Failed to load module from {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

def prepare_directories(
    seq_type:   str,
    work_ref:   str,
    work_tools: str,
    work_run:   str,
    results:    ResultsType,
    ref:        RefsType,
    tool:       ToolsType,
    organism:   str
) -> Dict[str, str]:
    """
    Prepares necessary directory paths based on sequencing type and configuration.

    :param seq_type		: Type of sequencing (e.g., SC_TENX_Visium_FFPE).
    :param work_ref		: Path for reference files.
    :param work_tools	: Path for tools.
    :param work_run		: Path for running jobs.
    :param results		: ResultsType instance containing output path configurations.
    :param ref			: RefsType instance with reference genome info.
    :param tool			: ToolsType instance with tool configuration.
    :param organism		: Organism name used in reference selection.

    :return				: Dictionary of prepared paths.
    """
    res_dir_all     =   f"{work_ref}/{ref[seq_type]._get_params()[organism]['ref']}"
    result_dir_all  =   f"{work_run}/{results[seq_type]._get_params()['local']}"
    data_dir_all    =   f"{work_run}/{results[seq_type]._get_params()['fastq']}"
    toolpath_all    =   f"{work_tools}/{tool[seq_type]._get_params()}"
    ceph_res        =   f"{results[seq_type]._get_params()['ceph']}"

    return {
        "res_dir_all"	: res_dir_all,
        "result_dir_all": result_dir_all,
        "data_dir_all"	: data_dir_all,
        "toolpath_all"	: toolpath_all,
        "ceph_res"		: ceph_res,
    }

def process_sample(
    sample_row: pd.Series,
    work_ref:   str,
    work_tools: str,
    work_run:   str,
    seq_types:  list,
    results:    ResultsType,
    ref:        RefsType,
    tool:       ToolsType,
    core:       int = 10,
    memory:     int = 100,
) -> Tuple[Optional[subprocess.Popen], Optional[Any], Optional[str]]:
    """
    Processes a single sample row from the run sheet DataFrame.

    :param sample_row	: A single row from the run sheet DataFrame.
    :param work_ref		: Base path for reference files.
    :param work_tools	: Base path for tools/scripts.
    :param work_run		: Base path for running jobs.
    :param results		: ResultsType instance with output path configurations.
    :param ref			: RefsType instance with reference genome info.
    :param tool			: ToolsType instance with tool configuration.
    :param core			: Number of CPU cores to use.
    :param memory		: Memory limit (in GB) for processing.

    :return				: Tuple of (subprocess.Popen object, log file object, Ceph result path).
    """
    sample_id       =   sample_row['Sample_ID'] 
    flowcell        =   sample_row['Flowcell']
    name_organism   =   sample_row['Organism_name']
    organism        =   sample_row['Reference']   # GRCh38 ...
    seq_type        =   sample_row['SEQtype']     # SC_TENX_Visium_FFPE, ...
    cmd_script      =   sample_row['Cmd']         # src/main/_2_Commands/10X/_10X_scRNA.py ...

    dirs = prepare_directories(seq_type     =   seq_type, 
                               work_ref     =   work_ref, 
                               work_tools   =   work_tools, 
                               work_run     =   work_run, 
                               results      =   results, 
                               ref          =   ref, 
                               tool         =   tool, 
                               organism     =   organism)
    add_args: Dict[str, Any] = {}

    # More settings for FFPE, VDJ seqtype
    if seq_type     ==  'SC_TENX_Visium_FFPE':
        add_args.update({
            'probe_set'     :   f"{dirs['toolpath_all']}/{ref[seq_type]._get_params()[organism]['probe-set']}",
            'img'           :   sample_row['Img'],
            'area'          :   sample_row['Area'],
            'slide'         :   sample_row['Slide']})
    if 'SC_SeekGene_VDJ' in seq_types:
        add_args['chemistry']       =   'DD5V1'
        if seq_type     ==  'SC_SeekGene_RNA':
            dirs['result_dir_all']  =   f"{work_run}/{results['SC_SeekGene_VDJ']._get_params()['local']}"
            dirs['ceph_res']        =   f"{results['SC_SeekGene_VDJ']._get_params()['ceph']}"
        elif seq_type   ==  'SC_SeekGene_VDJ':
            add_args['chain'] = sample_row['VDJ_type']
    if 'TENX' in seq_type:
        add_args['memory'] = memory

    # Run command fot each sample
    postfix             =   results[seq_type]._get_params()['postfix']
    result_dir          =   dirs['result_dir_all']
    existing_results    =   glob(f"{result_dir}/{flowcell}/{sample_id}*/*{postfix}")

    # Check if exist
    if existing_results:
        log_file = open(f"{result_dir}/{flowcell}/{sample_id}_ann.log", "w")
        print(f"✅[Processing] Results already exist for {sample_id}.")
        return None, log_file, dirs['ceph_res']

    try:
        # Dynamic import comand for processing
        module      =   dynamic_import(f"{work_run}/{cmd_script}")
        functions   =   inspect.getmembers(module, 
                                           inspect.isfunction)
        if not functions:
            raise RuntimeError(f"Module {cmd_script} contains no functions.")
        func_name, func     =   functions[0]
        args = {
            "sample"	    :   sample_id,
            "flowcell"	    :   flowcell,
            "ref_dir"	    :   dirs["res_dir_all"],
            "toolpath"	    :   dirs["toolpath_all"],
            "result_dir"    :   dirs["result_dir_all"],
            "data_dir"	    :   dirs["data_dir_all"],
            "core"		    :   core}
        args.update(add_args)
        os.makedirs(f"{dirs['result_dir_all']}/{flowcell}", 
                    exist_ok=True)

        result = func(**args)
        log_path = result[-1]

        log_file = open(log_path, "w")
        run_process = subprocess.Popen(
            result[0],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=f"{dirs['result_dir_all']}/{flowcell}"
        )
        return run_process, log_file, dirs['ceph_res']
    except Exception as e:
        print(f"❌[Processing] Error processing sample {sample_id}: {e}")
        return None, None, None


def processing_flowcell(
    runsheet            :   pd.DataFrame,
    path_run_sheet      :   str,
    core:int            =   None,
    mem:int             =   None,
    ref                 =   RefsType,
    tool                =   ToolsType,
    results             =   ResultsType,
    work_ref:   str     =   None,
    work_tools: str     =   None,
    work_run:   str     =   None
) -> None:
    """
    Main function to process all samples in the run sheet with dynamic resource allocation.

    :param runsheet     : DataFrame containing run sheet data.
    :param ref          : Reference genome configuration object.
    :param tool         : Tool/script paths configuration object.
    :param results      : Output path configuration object.
    :param work_ref     : Base directory for reference files.
    :param work_tools   : Base directory for tools/scripts.
    :param work_run     : Base directory for running jobs.
    """
    samples_num     =   len(runsheet)
    flowcells       =   runsheet["Flowcell"].drop_duplicates().tolist()
    organisms       =   runsheet["Reference"].drop_duplicates().tolist()
    organisms_name  =   runsheet["Organism_name"].drop_duplicates().tolist()
    typeseqs        =   runsheet["SEQtype"].drop_duplicates().tolist()
    tissue          =   runsheet["Tissue"].drop_duplicates().tolist()
    
    # Resources
    if core == None and mem == None:
        per_sample_core, per_sample_mem     =   choose_resources(samples_num)
    else:
        per_sample_core, per_sample_mem     =   core, mem
    total_core      =   max(per_sample_core * samples_num, 4)   # Minimum 4 cores per sample
    total_memory    =   max(per_sample_mem * samples_num, 40)   # Minimum 40 GB RAM per sample

    # Start Processing flowcell
    print( "┌────────────────────────────────────────────────────────────────────────────────────────────────┐")
    print( "│              Flowcell processing info                                                          │")
    print( "├────────────────────────────────────────────────────────────────────────────────────────────────┤")
    print(f"│ ℹ️ Start to processed flowcells_:   {flowcells}")
    print(f"│ ℹ️ Sample number________________:   {samples_num}")
    print(f"│ ℹ️ Organism reference___________:   {organisms}")
    print(f"│ ℹ️ Type seq_____________________:   {typeseqs}")
    print(f"│ ⚙️ Total resources allocated____:   {total_core} cores, {total_memory} GB RAM")
    print(f"│ ⚙️ Resources per sample_________:   {per_sample_core} cores, {per_sample_mem} GB RAM")
    print( "└────────────────────────────────────────────────────────────────────────────────────────────────┘")

    processes: List[subprocess.Popen]   = []
    log_files                           = []
    ceph_paths: List[str]               = []
    sample_log_map: Dict[str, Any]      = {}
    ####################################################################
    # Processing samples in flowcell
    ####################################################################

    VDJ_key = False
    if 'SC_SeekGene_VDJ' in typeseqs:
        VDJ_key =   True
    for _, row in runsheet.iterrows():
        proc, log_file, ceph_path = process_sample(
            sample_row  =   row,
            work_ref    =   work_ref,
            work_tools  =   work_tools,
            work_run    =   work_run,
            results     =   results,
            seq_types   =   typeseqs,
            ref         =   ref,
            tool        =   tool,
            core        =   per_sample_core,
            memory      =   per_sample_mem
        )
        if proc != None:
            print(f"🕐 [Processing] Process {row['Sample_ID']} started.")
        if proc and log_file:
            processes.append(proc)
            log_files.append(log_file)
            ceph_paths.append(ceph_path)

        sample_id   =   row['Sample_ID']
        sample_log_map[sample_id] = {
            'log_file'      :   log_file,
            'ceph_path'     :   ceph_path,
            'seq_type'      :   row['SEQtype'],
            'flowcell'      :   row['Flowcell'],
            'organism'      :   row['Reference'],
            'organism_name' :   row['Organism_name'],
            'tissue'        :   row['Tissue'],
            'row_index'     :   len(processes) - 1,
            'description'   :   row['Description']
        }
        time.sleep(2)

    for i, proc in enumerate(processes):
        proc.wait()
        if proc.returncode != 0:
            print(f"❌[Processing] Process failed with code: {proc.returncode}")
        else:
            print("✅[Processing] Process completed successfully.")
    for i, path in enumerate(ceph_paths):
        runsheet.at[i, 'Ceph_Path'] = path

    rna_seq_types       =   {'SC_TENX_RNA', 'SC_SeekGene_RNA'}
    supported_organisms =   {'GRCh38'}  # MM10
    should_annotate = any(
            (seq_type in rna_seq_types and organism in supported_organisms) 
            for seq_type, organism in zip(runsheet["SEQtype"], runsheet["Reference"])
        )
    if should_annotate:
        print("🧬[Annotation] Starting parallel scParadise annotation for RNA samples...")

        annotation_tasks = []
        for sample_id, sample_info in sample_log_map.items():
            if (sample_info['seq_type'] in rna_seq_types and 
                sample_info['organism'] in supported_organisms):
                annotation_tasks.append({
                            'sample_id'     :   sample_id,
                            'organism'      :   sample_info['organism'],
                            'seq_type'      :   sample_info['seq_type'],
                            'flowcell'      :   sample_info['flowcell'],
                            'organism_name' :   sample_info['organism_name'],
                            'tissue'        :   sample_info['tissue'],
                            'description'   :   sample_info['description']
                })
        if annotation_tasks:
            max_workers = min(len(annotation_tasks), multiprocessing.cpu_count() // 2, 4)
            max_workers = max(max_workers, 1)
            
            print(f"🕐[Annotation] Processing {len(annotation_tasks)} samples with {max_workers} parallel workers")

            results_ann = []
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                future_to_sample = {
                    executor.submit(
                        process_annotation, 
                        task, 
                        work_ref, 
                        work_tools, 
                        work_run, 
                        results, 
                        ref, 
                        tool,
                        VDJ_key
                    ): task['sample_id'] 
                    for task in annotation_tasks
                }
                
                for future in concurrent.futures.as_completed(future_to_sample):
                    sample_id = future_to_sample[future]
                    try:
                        result_sample_id, success, message = future.result()
                        results_ann.append((result_sample_id, success, message))
                        
                        if sample_id in sample_log_map:
                            sample_log_map[sample_id]['log_file'].write(f"\n{message}\n")
                            sample_log_map[sample_id]['log_file'].flush()
                        
                        if success:
                            print(f"✅[Annotation] Completed: {sample_id}")
                        else:
                            print(f"❌[Annotation] Failed: {sample_id}")
                            
                    except Exception as e:
                        error_msg = f"❌[Annotation] Unexpected error processing {sample_id}: {str(e)}"
                        print(error_msg)
                        if sample_id in sample_log_map:
                            sample_log_map[sample_id]['log_file'].write(f"{error_msg}\n")
                            sample_log_map[sample_id]['log_file'].flush()
            
            successful = sum(1 for _, success, _ in results_ann if success)
            failed = len(results_ann) - successful
            
            print(f"📊[Annotation] Annotation completed: {successful} successful, {failed} failed")
        else:
            print("ℹ️[Annotation] No RNA samples found for annotation")

    for sample_info in sample_log_map.values():
        sample_info['log_file'].close()


    print(f"✅[Processing] {flowcells} - processing complete!")
    print("-----------------------------------------------------")