import pandas as pd
from datetime import datetime
import re

def extract_date_from_flowcell(flowcell):
	if pd.isna(flowcell):
		return None
	
	# Ищем первые 6 цифр
	match = re.search(r'(\d{6})', str(flowcell))
	if match:
		date_str = match.group(1)
		try:
			return datetime.strptime(date_str, '%y%m%d')
		except ValueError:
			return None
	return None

def process_multiome_data(df:pd.DataFrame,
						  valid_types:list,
						  max_date_diff:int):
	result_df       =   df.copy()
	multiome_mask   =   result_df['Desct_TYPE'].str.contains('Multiome', na=False)
	multiome_df     =   result_df[multiome_mask].copy()
	
	if multiome_df.empty:
		print("⚠️[3.0.2 Conver multiome] No contains Multiome in Desct_TYPE")
		return result_df
	
	invalid_multiome_types  =   set(multiome_df['Desct_TYPE'].unique()) - set(valid_types)
	if invalid_multiome_types:
		print(f"⚠️[3.0.2 Conver multiome] Find Multiome not supported types")
		for t in invalid_multiome_types:
			print(f"👉[3.0.2 Conver multiome] {t}")
	
	multiome_df     =   multiome_df[multiome_df['Desct_TYPE'].isin(valid_types)].copy()
	if multiome_df.empty:
		print("⚠️[3.0.2 Conver multiome] Not Multiome in supported types")
		return result_df
	
	processed_samples = set()
	rows_to_drop = [] 
	
	for sample_id, group in multiome_df.groupby('Sample_ID'):
		if len(group) < 2:
			print(f"⚠️[3.0.2 Conver multiome] For Sample_ID '{sample_id}' find only {len(group)} record Multiome.\n⚠️[Conver multiome] Need 2 (RNA and ATAC).")
			continue
		
		rna_records     =   group[group['Desct_TYPE'].str.endswith('_RNA')]
		atac_records    =   group[group['Desct_TYPE'].str.endswith('_ATAC')]
		
		if rna_records.empty or atac_records.empty:
			print(f"⚠️[3.0.2 Conver multiome] For Sample_ID '{sample_id}' not foundet RNA and ATAC")
			continue
		
		rna_record      =   rna_records.iloc[0]
		atac_record     =   atac_records.iloc[0]

		rna_date        =   extract_date_from_flowcell(rna_record['Flowcell'])
		atac_date       =   extract_date_from_flowcell(atac_record['Flowcell'])
		
		if rna_date and atac_date:
			actual_date_diff = abs((rna_date - atac_date).days)
			if actual_date_diff > max_date_diff:
				print(f"⚠️[3.0.2 Conver multiome] For Sample_ID '{sample_id}' data diff in Flowcell name: {actual_date_diff} days (> {max_date_diff} days)")
				continue
		
		base_type       =   rna_record['Desct_TYPE'].replace('_RNA', '')
		new_flowcell    =   f"{rna_record['Flowcell']}-{atac_record['Flowcell']}"

		rna_desc        =   str(rna_record['Description']).strip() if not pd.isna(rna_record['Description']) else ''
		atac_desc       =   str(atac_record['Description']).strip() if not pd.isna(atac_record['Description']) else ''

		if rna_desc and atac_desc:
			if rna_desc == atac_desc:
				new_description = rna_desc
			else:
				unique_descriptions = []
				if rna_desc and rna_desc not in unique_descriptions:
					unique_descriptions.append(rna_desc)
				if atac_desc and atac_desc not in unique_descriptions:
					unique_descriptions.append(atac_desc)
				new_description = '|'.join(unique_descriptions)
		elif rna_desc:
			new_description = rna_desc
		elif atac_desc:
			new_description = atac_desc
		else:
			new_description = ''

		rna_idx         =   rna_record.name
		atac_idx        =   atac_record.name

		result_df.at[rna_idx, 'Flowcell'] = new_flowcell
		result_df.at[rna_idx, 'Description'] = new_description
		result_df.at[rna_idx, 'Desct_TYPE'] = base_type
	
		for column in result_df.columns:
			if column not in ['Flowcell', 'Desct_TYPE', 'Description']:
				rna_value = result_df.at[rna_idx, column]
				atac_value = result_df.at[atac_idx, column]

				if pd.isna(rna_value) and not pd.isna(atac_value):
					result_df.at[rna_idx, column] = atac_value
				elif not pd.isna(rna_value) and not pd.isna(atac_value) and rna_value != atac_value:
					result_df.at[rna_idx, column] = f"{rna_value}-{atac_value}"
		
		rows_to_drop.append(atac_idx)
		processed_samples.add(sample_id)

	if rows_to_drop:
		result_df = result_df.drop(rows_to_drop)
	
	print(f"✅[3.0.2 Conver multiome] Processed {len(processed_samples)} Multiome samples")
	return result_df



def process_cellplex_data(df:pd.DataFrame,
						  valid_types:list):

	result_df       =   df.copy()
	cellplex_mask   =   result_df['Desct_TYPE'].str.contains('CellPlex', na=False)
	cellplex_df     =   result_df[cellplex_mask].copy()

	if cellplex_df.empty:
		print("⚠️[3.0.2 Conver cellplex] No contains CellPlexs in Desct_TYPE")
		return result_df
	
	invalid_cellplex_types  =   set(cellplex_df['Desct_TYPE'].unique()) - set(valid_types)
	if invalid_cellplex_types:
		print(f"⚠️[3.0.2 Conver cellplex] Find CellPlex not supported types")
		for t in invalid_cellplex_types:
			print(f"👉[3.0.2 Conver cellplex] {t}")
	
	cellplex_df     =   cellplex_df[cellplex_df['Desct_TYPE'].isin(valid_types)].copy()
	if cellplex_df.empty:
		print("⚠️[3.0.2 Conver cellplex] Not CellPlex in supported types")
		return result_df
	
	processed_indices = []
	cellplex_df_converted   =   []

	for flowcell in cellplex_df['Flowcell'].unique():
		cellplex_df_flowcell = cellplex_df[cellplex_df['Flowcell'] == flowcell]
		
		if len(cellplex_df_flowcell) < 2:
			print(f"⚠️[3.0.2 Conver cellplex] For Flowcell '{flowcell}' find only {len(cellplex_df_flowcell)} record CellPlex.\n⚠️[Conver cellplex] Need 2 per sample (GEX and MUX).")
			continue
		
		processed_indices.extend(cellplex_df_flowcell.index.tolist())
		
		cellplex_df_flowcell[['CellPlex_ID', 'CMO', 'PLEX']] = cellplex_df_flowcell.apply(lambda x: extract_cellplex_data(x), axis=1)
		cellplex_df_flowcell = merge_plex_rows_compact(df = cellplex_df_flowcell)
		
		if len(cellplex_df_converted) == 0:
			cellplex_df_converted = cellplex_df_flowcell
		else:
			cellplex_df_converted = pd.concat([cellplex_df_converted, 
											   cellplex_df_flowcell],
											   axis=0,
											   ignore_index=True)
	
	result_df = result_df.drop(index=processed_indices)
	result_df = pd.concat([result_df, cellplex_df_converted], 
						   axis=0,
						   ignore_index=True)
	
	print(f"✅[3.0.2 Conver cellplex] Processed {len(cellplex_df)} CellPlex samples")
	return result_df

def extract_cellplex_data(x:str):
	flowcell	=	x['Flowcell']
	x 			=	x['Description']

	split_description	=	x.split(';')
	re_pattern_id	    =	re.compile(r"[Ii][Dd]=")
	re_pattern_cmo	    =	re.compile(r"[CcСс][MmМм][OoОо]=")
	re_pattern_plex	    =	re.compile(r"[PpРр][Ll][EeЕе][XxХх]=")

	cellplex_id		    =	[s for s in split_description if re_pattern_id.search(s)]
	cellplex_cmo	    =	[s for s in split_description if re_pattern_cmo.search(s)]
	cellplex_plex	    =	[s for s in split_description if re_pattern_plex.search(s)] 

	cellplex_id			=	re.sub(re_pattern_id,	"", cellplex_id[0]) 	if cellplex_id 		else None
	cellplex_cmo		=	re.sub(re_pattern_cmo,	"", cellplex_cmo[0]) 	if cellplex_cmo 	else None
	cellplex_plex		=	re.sub(re_pattern_plex,	"", cellplex_plex[0]) 	if cellplex_plex 	else None


	if len(cellplex_id) >= 64:
		s_ids = []
		for s_id in cellplex_id.split('_'):
			short_id = s_id.replace('770', '')[:5]
			s_ids.append(short_id)
		more_arg	= ['--description', cellplex_id]	
		sample 		= '_'.join(s_ids)
		cellplex_id	=	'770-' + sample

	if flowcell == '240402_A00926_0772_BHN5TTDRXY':
		cellplex_id		=	cellplex_id
		cellplex_cmo	=	'CMO301_CMO302_CMO303_CMO304_CMO305_CMO306_CMO307_CMO308'
		if 'barcode' in cellplex_plex:
			cellplex_plex	=	'MUX'
		elif 'cellplex' in cellplex_plex:
			cellplex_plex	=	'GEX'


	return pd.Series([cellplex_id, cellplex_cmo, cellplex_plex])

def merge_plex_rows_compact(df:pd.DataFrame):
	df 							= 	df.copy()
	df['CellPlex_Sample_ID']	=	df['Sample_ID']
	df['Sample_ID']				=	df['CellPlex_ID']
	df							=	df.drop(columns='CellPlex_ID')
	df['_is_gex'] 				= 	df['PLEX'] == 'GEX'
	df 							= 	df.sort_values(['Sample_ID', '_is_gex'], ascending=[True, False])
	def custom_agg(series):
		if series.name == '_is_gex':
			return None
		unique_vals = series.dropna().unique()
		if len(unique_vals) <= 1:
			return unique_vals[0] if len(unique_vals) == 1 else None
		gex_val = series.iloc[0] if df.loc[series.index[0], '_is_gex'] else None
		other_vals = [v for v in unique_vals if v != gex_val]
		if gex_val is not None:
			return f"{gex_val}|{'|'.join(map(str, other_vals))}" if other_vals else gex_val
		else:
			return '|'.join(map(str, unique_vals))
	result 			= 	df.groupby('Sample_ID').agg(custom_agg).reset_index()
	result 			= 	result.drop('_is_gex', axis=1, errors='ignore')
	result['CMO']	=	result['CMO'].apply(lambda x: fix_cmo_list(x))
	
	return result

def fix_cmo_list(CMO_string:str):
	CMO_list	=	CMO_string.split('_')
	if not CMO_list:
		return []
	numbers = []
	for item in CMO_list:
		digits = ''.join(filter(str.isdigit, item))
		if len(digits) >= 3:
			num = int(digits[:3])
			if num >= 301:
				numbers.append(num)
	
	if not numbers:
		return []
	numbers.sort()
	base_candidate = numbers[0]
	all_digits_list = [''.join(filter(str.isdigit, item)) for item in CMO_list]
	all_nums = []
	for digits in all_digits_list:
		if len(digits) >= 3:
			all_nums.append(int(digits[:3]))
		else:
			all_nums.append(None)
	for i in range(1, len(all_nums)):
		if all_nums[i] is not None and all_nums[i-1] is not None:
			if all_nums[i] - all_nums[i-1] == 1:
				base_candidate = all_nums[0]
				break
	if all_nums[0] is not None and all_nums[0] < 301:
		if len(all_nums) >= 4:
			if (all_nums[0] == 299 and all_nums[1] == 300 and 
				all_nums[2] == 301 and all_nums[3] == 302):
				return ["Error"]
		valid_nums = [n for n in all_nums if n is not None and n >= 301]
		if valid_nums:
			min_valid = min(valid_nums)
			base_candidate = min_valid - all_nums.index(min_valid)
		else:
			base_candidate = 301
	if base_candidate < 301:
		base_candidate = 301
	result = []
	for i in range(len(CMO_list)):
		expected_num = base_candidate + i
		if expected_num < 301:
			expected_num = 301
		result.append(f"CMO{expected_num}")
	
	result =	'_'.join(result)
	return result