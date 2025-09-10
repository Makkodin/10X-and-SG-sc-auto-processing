import  os
import  subprocess
from    glob    import  glob
from    typing  import  Optional

def load_fastq(   
        flowcell:str,
        user:str,
        save_fastq:str,
        load_bcl:str,
        load_fastq:str,
        password:str)-> Optional[str]:
    """
    Load FASTQ data.

    :param flowcell     : Flowcell name.
    :param user         : Username (load from config file).
    :param save_fastq   : Path to save FASTQ data (1.Data/FASTQ)
    :param load_bcl     : Path to load BCL data from ceph (/mnt/cephfs3_ro/BCL/uvd*)
    :param load_fastq   : Path to load FASTQ data from ceph (/mnt/cephfs*_ro/FASTQS/uvd*)
    :param password     : Password (load from config file).
    :return             : Path to save BCL data (1.Data/FASTQ/FLOWCELL)
    """
    
    # Check exist folder fastq4 and SampleSheet
    fastq_flowcell_path =   f"{load_fastq}/{flowcell}_fastq4"
    ss_flowcell_path    =   f"{load_bcl}/{flowcell}"
    access_fastq        =   []
    access_ss           =   []

    # If ceph files not exist - load from cs11
    if os.path.exists(fastq_flowcell_path) == False:
        fastq_flowcell_path =   f"{user}@cs11:{load_fastq}/{flowcell}_fastq4"
        access_fastq        =   ["sshpass", "-p", f"{password}"]
    if os.path.exists(ss_flowcell_path) == False:
        ss_flowcell_path    =   f"{user}@cs11:{load_bcl}/{flowcell}/*.csv"
        access_ss           =   ["sshpass", "-p", f"{password}"]

    # rsync files
    os.makedirs(f"{save_fastq}/{flowcell}", exist_ok=True)
    load_fastq_cmd  =   access_fastq    + ["rsync","-r","--ignore-existing",
                                            f'{fastq_flowcell_path}/*', f"{save_fastq}/{flowcell}/"]
    load_ss_cmd     =   access_ss       + ["rsync","--ignore-existing",
                                            ss_flowcell_path, f"{save_fastq}/{flowcell}/"]
    try:

        subprocess.run( load_fastq_cmd, 
                        check    =   True,
                        stdout   =   subprocess.PIPE,
                        stderr   =   subprocess.PIPE,
                    )
        subprocess.run( load_ss_cmd, 
                        check    =   True,
                        stdout   =   subprocess.PIPE,
                        stderr   =   subprocess.PIPE,
                    )
        # If rsync done - ok
        if os.path.exists(f"{save_fastq}/{flowcell}"):
            print(f"✅[Load FASTQ] Rsync \033[1m{'1.Data' + save_fastq.split('/1.Data', 1)[-1]}/{flowcell}\033[0m complete!")

            ss_save = glob(f"{save_fastq}/{flowcell}/*.csv")
            if len(ss_save) == 1:
                print(f"✅[Load FASTQ] Rsync \033[1m{'1.Data' + ss_save[0].split('/1.Data', 1)[-1]}\033[0m complete!")
            else:
                print(f"❌[Load FASTQ] No exist SampleSheet!")
            fastq_res = f'{save_fastq}/{flowcell}'
        else:
            print(f"❌[Load FASTQ] No exist \033[1m{'1.Data' + save_fastq.split('/1.Data', 1)[-1]}/{flowcell}\033[0m!")
            fastq_res = False
        
    except subprocess.CalledProcessError as e:
        print(f"❌[Load FASTQ] Rsync error\nError code: {e.returncode}")
        fastq_res = False
    
    return fastq_res