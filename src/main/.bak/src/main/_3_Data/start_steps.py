import  getpass
import  pandas as pd
from    main._3_Data._1_load_ceph_parse_sheet          import load_airflow_parse


supported_types =   [
                        'SC_TENX_RNA',
                        'SC_SeekGene_FullRNA',
                        'SC_TENX_ATAC',
                        'SC_SeekGene_RNA',
                        'SC_SeekGene_VDJ',
                        'SC_TENX_Multiome_RNA',
                        'SC_TENX_Multiome_ATAC',
                        'SC_SeekGene_Multiome_RNA',
                        'SC_SeekGene_Multiome_ATAC'
                    ]

warning_types	=	['SC_TENX_Multiome_RNA',
                     'SC_TENX_Multiome_ATAC',
                     'SC_SeekGene_Multiome_RNA',
                     'SC_SeekGene_Multiome_ATAC']

# Password and user for load raw files and move to ceph
def get_credentials():
    """Get username and password securely"""
    username    =   input("⚙️ [Authorization] Enter username: ")
    password    =   getpass.getpass("⚙️ [Authorization] Enter password: ")
    return username, password

def get_mail_credentials():
    """Get username and password securely"""
    username = input("⚙️ [Authorization] Enter user mail: ")
    password = getpass.getpass("⚙️ [Authorization] Enter mail password: ")

    if "@" not in username:
        username = username + "@cspfmba.ru"
    return username, password

def update_info_sheet():
    """Update info sheet and return sorted list of flowcells"""
    info_sheet_path         =   load_airflow_parse(
        info_sheet_ceph8    =   '/mnt/cephfs8_rw/functional-genomics/ofateev/Parse_df/results_parsing.csv',
        info_sheet          =   '/mnt/raid0/ofateev/projects/SC_auto/1.Data/Info/results_parsing.csv'
    )
    info_sheet = pd.read_csv(info_sheet_path)
    info_sheet      =   info_sheet[info_sheet['Desct_TYPE'].isin(supported_types)]
    sorted_list     =   sorted(set(info_sheet['Flowcell']), reverse=True)
    return info_sheet, sorted_list


#def update_info_sheet():
#    """Update info sheet and return sorted list of flowcells"""
#    info_sheet_path = load_airflow_parse(
#        info_sheet_ceph8='/mnt/cephfs8_rw/functional-genomics/ofateev/Parse_df/results_parsing.csv',
#        info_sheet='/mnt/raid0/ofateev/projects/SC_auto/1.Data/Info/results_parsing.csv'
#    )
#    info_sheet = pd.read_csv(info_sheet_path, low_memory=False)
#    info_sheet = info_sheet[info_sheet['Desct_TYPE'].isin(supported_types)]
#    warning_types = ['SC_TENX_Multiome_RNA', 'SC_TENX_Multiome_ATAC', 
#                     'SC_SeekGene_Multiome_RNA', 'SC_SeekGene_Multiome_ATAC']
#    all_flowcells = set(info_sheet['Flowcell'])
#    multiome_df = info_sheet[info_sheet['Desct_TYPE'].isin(warning_types)].copy()
#    sample_dict = {}
#    for _, row in multiome_df.iterrows():
#        sample_id = row['Sample_ID']
#        flowcell = row['Flowcell']
#        desc_type = row['Desct_TYPE']
#        if sample_id not in sample_dict:
#            sample_dict[sample_id] = {'TENX_RNA': None, 'TENX_ATAC': None, 
#                                      'SeekGene_RNA': None, 'SeekGene_ATAC': None}
#        if 'TENX' in desc_type and 'RNA' in desc_type:
#            sample_dict[sample_id]['TENX_RNA'] = flowcell
#        elif 'TENX' in desc_type and 'ATAC' in desc_type:
#            sample_dict[sample_id]['TENX_ATAC'] = flowcell
#        elif 'SeekGene' in desc_type and 'RNA' in desc_type:
#            sample_dict[sample_id]['SeekGene_RNA'] = flowcell
#        elif 'SeekGene' in desc_type and 'ATAC' in desc_type:
#            sample_dict[sample_id]['SeekGene_ATAC'] = flowcell
#    multiome_pairs = []
#    used_flowcells = set()
#    for sample_id, flows in sample_dict.items():
#        for tech in ['TENX', 'SeekGene']:
#            rna = flows.get(f'{tech}_RNA')
#            atac = flows.get(f'{tech}_ATAC')
#            if rna and atac:
#                pair = [rna, atac]
#                multiome_pairs.append(pair)
#                used_flowcells.add(rna)
#                used_flowcells.add(atac)
#    unique_pairs = []
#    seen = set()
#    for pair in multiome_pairs:
#        pair_tuple = tuple(pair)
#        if pair_tuple not in seen:
#            seen.add(pair_tuple)
#            unique_pairs.append(pair)
#    sorted_list = []
#    single_flowcells = sorted([fc for fc in all_flowcells if fc not in used_flowcells], reverse=True)
#    sorted_list.extend(single_flowcells)
#    unique_pairs_sorted = sorted(unique_pairs, key=lambda x: x[0], reverse=True)
#    sorted_list.extend(unique_pairs_sorted)
#    def extract_date(element):
#        if isinstance(element, list):
#            return element[0][:6]
#        else:
#            return element[:6]
#    date_groups = {}
#    for item in sorted_list:
#        date = extract_date(item)
#        if date not in date_groups:
#            date_groups[date] = []
#        date_groups[date].append(item)
#    unique_dates = sorted(set(extract_date(item) for item in sorted_list), reverse=True)
#    filtered_list = []
#    for date in unique_dates:
#        filtered_list.extend(date_groups[date])
#    
#    return info_sheet, filtered_list
#

