import  getpass
import  re
import  pandas as pd
from    main._3_Processing._0_PREprocessing._1_load_data.CEPH_parse_sheet_load import load_airflow_parse
from    main._3_Processing._0_PREprocessing._2_modification.rename_flowcells import process_multiome_data, process_cellplex_data

# Password and user for load raw files and move to ceph
def get_credentials():
    """Get username and password securely"""
    username    =   input("⚙️ [Authorization] Enter username: ")
    password    =   getpass.getpass("⚙️ [Authorization] Enter password: ")
    return username, password

def get_mail_credentials():
    """Get username and password securely"""
    username    =   input("⚙️ [Authorization] Enter user mail: ")
    password    =   getpass.getpass("⚙️ [Authorization] Enter mail password: ")

    if "@" not in username:
        username = username + "@cspfmba.ru"
    return username, password

def update_info_sheet(  workdir:str,
                        info_sheet_ceph8:str,
                        info_sheet:str,
                        supported_types:list,
                        multiome_types:list,
                        cellplex_types:list,
                        max_date_diff:int):
    """Update info sheet and return sorted list of flowcells"""
    info_sheet_path         =   load_airflow_parse(
        workdir             =   workdir,
        info_sheet_ceph8    =   info_sheet_ceph8,
        info_sheet          =   info_sheet
    )
    info_sheet      =   pd.read_csv(info_sheet_path, low_memory=False)
    info_sheet      =   info_sheet[info_sheet['Desct_TYPE'].isin(supported_types)]
    info_sheet      =   info_sheet[[
                                'Flowcell',  'Sample_ID', 'Batch',
                                'Desct_TYPE','Descr_ORG', 'Description'
                                ]]
    info_sheet      =   process_multiome_data(df            =   info_sheet,
                                              valid_types   =   multiome_types,
                                              max_date_diff =   max_date_diff)
    info_sheet      =   process_cellplex_data(df            =   info_sheet,
                                              valid_types   =   cellplex_types)
    
    sorted_list     =   sorted(set(info_sheet['Flowcell']), 
                               reverse=True)
    return info_sheet, sorted_list