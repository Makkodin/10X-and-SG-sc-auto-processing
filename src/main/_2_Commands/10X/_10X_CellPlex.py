from main._3_Processing._0_PREprocessing._2_modification.create_ss_CellPlex import cellplex_generate_csv

def _CellPlex(  flowcell:str,
					 sample:str,
					 ref_dir:str,
					 result_dir:str,
					 data_dir:str,
					 core:int,
					 toolpath:str,
					 org_prefix:str,
					 log_file:str,
					 memory:int,
					 cmo_cellplex:str,
					 samples_cellplex:str,
					 plex_cellplex:str,
					 more_arg:list = []
			  ):

		samples_cellplexs  		=   samples_cellplex.split('|')
		plex_cellplexs    	 	=   plex_cellplex.split('|')
		samples_plex_cellplex 	=  	[f'{samples_cellplexs[0]}|{plex_cellplexs[0]}',
									f'{samples_cellplexs[1]}|{plex_cellplexs[1]}']
		if len(sample) >= 64:
			s_ids = []
			for s_id in sample.split('_'):
				short_id = s_id.replace('770', '')[:5]
				s_ids.append(short_id)
			more_arg	= ['--description', sample]	
			sample 	= '_'.join(s_ids)
			sample	=	'770-' + sample

		if flowcell != '240607_A00923_0804_BHMKYVDRXY':
			path_to_sample_tenx_cellplex_sheet  =   cellplex_generate_csv(
																							  flowcell    =   flowcell,
																							  sample      =   sample,
																							  ref_dir     =   ref_dir,
																							  result_dir  =   result_dir,
																							  data_dir    =   data_dir,
																							  org_prefix  =   org_prefix,
																							  cmo_cellplex            =   cmo_cellplex,
																							  samples_plex_cellplex   =   samples_plex_cellplex)
			command     =   [f"{toolpath}/cellranger","multi",
									 "--id",            f"{sample}_{org_prefix}",
									 "--csv",           path_to_sample_tenx_cellplex_sheet,
									 "--localcores",    str(core),
									 "--localmem",      str(memory)
									]   + more_arg
		else:
			samples_plex_cellplex	=	[x.split('|')[0] for x in samples_plex_cellplex if 'GEX' in x][0]
			command     			=   [f"{toolpath}/cellranger","count",
                        			 	"--id",            f"{sample}_{org_prefix}",
                        			 	"--sample",        f"{samples_plex_cellplex}",
                        			 	"--fastqs",        f"{data_dir}",
                        			 	"--transcriptome", f"{ref_dir}",
                        			 	"--localcores",    f"{core}",
                        			 	"--localmem",      f"{memory}",
                        			 	"--create-bam",      "true"
                        			] + more_arg



		return command, log_file