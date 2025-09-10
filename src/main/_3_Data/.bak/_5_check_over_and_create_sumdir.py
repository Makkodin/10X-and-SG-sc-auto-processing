from    _1_PATHs.results   	import ResultsType
from    _1_PATHs.tools  	import ToolsType
from 	glob 	import 	glob
import  pandas  as  pd
import 	os
import  shutil
import 	time
import  subprocess

import os

def count_files_in_dir(root_dir):
	return sum(len(files) for _, _, files in os.walk(root_dir))

def check_and_move_reports(
					runsheet:pd.DataFrame,
					runsheet_path:str,
					flowcell:str,
					fastq_res_folder:str,
					password:str,
				   	results     	= 	ResultsType,
					toolpath		=	ToolsType,
				   	work_run:str 	= 	'/mnt/raid0/ofateev/projects/SC_auto'
				   ):
	samples_parse_df        		= runsheet
	samples_parse_df['Report_path'] = "Error"
	res_folder_local 				= None

	for i in range(len(samples_parse_df)):
		_sample     =   samples_parse_df.iloc[i]['Sample_ID']
		_seq_type   =   samples_parse_df.iloc[i]['SEQtype']
		if pd.isna(_seq_type):
			print(f"❌ SEQtype is missing for Sample_ID: {_sample}")
			break
		try:
			_postfix = results[_seq_type]._get_params()['postfix']
		except KeyError:
			print(f"❌ Unknown SEQtype '{_seq_type}' for Sample_ID: {_sample}")
			break
		_postfix	=	results[_seq_type]._get_params()['postfix']

		if 'VDJ_type' in samples_parse_df.columns:
			_seq_type = 'SC_SeekGene_VDJ'

		result_dir		=	f"{work_run}/{results[_seq_type]._get_params()['local']}"
		ceph_res_dir	= 	f"{results[_seq_type]._get_params()['ceph']}/{toolpath[_seq_type]._get_params()}"
		if not os.path.exists(ceph_res_dir):
			os.makedirs(ceph_res_dir)
		report_path		=	glob(f'{result_dir}/{flowcell}/{_sample}*/*{_postfix}')	

		if report_path:
			samples_parse_df.loc[i, 'Report_path'] 	= report_path[0]
			samples_parse_df.loc[i, 'Local_path'] 		= result_dir
			samples_parse_df.loc[i, 'Ceph_path'] 		= ceph_res_dir

	if "Error" in samples_parse_df['Report_path'].to_list():
		df_error = samples_parse_df[samples_parse_df['Report_path'] == 'Error']
		print(f'Not completed report.html for : {df_error["Sample_ID"].to_list()}')

	else: 
		os.makedirs(f"{result_dir}/{flowcell}/{flowcell}-sum", exist_ok=True)
		for i in range(len(samples_parse_df)):
			_sample			=	samples_parse_df.iloc[i]['Sample_ID']
			_report_path	=	samples_parse_df.iloc[i]['Report_path']
			new_name 		= 	_report_path.replace('web_summary', f'{_sample}-web_summary')\
											.replace('.html', '-report.html')\
											.split('/')[-1]
			sum_path		=	f"{result_dir}/{flowcell}/{flowcell}-sum"
			new_path		=	f"{sum_path}/{new_name}"
			shutil.copyfile(_report_path, 
				   			new_path)
		
		print(f"Move to sum dir:", f"{len(glob(f'{sum_path}/*'))}/{len(samples_parse_df)} reports")
		res_folder_local = f"{result_dir}/{flowcell}"
		shutil.copyfile(runsheet_path, 
				   		f"{res_folder_local}/{runsheet_path.split('/')[-1]}")

	
	set_res_ceph = list(set(samples_parse_df['Ceph_path'].to_list()))
	if res_folder_local != None:
		if len(set_res_ceph) == 1:
			load_com    = ['sshpass', '-p', f'{password}',
						   'sudo','rsync','-r',
						   '--no-links','--checksum','--progress',
							f'{res_folder_local}', 
							f'{ceph_res_dir}/']
		else: 
			print('Error in ceph_res_path :', set_res_ceph)
		try:
			result  =   subprocess.run(load_com, 
						   check    =   True,
						   stdout   =   subprocess.PIPE,
						   stderr   =   subprocess.DEVNULL,
						   text     =   True
						)
			time.sleep(30)
			print(f"Move to  {res_folder_local} ready!")
		except subprocess.CalledProcessError as e:
			print("Move error:")
			print(f"Code: {e}")


		local_count 	= 	count_files_in_dir(res_folder_local)
		remote_count 	= 	count_files_in_dir(f"{ceph_res_dir}/{flowcell}")

		remove_com  = ['sshpass', '-p', f'{password}',
						   'sudo','rm','-r',
							f'{res_folder_local}', 
							f'{fastq_res_folder}',
							f'{runsheet_path}']

		if local_count == remote_count:
			print(f"✅ Transfer {local_count}/{remote_count} files.")
			remove  =   subprocess.run(remove_com, 
						   check    =   True,
						   stdout   =   subprocess.PIPE,
						   stderr   =   subprocess.DEVNULL,
						   text     =   True
						)
			time.sleep(30)
			print(f"Remove all local files!")
		else:
			print(f"❌ Transfer {local_count}/{remote_count} files")
			remove  =   subprocess.run(remove_com, 
						   check    =   True,
						   stdout   =   subprocess.PIPE,
						   stderr   =   subprocess.DEVNULL,
						   text     =   True
						)
			time.sleep(30)

	return 