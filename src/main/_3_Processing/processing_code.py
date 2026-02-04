# source /mnt/raid0/ofateev/soft/seeksoultools.1.3.0/external/conda/bin/activate
import os
import warnings

warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"
import 	re
import 	traceback
import	pandas 		as 		pd
from 	glob 		import 	glob
from    tabulate 	import 	tabulate

from main._3_Processing._0_PREprocessing.skip_flowcells 						import 	add_to_skip_flowcells
from main._3_Processing._0_PREprocessing.already_process_flowcell				import 	add_to_processed_flowcells
from main._3_Processing._0_PREprocessing._2_modification.description_process 	import 	extract_slide_info, extract_area_info,\
																						find_image_path, extract_vdj_type, extract_tissue
from main._3_Processing._1_MAINprocessing._1_load_data  						import 	load_flowcell
from main._3_Processing._1_MAINprocessing._2_FLOWCELL_processing 				import 	processing_flowcell
from main._3_Processing._1_MAINprocessing._3_Create_Sumdir						import 	check_and_move_reports
from main._3_Processing._2_POSTprocessing.report.email_reporter					import 	archive_and_send_report
from main._3_Processing._2_POSTprocessing.move_and_remove						import 	move_and_remove

def print_upload_dict(flowcell_sample_processed:dict):
	table_data = []
	for key, data in flowcell_sample_processed.items():
		table_data.append({
			'Sample_ID'			: 	data.get('Sample_ID', key.split(':')[1] if ':' in key else key),
			'Flowcell'			: 	data.get('Flowcell', key.split(':')[0] if ':' in key else 'Unknown'),
			'Reference'			: 	data.get('Organism', data.get('Prefix reference', 'Unknown')),
			'SEQtype'			: 	data.get('SeqType', 'Unknown'),
			'Tissue'			: 	data.get('Tissue', 'Unknown'),
			'Load\nFastq'		: 	'✅' if data.get('Load_Status', False) else '❌',
			'Processed\nstatus'	: 	'✅' if data.get('Processed status', False) else '❌',
			'Annotation\nstatus': 	'✅' if data.get('Annotation status', False) else '⚠️'
		})
	print(tabulate(	table_data, 
					headers		=	'keys',
					tablefmt	=	'psql'))

def full_process_flowcell(
						info_sheet:pd.DataFrame, 
						flowcell_name:str, 
						username:str,     password:str,
						sender_email:str, sender_password:str,
						type_load_data:str,
						skip_flowcells:list,
						processed_flowcells:list,
						TypeConfig:type, 
						REFs_ORG_compare:dict,
						REFs_ORG_prefix:dict,
						SOFT_local_dir:str,
						REFS_local_dir:str,
						Fastp_params:dict,
						workdir:str,
						BCL_load:str,
						BCL_save:str,
						FASTQ_load:str,
						FASTQ_save:str,
						processed_skip:str,
						email_config:str                
					):
	
	try:
		"""
		Check if Flowcell in skip list  
		"""
		if flowcell_name in skip_flowcells:
			print(f"\033[92m❌[3 Processing] Flowcell {flowcell_name} in skip_flowcells list, skipping\033[0m")
			return False
		if flowcell_name in processed_flowcells:
			print(f"\033[92m✅[3 Processing] Flowcell {flowcell_name} in processed list, skipping\033[0m")
			return True
		df_flowcell_temp    =   info_sheet[info_sheet['Flowcell'] == flowcell_name]
		"""
		Check if Flowcell in info_sheet
		"""
		if df_flowcell_temp.empty:
			print(f"\033[91m❌[3 Processing] Flowcell {flowcell_name} not found in info_sheet\033[0m")
			return False

		"""
		Process sample in flowcell (sample by sample)
		"""
		sample_ids          =   df_flowcell_temp['Sample_ID'].unique()
		_refs_compare       =   REFs_ORG_compare
		_refs_prefix        =   REFs_ORG_prefix


		_flowcell_sample_status			=	[]
		_flowcell_sample_processed   	=   {}
		for sample_id in  sample_ids:
			# '240411_A01022_0750_AHNFHFDRXY:962000685201'
			df_flowcell_sample_id   =   df_flowcell_temp[df_flowcell_temp['Sample_ID'] == sample_id]
			# 'SC_SeekGene_RNA'
			seq_type                =   df_flowcell_sample_id['Desct_TYPE'].unique()[0]
			# 'human'
			organism                =   df_flowcell_sample_id['Descr_ORG'].unique()[0]
			# 'GRCh38'
			reference               =   _refs_compare[organism]
			# 'h'
			prefix                  =   _refs_prefix[organism]
			# 'species=human;biotype=blood;onco=normal'
			description             =   df_flowcell_sample_id['Description'].unique()[0]
			# 'seeksoultools.1.2.2'
			TOOL_VERSION            =   TypeConfig[seq_type]._get_tool_version()

			LOCAL_REFS_DIR          =   TypeConfig[seq_type]._get_params()[reference]['ref']
			LOCAL_TOOL_COMMAND      =   TypeConfig[seq_type]._get_params()['cmd']
			LOCAL_RESULTS           =   TypeConfig[seq_type]._get_params()['local']
			# '_summary.csv'
			LOCAL_STAT_POSTFIX      =   TypeConfig[seq_type]._get_params()['stat']
			# '_report.html'
			LOCAL_HTML_POSTFIX      =   TypeConfig[seq_type]._get_params()['postfix']
			# '/mnt/cephfs8_rw/functional-genomics/SG_SC_RES/scRNA/seeksoultools.1.2.2/240411_A01022_0750_AHNFHFDRXY'
			PATH_CEPH_RES           =   f"{TypeConfig[seq_type]._get_params()['ceph']}/{TOOL_VERSION}/{flowcell_name}"
			# False | True
			alredy_processed        =   False
			_find_files				=	[x for x in glob(f'{PATH_CEPH_RES}/{sample_id}_{prefix}') if '.bak' not in x]
			if len(_find_files) !=  0:
				alredy_processed    =   True

			# None |  '5', 'TR', 'IG'
			_vdj                    =   None
			# None | '/mnt/raid0/ofateev/soft/spaceranger-3.1.2/external/tenx_feature_references/targeted_panels/Visium_Human_Transcriptome_Probe_Set_v1.0_GRCh38-2020-A.csv'
			_ffpe_probeset			=	None
			# None | '/mnt/raid0/ofateev/projects/SC_auto/1.Data/Image/241118_A01022_0825_BHJMCNDRX5/770133303401_V11M15-277_A1_visimg.tif'
			_ffpe_img               =   None
			# None | 'V11M15-277'
			_ffpe_slide             =   None
			# None | 'A1
			_ffpe_area              =   None
			if seq_type     ==  'SC_SeekGene_VDJ':
				_vdj                    =   extract_vdj_type(description=description)
				if _vdj ==  '5':
					LOCAL_TOOL_COMMAND      =   TypeConfig['SC_SeekGene_RNA']._get_params()['cmd']
					LOCAL_STAT_POSTFIX      =   TypeConfig['SC_SeekGene_RNA']._get_params()['stat']
					LOCAL_HTML_POSTFIX      =   TypeConfig['SC_SeekGene_RNA']._get_params()['postfix']
			
			# 'FFPE'
			tissue  =   extract_tissue(description  =   description)

			# CellPlex
			CELLPLEX_ID, CELLPLEX_CMO, CELLPLEX_PLEX	=	None, None, None
			if seq_type     ==  'SC_TENX_CellPlex':
				CELLPLEX_ID		=	df_flowcell_sample_id['CellPlex_Sample_ID'].unique()[0]
				CELLPLEX_CMO	=	df_flowcell_sample_id['CMO'].unique()[0]
				CELLPLEX_PLEX	=	df_flowcell_sample_id['PLEX'].unique()[0]
			
			# '/mnt/raid0/ofateev/refs/SG_scRNA_GRCh38'
			PATH_LOCAL_REFS         =   f"{REFS_local_dir}/{LOCAL_REFS_DIR}"
			# '/mnt/raid0/ofateev/soft/seeksoultools.1.2.2'
			PATH_LOCAL_TOOL         =   f"{SOFT_local_dir}/{TOOL_VERSION}"
			# '/mnt/raid0/ofateev/projects/SC_auto/src_new/main/_2_Commands/SG/_SG_scRNA.py'
			PATH_LOCAL_TOOL_COMMAND =   f"{workdir}/{LOCAL_TOOL_COMMAND}"
			# '/mnt/raid0/ofateev/projects/SC_auto/2.Results/SG/scRNA/240411_A01022_0750_AHNFHFDRXY'
			PATH_LOCAL_RESULTS      =   f"{workdir}/{LOCAL_RESULTS}/{flowcell_name}" 
			# '/mnt/raid0/ofateev/projects/SC_auto/2.Results/SG/scRNA/240411_A01022_0750_AHNFHFDRXY/962000685201_h/*_summary.csv'
			PATH_LOCAL_STAT_POSTFIX =   f"{PATH_LOCAL_RESULTS}/{sample_id}_{prefix}/*{LOCAL_STAT_POSTFIX}"
			# '/mnt/raid0/ofateev/projects/SC_auto/2.Results/SG/scRNA/240411_A01022_0750_AHNFHFDRXY/962000685201_h/*_report.html'
			PATH_LOCAL_HTML_POSTFIX =   f"{PATH_LOCAL_RESULTS}/{sample_id}_{prefix}/*{LOCAL_HTML_POSTFIX}"
			# '/mnt/raid0/ofateev/projects/SC_auto/2.Results/SG/scRNA/240411_A01022_0750_AHNFHFDRXY/962000685201_h.log'
			PATH_LOCAL_LOG			=	f"{PATH_LOCAL_RESULTS}/{sample_id}_{prefix}.log"
			# '/mnt/raid0/ofateev/projects/SC_auto/2.Results/SG/scRNA/240411_A01022_0750_AHNFHFDRXY/240411_A01022_0750_AHNFHFDRXY-sum'
			PATH_LOCAL_SUM_STAT		=	f"{PATH_LOCAL_RESULTS}/{flowcell_name}-sum"

			# None | '/mnt/raid0/ofateev/projects/SC_auto/2.Results/SG/scRNA/240411_A01022_0750_AHNFHFDRXY/962000685201_h/step3/filtered_feature_bc_matrix/filtered_feature_bc_matrix_annotated_scParadise_*png'
			PATH_LOCAL_ANNOT_PNG	=	None
			if seq_type == 'SC_TENX_RNA':
				PATH_LOCAL_ANNOT_PNG		=	f"{PATH_LOCAL_RESULTS}/{sample_id}_{prefix}/outs/filtered_feature_bc_matrix_annotated_scParadise_*png"
			elif seq_type == 'SC_SeekGene_RNA':
				PATH_LOCAL_ANNOT_PNG		=	f"{PATH_LOCAL_RESULTS}/{sample_id}_{prefix}/step3/filtered_feature_bc_matrix/filtered_feature_bc_matrix_annotated_scParadise_*png"
			elif seq_type == 'SC_SeekGene_VDJ' and _vdj == '5':
				PATH_LOCAL_ANNOT_PNG		=	f"{PATH_LOCAL_RESULTS}/{sample_id}_{prefix}/step3/filtered_feature_bc_matrix/filtered_feature_bc_matrix_annotated_scParadise_*png"

			# None | '/mnt/cephfs8_rw/functional-genomics/SG_SC_RES/scRNA/seeksoultools.1.2.2/240411_A01022_0750_AHNFHFDRXY/962000685201_h/step3/filtered_feature_bc_matrix/filtered_feature_bc_matrix_annotated_scParadise_*png'
			PATH_CEPH_ANNOT_PNG	=	None
			if seq_type == 'SC_TENX_RNA':
				PATH_CEPH_ANNOT_PNG		=	glob(f"{PATH_CEPH_RES}/{sample_id}_{prefix}/outs/filtered_feature_bc_matrix_annotated_scParadise_*png")
				PATH_CEPH_ANNOT_PNG 	= 	PATH_CEPH_ANNOT_PNG[0] if PATH_CEPH_ANNOT_PNG else False
			elif seq_type == 'SC_SeekGene_RNA':
				PATH_CEPH_ANNOT_PNG		=	glob(f"{PATH_CEPH_RES}/{sample_id}_{prefix}/step3/filtered_feature_bc_matrix/filtered_feature_bc_matrix_annotated_scParadise_*png")
				PATH_CEPH_ANNOT_PNG 	= 	PATH_CEPH_ANNOT_PNG[0] if PATH_CEPH_ANNOT_PNG else False
			elif seq_type == 'SC_SeekGene_VDJ' and _vdj == '5':
				PATH_CEPH_ANNOT_PNG		=	glob(f"{PATH_CEPH_RES}/{sample_id}_{prefix}/step3/filtered_feature_bc_matrix/filtered_feature_bc_matrix_annotated_scParadise_*png")
				PATH_CEPH_ANNOT_PNG 	= 	PATH_CEPH_ANNOT_PNG[0] if PATH_CEPH_ANNOT_PNG else False
			
			if seq_type     ==  'SC_TENX_Visium_FFPE':
				LOCAL_IMG		=	f"{workdir}/{TypeConfig[seq_type]._get_params()['img']}"
				_ffpe_probeset	=	f"{PATH_LOCAL_TOOL}/{TypeConfig['SC_TENX_Visium_FFPE']._get_params()[reference]['probe-set']}"
				_ffpe_img   	=   find_image_path(    sample_id    	=   sample_id,
														flowcell		=	flowcell_name,
														img_save_dir 	=   LOCAL_IMG)
				_ffpe_slide 	=   extract_slide_info( img_path     =   _ffpe_img)
				_ffpe_area  	=   extract_area_info(  img_path     =   _ffpe_img)

			# None | '/mnt/raid0/ofateev/projects/SC_auto/2.Results/10X/Multiome/240918_A00926_0824_BHT35WDMXY-240917_VH00195_169_AAF7WJLM5/240918_A00926_0824_BHT35WDMXY-240917_VH00195_169_AAF7WJLM5:m0003168308-multiome.csv'
			if seq_type	==	'SC_TENX_Multiome':
				PATH_LOCAL_TENX_MULTIOME=	f"{PATH_LOCAL_RESULTS}/{flowcell_name}:{sample_id}-multiome.csv"
			else:
				PATH_LOCAL_TENX_MULTIOME=	None

			# '/mnt/raid0/ofateev/projects/SC_auto/1.Data/FASTQ/240918_A00926_0824_BHT35WDMXY'
			PATH_LOCAL_DATA			=	f"{FASTQ_save}/{flowcell_name}"	
		
			_flowcell_sample_processed[f'{flowcell_name}:{sample_id}']  =   {											# '240411_A01022_0750_AHNFHFDRXY:962000685201'
															'Sample_ID'                 :   sample_id,           		# '962000685201'
															'Flowcell'                  :   flowcell_name,      		# '240411_A01022_0750_AHNFHFDRXY'
															'SeqType'                   :   seq_type, 					# 'SC_SeekGene_RNA'
															'Organism'                  :   organism, 					# 'human'
															'Reference name' 			:	reference,					# 'GRCh38'
															'Prefix reference'          :   prefix,         			# 'h'
															'Path to refs'              :   PATH_LOCAL_REFS,    		# '/mnt/raid0/ofateev/refs/SG_scRNA_GRCh38'
															'Tissue'                    :   tissue,						# 'FFPE'
															'VDJ type'                  :   _vdj,       				# None | '5', 'TR', 'IG'
															'ProbeSet'         			:	_ffpe_probeset,				# None | '/mnt/raid0/ofateev/soft/spaceranger-3.1.2/external/tenx_feature_references/targeted_panels/Visium_Human_Transcriptome_Probe_Set_v1.0_GRCh38-2020-A.csv'
															'Image FFPE'                :   _ffpe_img,         			# None | '/mnt/raid0/ofateev/projects/SC_auto/1.Data/Image/241118_A01022_0825_BHJMCNDRX5/770133303401_V11M15-277_A1_visimg.tif'
															'Slide FFPE'                :   _ffpe_slide,         		# None | 'V11M15-277'
															'Area FFPE'                 :   _ffpe_area,					# None | 'A1
															'Tool version'              :   TOOL_VERSION,   			# 'seeksoultools.1.2.2'
															'Path install tool'         :   PATH_LOCAL_TOOL, 			# '/mnt/raid0/ofateev/refs/SG_scRNA_GRCh38'
															'Path cmd run'              :   PATH_LOCAL_TOOL_COMMAND,	# '/mnt/raid0/ofateev/projects/SC_auto/src_new/main/_2_Commands/SG/_SG_scRNA.py'
															'Path data'					:	PATH_LOCAL_DATA,			# '/mnt/raid0/ofateev/projects/SC_auto/1.Data/FASTQ/240918_A00926_0824_BHT35WDMXY'
															'Path local results'        :   PATH_LOCAL_RESULTS, 		# '/mnt/raid0/ofateev/projects/SC_auto/2.Results/SG/scRNA/240411_A01022_0750_AHNFHFDRXY'
															'Path local sum stat'		:	PATH_LOCAL_SUM_STAT,		# '/mnt/raid0/ofateev/projects/SC_auto/2.Results/SG/scRNA/240411_A01022_0750_AHNFHFDRXY/240411_A01022_0750_AHNFHFDRXY-sum'
															'Path ceph results'         :   PATH_CEPH_RES,  			# '/mnt/cephfs8_rw/functional-genomics/SG_SC_RES/scRNA/seeksoultools.1.2.2/240411_A01022_0750_AHNFHFDRXY'
															'Path result stat prefix'   :   PATH_LOCAL_STAT_POSTFIX,  	# '/mnt/raid0/ofateev/projects/SC_auto/2.Results/SG/scRNA/240411_A01022_0750_AHNFHFDRXY/962000685201_h/*_summary.csv'
															'Path result html prefix'   :   PATH_LOCAL_HTML_POSTFIX, 	# '/mnt/raid0/ofateev/projects/SC_auto/2.Results/SG/scRNA/240411_A01022_0750_AHNFHFDRXY/962000685201_h/*_report.html'
															'Result stat prefix'        :   LOCAL_STAT_POSTFIX,   		# '_summary.csv'
															'Result html prefix'        :   LOCAL_HTML_POSTFIX,   		# '_report.html'
															'Path log' 					:	PATH_LOCAL_LOG,				# '/mnt/raid0/ofateev/projects/SC_auto/2.Results/SG/scRNA/240411_A01022_0750_AHNFHFDRXY/962000685201_h.log'
															'Multiome 10X sheet'		:	PATH_LOCAL_TENX_MULTIOME,	# None | '/mnt/raid0/ofateev/projects/SC_auto/2.Results/10X/Multiome/240918_A00926_0824_BHT35WDMXY-240917_VH00195_169_AAF7WJLM5/240918_A00926_0824_BHT35WDMXY-240917_VH00195_169_AAF7WJLM5:m0003168308-multiome.csv'
															'Path local annotation png'	:	PATH_LOCAL_ANNOT_PNG,		# None | '/mnt/raid0/ofateev/projects/SC_auto/2.Results/SG/scRNA/240411_A01022_0750_AHNFHFDRXY/962000685201_h/step3/filtered_feature_bc_matrix/filtered_feature_bc_matrix_annotated_scParadise_*png'
															'Path ceph annotation png'	:	PATH_CEPH_ANNOT_PNG,		# None | False | '/mnt/cephfs8_rw/functional-genomics/SG_SC_RES/scRNA/seeksoultools.1.2.2/240411_A01022_0750_AHNFHFDRXY/962000685201_h/step3/filtered_feature_bc_matrix/filtered_feature_bc_matrix_annotated_scParadise_*png'
															'Processed status'          :   alredy_processed,			# True | False
															'CellPlex_ID'				:	CELLPLEX_ID,				# None | GEX_Pool0001|MUX_Pool0001
															'CellPlex_CMO'				:	CELLPLEX_CMO,				# None | CMO305_CMO306_CMO307_CMO308
															'CellPlex_PLEX'				:	CELLPLEX_PLEX				# None | GEX|MUX

															}
			_flowcell_sample_status.append(alredy_processed)
		#======================================================
		#======================================================
		# SPECIFIC PROCESSINGs
		if flowcell_name == '240607_A00923_0804_BHMKYVDRXY':
			for key, value in _flowcell_sample_processed.items():
				#value['SeqType']				=	'SC_TENX_RNA'
				#value['Path cmd run']			=	value['Path cmd run'].replace('_10X_CellPlex.py','_10X_scRNA.py')
				value['Path local results']		=	value['Path local results'].replace('CellPlex', 'scRNA')
				value['Path local sum stat']	=	value['Path local sum stat'].replace('CellPlex', 'scRNA')
				value['Path ceph results']		=	value['Path ceph results'].replace('CellPlex', 'scRNA')
				value['Path result stat prefix']=	value['Path result stat prefix'].replace('*outs/per_sample_outs/*/metrics_summary.csv', '*outs/metrics_summary.csv').replace('CellPlex', 'scRNA')
				value['Path result html prefix']=	value['Path result html prefix'].replace('*outs/per_sample_outs/*/web_summary.html', '*outs/web_summary.html').replace('CellPlex', 'scRNA')
				value['Result stat prefix']		=	value['Result stat prefix'].replace('outs/per_sample_outs/*/metrics_summary.csv', 'outs/web_summary.html')
				value['Result html prefix']		=	value['Result html prefix'].replace('outs/per_sample_outs/*/web_summary.html', 'outs/metrics_summary.csv')
				value['Path log']				=	value['Path log'].replace('CellPlex', 'scRNA')
		#======================================================
		#======================================================
		
		if False in _flowcell_sample_status:
			"""
			Start processa
			"""
			print("\033[91m" + "=" * 53 + "\033[0m")
			print(f"\033[92m🕐[3 Processing] Processing specified flowcell: {flowcell_name}\033[0m")
			"""
			Load flowcell data (sample by sample - fastq) (flowcell - bcl)
			"""
			# Output status load_flowcell
			# {'240411_A01022_0750_AHNFHFDRXY:962000685201'	: True,
			# '240411_A01022_0750_AHNFHFDRXY:962000695201'	: True}
			results =   load_flowcell(
									flowcell_sample_processed   =   _flowcell_sample_processed,
									bcl_load                    =   BCL_load, 
									bcl_save                    =   BCL_save,
									fastq_load                  =   FASTQ_load, 
									fastq_save                  =   FASTQ_save,
									username                    =   username, 
									password                    =   password,
									filter_reads                =   True,
									type_load_data              =   type_load_data,
									core                        =   Fastp_params['core'],
									min_length                  =   Fastp_params['min_length'],
									max_len1                    =   Fastp_params['max_len1'],
									fastq_parallel_workers      =   8,
									filter_parallel_samples     =   8)
			all_false = not any(results.values())
			if all_false == True:
				add_to_skip_flowcells(	path_to_file=	processed_skip,
							 			flowcell	=	flowcell_name, 
										reason		=	f"Processing error: {str(e)}")
				return False
			"""
			Add new keys to "_flowcell_sample_processed"
			"""
			for key in _flowcell_sample_processed:
				if key in results:
					_flowcell_sample_processed[key]['Load_Status'] = results[key]
				else:
					_flowcell_sample_processed[key]['Load_Status'] = False

			# +--------------+-------------------------------+-------------+-----------------+------------+--------------+--------------------+---------------------+
			# |    Sample_ID | Flowcell                      | Reference   | SEQtype         | Tissue     | Load Fastq   | Processed status   | Annotation status   |
			# |--------------+-------------------------------+-------------+-----------------+------------+--------------+--------------------+---------------------|
			# | 962000685201 | 240411_A01022_0750_AHNFHFDRXY | human       | SC_SeekGene_RNA | PBMC;cells | ✅           | ❌                 | ❌                  |
			# | 962000695201 | 240411_A01022_0750_AHNFHFDRXY | human       | SC_SeekGene_RNA | PBMC;cells | ✅           | ❌                 | ❌                  |
			# +--------------+-------------------------------+-------------+-----------------+------------+--------------+--------------------+---------------------+
			print_upload_dict(_flowcell_sample_processed)
			#'240411_A01022_0750_AHNFHFDRXY:962000685201': {
			#'Sample_ID'				: 	'962000685201',
  			#'Flowcell'					: 	'240411_A01022_0750_AHNFHFDRXY',
  			#'SeqType'					: 	'SC_SeekGene_RNA',
  			#'Organism'					: 	'human',
  			#'Reference name'			: 	'GRCh38',
  			#'Prefix reference'			: 	'h',
  			#'Path to refs'				: 	'/mnt/raid0/ofateev/refs/SG_scRNA_GRCh38',
  			#'Tissue'					: 	'PBMC;cells',
  			#'VDJ type'					: 	None,
  			#'ProbeSet'					: 	None,
  			#'Image FFPE'				: 	None,
  			#'Slide FFPE'				: 	None,
  			#'Area FFPE'				: 	None,
  			#'Tool version'				: 	'seeksoultools.1.2.2',
  			#'Path install tool'		: 	'/mnt/raid0/ofateev/soft/seeksoultools.1.2.2',
  			#'Path cmd run'				: 	'/mnt/raid0/ofateev/projects/SC_auto/src_new/main/_2_Commands/SG/_SG_scRNA.py',
  			#'Path data'				: 	'/mnt/raid0/ofateev/projects/SC_auto/1.Data/FASTQ/240411_A01022_0750_AHNFHFDRXY',
  			#'Path local results'		: 	'/mnt/raid0/ofateev/projects/SC_auto/2.Results/SG/scRNA/240411_A01022_0750_AHNFHFDRXY',
  			#'Path local sum stat'		: 	'/mnt/raid0/ofateev/projects/SC_auto/2.Results/SG/scRNA/240411_A01022_0750_AHNFHFDRXY/240411_A01022_0750_AHNFHFDRXY-sum',
  			#'Path ceph results'		: 	'/mnt/cephfs8_rw/functional-genomics/SG_SC_RES/scRNA/seeksoultools.1.2.2/240411_A01022_0750_AHNFHFDRXY',
  			#'Path result stat prefix'	: 	'/mnt/raid0/ofateev/projects/SC_auto/2.Results/SG/scRNA/240411_A01022_0750_AHNFHFDRXY/962000685201_h/*_summary.csv',
  			#'Path result html prefix'	: 	'/mnt/raid0/ofateev/projects/SC_auto/2.Results/SG/scRNA/240411_A01022_0750_AHNFHFDRXY/962000685201_h/*_report.html',
  			#'Result stat prefix'		: 	'_summary.csv',
  			#'Result html prefix'		: 	'_report.html',
  			#'Path log'					: 	'/mnt/raid0/ofateev/projects/SC_auto/2.Results/SG/scRNA/240411_A01022_0750_AHNFHFDRXY/962000685201_h.log',
  			#'Multiome 10X sheet'		: 	None,
  			#'Path local annotation png': 	'/mnt/raid0/ofateev/projects/SC_auto/2.Results/SG/scRNA/240411_A01022_0750_AHNFHFDRXY/962000685201_h/step3/filtered_feature_bc_matrix/filtered_feature_bc_matrix_annotated_scParadise_*png',
  			#'Path ceph annotation png'	: 	False,
  			#'Processed status'			: 	True,
  			#'Load_Status'				: 	True,
  			#'Annotation status'		: 	True,
			#'CellPlex_ID'				:	GEX_Pool0001|MUX_Pool0001
			#'CellPlex_CMO'				:	CMO305_CMO306_CMO307_CMO308
			#'CellPlex_PLEX'			:	GEX|MUX }
			_flowcell_sample_processed,overall_success	=	processing_flowcell(flowcell_sample_processed	=	_flowcell_sample_processed,
																				work_dir					=	workdir)

			# +--------------+-------------------------------+-------------+-----------------+------------+--------------+--------------------+---------------------+
			# |    Sample_ID | Flowcell                      | Reference   | SEQtype         | Tissue     | Load Fastq   | Processed status   | Annotation status   |
			# |--------------+-------------------------------+-------------+-----------------+------------+--------------+--------------------+---------------------|
			# | 962000685201 | 240411_A01022_0750_AHNFHFDRXY | human       | SC_SeekGene_RNA | PBMC;cells | ✅           | ✅                 | ✅                  |
			# | 962000695201 | 240411_A01022_0750_AHNFHFDRXY | human       | SC_SeekGene_VDJ | PBMC;cells | ✅           | ✅                 | ⚠️                  |
			# +--------------+-------------------------------+-------------+-----------------+------------+--------------+--------------------+---------------------+
			if overall_success == True:
				print_upload_dict(_flowcell_sample_processed)
				if flowcell_name == '240607_A00923_0804_BHMKYVDRXY':
					for key, value in _flowcell_sample_processed.items():
						value['SeqType']				=	'SC_TENX_RNA'
		
				_flowcell_sample_processed	=	check_and_move_reports(flowcell_sample_processed	=	_flowcell_sample_processed)
				archive_status				=	archive_and_send_report(
																	flowcell_sample_processed	=	_flowcell_sample_processed,
																	sender_email				=	sender_email,
																	sender_password				=	sender_password,
																	config_path					=	email_config
																)
				move_and_remove_status	= False
				if archive_status 	== True:
					move_and_remove_status	=	move_and_remove(flowcell_sample_processed	=	_flowcell_sample_processed,
												 				password					=	password)
				if move_and_remove_status 	== True:
					print(f"\033[92m🕐[3 Processing] All samples processed in flowcell: {flowcell_name}\033[0m")
					add_to_processed_flowcells(	path_to_file=	processed_skip,
								 				flowcell	=	flowcell_name, 
												reason		=	f"All samples {flowcell_name} processed")
					return True
			else:
				return False

		else:
			print("\033[91m" + "=" * 53 + "\033[0m")
			print(f"\033[92m🕐[3 Processing] All samples processed in flowcell: {flowcell_name}\033[0m")
			add_to_processed_flowcells(	path_to_file=	processed_skip,
							 			flowcell	=	flowcell_name, 
										reason		=	f"All samples {flowcell_name} processed")
			return True

	except Exception as e:
		error_msg = f"3 ERROR processing flowcell {flowcell_name}: {str(e)}"
		print(f"\033[91m{error_msg}\033[0m")
		print(f"Traceback: {traceback.format_exc()}")
		add_to_skip_flowcells(	path_to_file=	processed_skip,
							 	flowcell	=	flowcell_name, 
								reason		=	f"Processing error: {str(e)}")
		return False
