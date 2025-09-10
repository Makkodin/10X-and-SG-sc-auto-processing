from    _1_PATHs.referens  import RefsType
from    _1_PATHs.tools     import ToolsType
from    _1_PATHs.results   import ResultsType

import  sys
import  pandas as pd
import 	os
import 	time
from 	glob	import 	glob
import 	subprocess
import  importlib.util
import  inspect

def dynamic_import(script_path):
	module_name = script_path.split("/")[-1].replace(".py", "")
	spec        = importlib.util.spec_from_file_location(module_name, script_path)
	module      = importlib.util.module_from_spec(spec)
	sys.modules[module_name] = module
	spec.loader.exec_module(module)
	return module


def processing_flowcell(runsheet:pd.DataFrame,
						ref         	= 	RefsType,
						tool        	= 	ToolsType,
						results     	= 	ResultsType,
						work_ref:str    = 	'/mnt/raid0/ofateev/refs',
						work_tools:str  = 	'/mnt/raid0/ofateev/soft',
						work_run:str    = 	'/mnt/raid0/ofateev/projects/SC_auto'
						):
	
	samples_parse_df        = runsheet

	samples_num =   len(samples_parse_df["Sample_ID"])
	flowcells	=	samples_parse_df["Flowcell"].drop_duplicates().to_list()
	organism    =   samples_parse_df["Reference"].drop_duplicates().to_list()
	typeseq     =   samples_parse_df["SEQtype"].drop_duplicates().to_list()

	samples_parse_df['Dir_res'] = "None"

	print("-----------------------------------------------------")
	print("              Flowcell processing info               ")
	print("-----------------------------------------------------")
	print(f"Start to processed flowcells_:   {flowcells}")
	print(f"Sample number________________:   {samples_num}")
	print(f"Organism reference___________:   {organism}")
	print(f"Type seq_____________________:   {typeseq}")
	print("-----------------------------------------------------")

	_core,_memory	= 	10,100
	
	processes,log_files = [],[]
	for i in range(len(samples_parse_df)):
		_sample     =   samples_parse_df.iloc[i]['Sample_ID']
		_flowcell   =   samples_parse_df.iloc[i]['Flowcell']
		_ref        =   samples_parse_df.iloc[i]['Reference']
		_seq_type   =   samples_parse_df.iloc[i]['SEQtype']
		_cmd        =   samples_parse_df.iloc[i]['Cmd']

		res_dir_all 	= 	f"{work_ref}/{ref[_seq_type]._get_params()[_ref]['ref']}"
		result_dir_all	=	f"{work_run}/{results[_seq_type]._get_params()['local']}"
		data_dir_all	=	f"{work_run}/{results[_seq_type]._get_params()['fastq']}"
		toolpath_all	=	f"{work_tools}/{tool[_seq_type]._get_params()}"
		ceph_res		=	f"{results[_seq_type]._get_params()['ceph']}"

		add_args	=	{}

		if _seq_type == 'SC_TENX_Visium_FFPE':
			_img    =   samples_parse_df.iloc[i]['Img']
			_slide  =   samples_parse_df.iloc[i]['Slide']
			_area   =   samples_parse_df.iloc[i]['Area']

			add_args['probe_set']	=	f"{work_ref}/{ref[_seq_type]._get_params()[_ref]['probe-set']}"
			add_args['img']			=	_img
			add_args['area']		=	_area
			add_args['slide']		=	_slide
			
		elif _seq_type == 'SC_SeekGene_VDJ':
			_chain	=	samples_parse_df.iloc[i]['VDJ_type']
			add_args['chain']	=	_chain
		
		if 'SC_SeekGene_VDJ' in typeseq:
			_chemistry	=	'DD5V1'
			if _seq_type == 'SC_SeekGene_RNA':
				result_dir_all	= f"{work_run}/{results['SC_SeekGene_VDJ']._get_params()['local']}"
				ceph_res		= f"{results['SC_SeekGene_VDJ']._get_params()['ceph']}"	
			add_args['chemistry']	=	_chemistry
		elif 'TENX' in _seq_type:
			add_args['memory']		=	_memory
		postfix			=	f"{results[_seq_type]._get_params()['postfix']}"
		sample_res 		= 	glob(f"{result_dir_all}/{_flowcell}/{_sample}*/*{postfix}")

		if len(sample_res) == 0:
			try: 
				module          =   dynamic_import(f'{work_run}/{_cmd}')
				functions       =   inspect.getmembers(module, inspect.isfunction)
				process 	    =   functions[0][0]

				if hasattr(module, process):
					process_function	= 	getattr(module, process)
					args				=	{"sample"		:	_sample,
							   				 "flowcell"		:	_flowcell,
											 "ref_dir"		:	res_dir_all,
											 "toolpath"		:	toolpath_all,
											 "result_dir"	:	result_dir_all,
											 "data_dir"		:	data_dir_all,
											 "core"			:	_core,
											 }
					if add_args:
						args.update(add_args)
					os.makedirs(f"{result_dir_all}/{_flowcell}", exist_ok=True)
					result = process_function(**args)

				log_file_path	=	 result[-1]
				log_file    	=   open(log_file_path, "w")
				log_files.append(log_file)
				run_process = subprocess.Popen(result[0],
											stdout=log_file,  
											stderr=subprocess.STDOUT,
											cwd=f"{result_dir_all}/{_flowcell}")
				processes.append(run_process)
				time.sleep(2)

			except Exception as e:
				print(f"Failed to process {_cmd}: {e}")    

			samples_parse_df.loc[i, 'Ceph_Path'] = ceph_res
		else:
			print("Process completed successfully.")


	for run_process in processes:
		run_process.wait()
		if run_process.returncode != 0:
			print(f"Process error (code: {run_process.returncode}).")
		else:
			print("Process completed successfully.")

	for log_file in log_files:
		log_file.close()

	print(f"{_flowcell} - over!")
	print("-----------------------------------------------------")
		

