def cellplex_generate_csv(
						flowcell:str,				# 240427_A00926_0778_BHMKJMDRXY
						sample:str,					# 770931560000_770931780000_770931860000_770932040000
						ref_dir: str,
						result_dir: str,
						data_dir: str,
						org_prefix: str,			# h
						cmo_cellplex:str,			# GEX_Pool0002|CMO309_CMO310_CMO311_CMO312
						samples_plex_cellplex:list	# [GEX, MUX]
						  ) -> None:
	
	path_to_csv	=	f'{result_dir}/{sample}_CellPlex.csv'
	with open(path_to_csv, "w") as f:
		f.write('[gene-expression]\n')
		f.write(f'reference,{ref_dir}\n')
		f.write('create-bam,true\n\n')

		f.write('[libraries]\n')
		f.write('fastq_id,fastqs,feature_types\n')

		for sample_cellples in samples_plex_cellplex:
			library_type 	= 	sample_cellples.split('|')[1]
			fastq_id		=	sample_cellples.split('|')[0]
			
			if 'GEX' in library_type:
				feature_type 	= 'Gene Expression'
			elif 'MUX' in library_type:
				feature_type	= 'Multiplexing Capture'
			
			f.write(f'{fastq_id},"{data_dir}",{feature_type}\n')

		f.write('\n[samples]\n')
		f.write('sample_id,cmo_ids\n')
		cmo_ids_str = '|'.join(cmo_cellplex.split('_'))
		f.write(f'"{sample}_{org_prefix}","{cmo_ids_str}"\n')
		f.close()
	return path_to_csv