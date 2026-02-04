import  os
import  subprocess
from    typing  import  Optional

def load_bcl(   
        flowcell:str,
        user:str,
        save_bcl:str,
        load_bcl:str,
        password:str)-> Optional[str]:
    """
    Load BCL data.

    :param flowcell : Flowcell name.
    :param user     : Username (load from config file).
    :param save_bcl : Path to save BCL data (1.Data/BCL)
    :param load_bcl : Path to load BCL data from ceph (/mnt/cephfs3_ro/BCL/uvd*)
    :param password : Password (load from config file).
    :return         : Path to save BCL data (1.Data/BCL/FLOWCELL)
    """
    # Check exist folder
    bcl_flowcell_path   =   f"{load_bcl}/{flowcell}"
    access              =   []
    # If ceph folder not exist - load from cs11
    if os.path.exists(bcl_flowcell_path) == False:
        bcl_flowcell_path   =   f"{user}@cs11:{load_bcl}/{flowcell}"
        access              =   ["sshpass", "-p", f"{password}"]
    # rsync files
    load_cmd    =   access + ["rsync","-r","--ignore-existing",
                              bcl_flowcell_path, f"{save_bcl}/"]
    try:
        subprocess.run( load_cmd, 
                        check    =   True,
                        stdout   =   subprocess.PIPE,
                        stderr   =   subprocess.PIPE,
                    )
        # If rsync done - ok
        if os.path.exists(f"{save_bcl}/{flowcell}"):
            print(f"✅[Load BCL] Rsync {save_bcl}/{flowcell} complete!")
            bcl_res = f'{save_bcl}/{flowcell}'
        else:
            print(f"❌[Load BCL] No exist {save_bcl}/{flowcell}!")
            bcl_res = False
            
        
    except subprocess.CalledProcessError as e:
        print(f"❌[Load BCL] Rsync error\nError code: {e.returncode}")
        bcl_res = False

    return bcl_res
