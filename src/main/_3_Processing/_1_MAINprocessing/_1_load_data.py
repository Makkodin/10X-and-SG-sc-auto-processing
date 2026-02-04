import os
import re
from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from main._3_Processing._0_PREprocessing._1_load_data.BCL_load          import  load_bcl
from main._3_Processing._0_PREprocessing._1_load_data.FASTQ_load        import  load_fastq
from main._3_Processing._0_PREprocessing._1_load_data.SampleSheet_load  import  load_sample_sheet_flowcell

from main._3_Processing._0_PREprocessing._3_reads_processing.demultiplication    import  bcl2fastq, bcl2fastq_atac
from main._3_Processing._0_PREprocessing._3_reads_processing.filter_reads_fastp  import  fastp_reads_with_repair
from main._1_Config.main_config import multiome_pattern


def load_fastq_wrapper(args: Tuple) -> bool:
	sample_id, flowcell, username, password, fastq_load, fastq_save = args
	try:
		sample_fastq_dir = os.path.join(fastq_save, flowcell, sample_id)
		if os.path.exists(sample_fastq_dir):
			fastq_files = [f for f in os.listdir(sample_fastq_dir) 
						  if f.endswith(('.fastq.gz'))]
			if fastq_files:
				print(f"ℹ️[3.1.1 Load FASTQ] Files already exist for {flowcell}:{sample_id}")
				return True
		result = load_fastq(
			sample_id       =   sample_id,
			flowcell        =   flowcell,
			user            =   username,
			password        =   password,
			load_fastq      =   fastq_load,
			save_fastq      =   fastq_save,
			check_existing  =   True
		)
		return bool(result)
	except Exception as e:
		print(f"❌[3.1.1 Load FASTQ Wrapper] Error for {flowcell}:{sample_id}: {str(e)}")
		return False

def load_fastq_parallel(
		args_list: List[Tuple], 
		max_workers: int = 5) -> Dict[Tuple, bool]:
	results = {}
	print(f"🕒[3.1.1 Load FASTQ Parallel] Parallel loading of {len(args_list)} samples")
	
	with ThreadPoolExecutor(max_workers=max_workers) as executor:
		future_to_args = {}
		for args in args_list:
			future = executor.submit(load_fastq_wrapper, args)
			future_to_args[future] = args
		completed = 0
		for future in as_completed(future_to_args):
			args = future_to_args[future]
			sample_id, flowcell, *_ = args
			completed += 1
			try:
				result = future.result()
				if result is None:
					results[args] = False
				else:
					results[args] = bool(result)
				if results[args]:
					print(f"✅[3.1.1 Load FASTQ {completed}/{len(args_list)}] Success: {flowcell}:{sample_id}")
				else:
					print(f"❌[3.1.1 Load FASTQ {completed}/{len(args_list)}] Failed: {flowcell}:{sample_id}")        
			except Exception as e:
				print(f"❌[3.1.1 Load FASTQ Parallel] Error for {flowcell}:{sample_id}: {str(e)}")
				results[args] = False
	success_count = 0
	for value in results.values():
		if isinstance(value, bool) and value:
			success_count += 1
	print(f"✅[3.1.1 Load FASTQ Parallel] Total: {success_count}/{len(args_list)} samples loaded successfully")
	return results

def load_flowcell(
		flowcell_sample_processed: Dict,
		bcl_load:   str, 
		bcl_save:   str,
		fastq_load: str, 
		fastq_save: str,
		username:   str, 
		password:   str,
		filter_reads:   bool            =   True,
		type_load_data: str             =   'fastq',
		core:       int                 =   16,
		min_length: int                 =   60,
		max_len1:   int                 =   150,
		fastq_parallel_workers: int     =   5,
		filter_parallel_samples:int     =   3
		) -> Dict[str, bool]:
	
	results     =   {}
	flowcells   =   list(set([x.split(':')[0] for x in flowcell_sample_processed.keys()]))
	seq_types   =   [x.get('SeqType', '') for x in flowcell_sample_processed.values()]
	atac_keys   =   'SC_TENX_ATAC' in seq_types
	flRNA_keys  =   'SC_SeekGene_FullRNA' in seq_types
	print(f"🕒[3.1.1 Load flowcell] Starting '{type_load_data}' loading for {len(flowcells)} flowcells")
	if type_load_data == 'bcl':
		for flowcell_full in flowcells:
			print(f"🕒[3.1.1 Load BCL] Processing flowcell: {flowcell_full}")
			if re.match(multiome_pattern, flowcell_full):
				flowcell_parts = flowcell_full.split('-')
				print(f"🕒[3.1.1 Load BCL] Multiome detected: {flowcell_parts}")
				for fc_part in flowcell_parts:
					print(f"🕒[3.1.1 Load BCL] Loading BCL for {fc_part}")
					bcl_res_folder = load_bcl(
						flowcell=fc_part,
						user=username,
						password=password,
						load_bcl=bcl_load,
						save_bcl=bcl_save)
					if bcl_res_folder:
						print(f"✅[3.1.1 Load BCL] BCL loaded for {fc_part}")
						if atac_keys:
							print(f"🕒[3.1.1 Demultiplex] Running bcl2fastq for ATAC: {fc_part}")
							fastq_res_folder = bcl2fastq_atac(
								bcl=bcl_res_folder, 
								fastq=fastq_save)
						else:
							print(f"🕒[3.1.1 Demultiplex] Running bcl2fastq: {fc_part}")
							fastq_res_folder = bcl2fastq(
								bcl=bcl_res_folder, 
								fastq=fastq_save)
						if flRNA_keys and filter_reads and fastq_res_folder:
							print(f"🕒[3.1.1 Filter reads] Filtering reads for FullRNA: {fc_part}")
							fastq_res_folder = fastp_reads_with_repair(
								fastq_save=fastq_save,
								flowcell=fc_part,
								core=core,
								min_length=min_length,
								max_len1=max_len1,
								more_arg=[],
								run_repair=True,
								parallel_samples=filter_parallel_samples
							)
						results[fc_part] = bool(fastq_res_folder)
					else:
						print(f"❌[3.1.1 Load BCL] Failed to load BCL for {fc_part}")
						results[fc_part] = False
			else:
				print(f"🕒[3.1.1 Load BCL] Loading BCL for {flowcell_full}")
				bcl_res_folder = load_bcl(
					flowcell=flowcell_full,
					user=username,
					password=password,
					load_bcl=bcl_load,
					save_bcl=bcl_save)
				if bcl_res_folder:
					print(f"✅[3.1.1 Load BCL] BCL loaded for {flowcell_full}")
					if atac_keys:
						print(f"🕒[3.1.1 Demultiplex] Running bcl2fastq for ATAC: {flowcell_full}")
						fastq_res_folder = bcl2fastq_atac(
							bcl=bcl_res_folder, 
							fastq=fastq_save)
					else:
						print(f"🕒[3.1.1 Demultiplex] Running bcl2fastq: {flowcell_full}")
						fastq_res_folder = bcl2fastq(
							bcl=bcl_res_folder, 
							fastq=fastq_save)
					if flRNA_keys and filter_reads and fastq_res_folder:
						print(f"🕒[3.1.1 Filter reads] Filtering reads for FullRNA: {flowcell_full}")
						fastq_res_folder = fastp_reads_with_repair(
							fastq_save=fastq_save,
							flowcell=flowcell_full,
							core=core,
							min_length=min_length,
							max_len1=max_len1,
							more_arg=[],
							run_repair=True,
							parallel_samples=filter_parallel_samples
						)
					results[flowcell_full] = bool(fastq_res_folder)
				else:
					print(f"❌[3.1.1 Load BCL] Failed to load BCL for {flowcell_full}")
					results[flowcell_full] = False
	
	elif type_load_data == 'fastq':
		print(f"🕒[3.1.1 Load SampleSheet] Loading SampleSheet for {len(flowcells)} flowcells")

		flowcell_samplesheet_status = {}
		for flowcell_full in flowcells:
			if re.match(multiome_pattern, flowcell_full):
				flowcell_parts  =   flowcell_full.split('-')
				for fc_part in flowcell_parts:
					status  =   load_sample_sheet_flowcell(
														flowcell    =   fc_part,
														user        =   username,
														password    =   password,
														load_bcl    =   bcl_load,
														save_fastq  =   fastq_save)
					flowcell_samplesheet_status[fc_part]    =   status
			else:
				status      =   load_sample_sheet_flowcell(
														flowcell    =   flowcell_full,
														user        =   username,
														password    =   password,
														load_bcl    =   bcl_load,
														save_fastq  =   fastq_save)
				flowcell_samplesheet_status[flowcell_full]  =   status
		all_false = not any(flowcell_samplesheet_status.values())
		if all_false == True:
			return flowcell_samplesheet_status
	
		fastq_args_list = []
		dict_for_cellplex	=	{}
		for key, value in flowcell_sample_processed.items():
			if value['Processed status'] == False:
				flowcell_full   =   key.split(':')[0]
				sample_id       =   key.split(':')[1]

				sample_id_cellplex	=	None
				if 'SC_TENX_CellPlex' in value['SeqType']:
					sample_id						=	value['CellPlex_ID'].split("|")
					sample_id_cellplex				=	key.split(':')[1]
					for s_id in sample_id:
						dict_for_cellplex[s_id]	=	sample_id_cellplex
					
				if re.match(multiome_pattern, flowcell_full):
					flowcell_parts      =   flowcell_full.split('-')
					target_flowcells    =   flowcell_parts
				else:
					target_flowcells    =   [flowcell_full]

				for flowcell in target_flowcells:
					if type(sample_id) == list:
						for s_id in sample_id:
							args = (s_id, 
									flowcell, 
									username, 
									password, 
									fastq_load, 
									fastq_save)
							fastq_args_list.append(args)
					elif type(sample_id)	== str:
						s_id	=	sample_id
						args = (s_id, 
								flowcell, 
								username, 
								password, 
								fastq_load, 
								fastq_save)
						fastq_args_list.append(args)

		if  len(fastq_args_list) == 0:
			return results
		fastq_results = load_fastq_parallel(
							args_list       =   fastq_args_list, 
							max_workers     =   fastq_parallel_workers)
		if flRNA_keys and filter_reads:
			print(f"🕒[3.1.1 Filter reads] Filtering reads for FullRNA samples")
			flowcell_samples = {}
			for (sample_id, flowcell, *_), success in fastq_results.items():
				if success:
					if flowcell not in flowcell_samples:
						flowcell_samples[flowcell]  =   []
					flowcell_samples[flowcell].append(sample_id)
			for flowcell, samples in flowcell_samples.items():
				if samples:
					print(f"🕒[3.1.1 Filter reads] Processing {len(samples)} samples for {flowcell}")
					fastp_reads_with_repair(
						fastq_save          =   fastq_save,
						flowcell            =   flowcell,
						core                =   core,
						min_length          =   min_length,
						max_len1            =   max_len1,
						more_arg            =   [],
						run_repair          =   True,
						parallel_samples    =   filter_parallel_samples
					)
		for (s_id, flowcell, *_), success in fastq_results.items():
			if s_id in dict_for_cellplex:
				key_sample = dict_for_cellplex[s_id]
			else:
				key_sample = s_id

			key = f"{flowcell}:{key_sample}"
			results[key] = success
	else:
		print(f"❌[3.1.1 Load flowcell] Unknown loading type: {type_load_data}")
	success_count = 0
	for value in results.values():
		if isinstance(value, bool) and value:
			success_count += 1
	print(f"✅[3.1.1 Load flowcell] Loading completed. Success: {success_count}/{len(results)}")
	return results