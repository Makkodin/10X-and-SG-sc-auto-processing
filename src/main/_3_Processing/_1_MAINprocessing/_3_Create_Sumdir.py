from glob import glob
import pandas as pd
import os
import shutil
import time
import subprocess
from typing import Dict, List, Tuple
from main._3_Processing._2_POSTprocessing.report.stat import collect_and_save_statistics_sample, create_flowcell_statistics_table
from main._3_Processing._2_POSTprocessing.report.email_reporter import archive_and_send_report

def count_files_in_dir(root_dir: str) -> int:
	return sum(len(files) for _, _, files in os.walk(root_dir))

def check_and_move_reports(
	flowcell_sample_processed: dict,
) -> dict:
	print(f"🕒[3.1.3 Create Summary Dir] Collecting statistics...")
	
	_set_sum_stat_dir	=	[]
	_set_flowcell		=	[]

	seqtypes_flowcell	=	{}
	for key, value in flowcell_sample_processed.items():
		_seq_type		=	value['SeqType']
		_flowcell		=	value['Flowcell']
		_sample 		= 	value['Sample_ID']
		_report 		= 	glob(value['Path result html prefix'])
		_stats 			= 	glob(value['Path result stat prefix'])
		sum_stat_dir 	= 	value['Path local sum stat']
		result_dir 		= 	value['Path local results']
		ceph_res_dir 	= 	value['Path ceph results']
		  
		os.makedirs(sum_stat_dir, 
					exist_ok	=	True)

		if not os.path.exists(ceph_res_dir):
			os.makedirs(ceph_res_dir, exist_ok=True)
		if _report:
			_report = _report[0]
			_stats = _stats[0] if _stats else None 
		processing_status = value['Processed status']
		if processing_status == False:
			print(f"⚠️[3.1.3 Create Summary Dir] Sample {_sample} not processed yet, skipping statistics collection")
			continue 
		updated_sample = collect_and_save_statistics_sample(
			sample_processed	=	value, 
			stat_full_path		=	_stats
		)
		flowcell_sample_processed[key] = updated_sample
		seqtypes_flowcell[_seq_type]	=	{'Flowcell'		:	_flowcell, 
								 		'Sum_stat_dir'	:	sum_stat_dir, 
										'Results_dir'	:	result_dir, 
										'Ceph_dir'		:	ceph_res_dir
										}

	for key_seq, value_seq in  seqtypes_flowcell.items():
		filtered_data = {key: value for key, value in flowcell_sample_processed.items() if value.get('SeqType') == key_seq}
		_flowcell_stat 		= 	create_flowcell_statistics_table(flowcell_sample_processed	=	filtered_data)

		_set_sum_stat_dir	=	seqtypes_flowcell[key_seq]['Sum_stat_dir']
		_set_flowcell		=	seqtypes_flowcell[key_seq]['Flowcell']
		path_to_stat_file	=	f'{_set_sum_stat_dir}/{_set_flowcell}_stat.csv'
		_flowcell_stat.to_csv(path_to_stat_file, index=False)
		print(f"✅[3.1.3 Create Summary Dir] Statistics collect: {path_to_stat_file}")

		reports_copied, plots_copied	=	copy_reports_and_plots(flowcell_sample_processed	=	filtered_data,
																sum_stat_dir				=	_set_sum_stat_dir)
	return flowcell_sample_processed

def copy_reports_and_plots(
	flowcell_sample_processed: Dict[str, Dict],
	sum_stat_dir: str = None
) -> Tuple[int, int]:
	reports_copied = 0
	plots_copied = 0
	if sum_stat_dir is None:
		first_key = next(iter(flowcell_sample_processed))
		sum_stat_dir = flowcell_sample_processed[first_key]['Path local sum stat']
	os.makedirs(sum_stat_dir, exist_ok=True)
	for key, value in flowcell_sample_processed.items():
		try:
			seqtype = value['SeqType']
			sample_id = value['Sample_ID']
			if not value.get('Processed status', False):
				print(f"⚠️[3.1.3 Create Summary Dir] Sample {sample_id} not processed, skipping file copy")
				continue
			report_glob_pattern = value['Path result html prefix']
			reports = glob(report_glob_pattern)
			if not reports:
				print(f"⚠️[3.1.3 Create Summary Dir] No reports found for sample {sample_id}")
				continue
			report_path = reports[0]
			report_dir_path = os.path.dirname(report_path) if report_path else ""
			if seqtype == 'SC_SeekGene_FullRNA':
				path_local_data = value['Path data']
				full_rna_folders = [
					'bak_multilines', 
					'bak_before_fastp', 
					'bak_before_repair'
				]
				for folder in full_rna_folders:
					folder_path = os.path.join(path_local_data, folder)
					if os.path.exists(folder_path):
						dest_path = os.path.join(sum_stat_dir, folder)
						try:
							shutil.copytree(folder_path, dest_path, dirs_exist_ok=True)
							print(f"✅[3.1.3 Create Summary Dir] Copied folder {folder} for {sample_id}")
							time.sleep(2)
						except Exception as e:
							print(f"⚠️[3.1.3 Create Summary Dir] Failed to copy folder {folder} for {sample_id}: {e}")
				for pattern in ["fastp_-l*", "*.log"]:
					search_pattern = os.path.join(path_local_data, pattern)
					for file_path in glob(search_pattern):
						try:
							file_name = os.path.basename(file_path)
							dest_path = os.path.join(sum_stat_dir, file_name)
							shutil.copy2(file_path, dest_path)
							print(f"✅[3.1.3 Create Summary Dir] Copied {file_name} for {sample_id}")
							time.sleep(1)
						except Exception as e:
							print(f"⚠️[3.1.3 Create Summary Dir] Failed to copy {file_path} for {sample_id}: {e}")
				after_fastp_dir = os.path.join(sum_stat_dir, "after_fastp")
				os.makedirs(after_fastp_dir, exist_ok=True)
				fastq_pattern = os.path.join(path_local_data, f"{sample_id}_S*_filtered.fastq.gz")
				for fastq_path in glob(fastq_pattern):
					try:
						file_name = os.path.basename(fastq_path)
						dest_path = os.path.join(after_fastp_dir, file_name)
						shutil.copy2(fastq_path, dest_path)
						print(f"✅[3.1.3 Create Summary Dir] Copied filtered fastq {file_name} for {sample_id}")
						time.sleep(1)
					except Exception as e:
						print(f"⚠️[3.1.3 Create Summary Dir] Failed to copy fastq {fastq_path} для {sample_id}: {e}")       
			plot_patterns = []
			if report_dir_path and seqtype in ['SC_TENX_RNA', 'SC_SeekGene_RNA', 'SC_SeekGene_VDJ']:
				if seqtype	==	'SC_SeekGene_VDJ':
					if value['VDJ type'] == '5':
						plot_patterns.append(os.path.join(report_dir_path, "*.png"))
						step3_filtered_path = os.path.join(report_dir_path, "step3", "filtered_feature_bc_matrix")
						if os.path.exists(step3_filtered_path):
							plot_patterns.append(os.path.join(step3_filtered_path, "*.png"))
						else:
							print(f"ℹ️[3.1.3 Create Summary Dir] Path not found: {step3_filtered_path}")
				else:
					plot_patterns.append(os.path.join(report_dir_path, "*.png"))
					step3_filtered_path = os.path.join(report_dir_path, "step3", "filtered_feature_bc_matrix")
					if os.path.exists(step3_filtered_path):
						plot_patterns.append(os.path.join(step3_filtered_path, "*.png"))
					else:
						print(f"ℹ️[3.1.3 Create Summary Dir] Path not found: {step3_filtered_path}")

			for pattern in plot_patterns:
				for plot_path in glob(pattern):
					try:
						plot_name = f'{sample_id}_{os.path.basename(plot_path)}'
						dest_path = os.path.join(sum_stat_dir, plot_name)
						shutil.copy2(plot_path, dest_path)
						plots_copied += 1
						print(f"✅[3.1.3 Create Summary Dir] Copied plot {plot_name}")
					except Exception as e:
						print(f"⚠️[3.1.3 Create Summary Dir] Failed to copy plot {plot_path} для {sample_id}: {e}")
			try:
				if os.path.exists(report_path):
					report_name = f'{sample_id}-report.html'
					dest_report_path = os.path.join(sum_stat_dir, report_name)
					shutil.copy2(report_path, dest_report_path)
					reports_copied += 1
					print(f"✅[3.1.3 Create Summary Dir] Copied report for {sample_id}")
				else:
					print(f"⚠️[3.1.3 Create Summary Dir] Report file not found for {sample_id}: {report_path}")
			except Exception as e:
				print(f"⚠️[3.1.3 Create Summary Dir] Failed to copy report for {sample_id}: {e}")
			
		except Exception as e:
			print(f"❌[3.1.3 Create Summary Dir] Error processing sample {key}: {e}")
			continue
	print(f"✅[3.1.3 Create Summary Dir] Moved to sum dir: {reports_copied}/{len(flowcell_sample_processed)} reports")
	print(f"✅[3.1.3 Create Summary Dir] Moved to sum dir: {plots_copied} plots")
	return reports_copied, plots_copied
