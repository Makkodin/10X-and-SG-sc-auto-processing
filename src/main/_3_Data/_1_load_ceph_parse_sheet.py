import  subprocess
from typing import Optional
def load_airflow_parse(info_sheet_ceph8:str,
                       info_sheet:str)-> Optional[str]:

    """
    Load parsing sheet (info by samples).

    :param info_sheet_ceph8 : Path to location file results_parsing.csv (/mnt/cephfs8_rw/functional-genomics/ofateev/Parse_df/results_parsing.csv).
    :param info_sheet       : Path to save file results_parsing.csv (SC_auto/1.Data/Info/results_parsing.csv).
    :return                 : Path to save file results_parsing.csv (SC_auto/1.Data/Info/results_parsing.csv).
    """
    load_com = ['rsync',
                info_sheet_ceph8, 
                info_sheet]
    try:
        subprocess.run(load_com, 
                       check    =   True,
                       stdout   =   subprocess.PIPE,
                       stderr   =   subprocess.PIPE)
        
        print(f"✅[Load sheet info] Rsync \033[1m{'1.Data' + info_sheet.split('/1.Data')[-1]}\033[0m complete!")
    except subprocess.CalledProcessError as e:
        print(f"❌[Load sheet info] Rsync error \033[1m{'1.Data' + info_sheet.split('/1.Data', 1)[-1]}\033[0m\nError code: {e.returncode}")
    return info_sheet