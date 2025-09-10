import warnings
warnings.filterwarnings("ignore")
warnings.simplefilter("ignore")

from    bs4 import BeautifulSoup as Soup 
from    typing  import  Optional
#import  re

from glob import glob
import subprocess

def get_runinfo(file:str)-> Optional[str]:
    """
    Parse RunInfo.xml file.

    :param file : Location RunInfo.xml in BCL folder.
    :return     : String for flag --use-bases-mask (Example: Y151,I8,Y8,Y151). 
    """
    try:
        with open(file, 'r', encoding='utf-8') as xml_file:
            soup = Soup(xml_file.read(), features='xml')
        reads = soup.find_all('Reads')
        index_read = ['Y', 'I', 'Y', 'Y']
        cycles = [read['NumCycles'] for read in reads if 'NumCycles' in read.attrs]
        if len(cycles) != len(index_read):
            raise ValueError("Length cycles != length index")
        result = ','.join(f"{index}{cycle}" for index, cycle in zip(index_read, cycles))
        return result

    except FileNotFoundError:
        print(f"❌ Error: {file} not found")
        return None
    except KeyError as e:
        print(f"❌ Error: <Reads>")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def bcl2fastq(
            bcl:str,
            fastq:str)-> Optional[str]:
    """
    Run bcl2fastq tool.

    :param bcl      : Location BCL flowcell folder (1.Data/BCL/FLOWCELL).
    :param fastq    : Location FASTQ folder (1.Data/FASTQ).
    :return         : Location FASTQ flowcell folder (1.Data/FASTQ/FLOWCELL).
    """
    
    flowcell    =   bcl.split('/')[-1]
    samplesheet =   glob(f'{bcl}/*csv')[0]
    command = [
        "bcl2fastq",
        "-l", "WARNING",
        "--runfolder-dir",  f"{bcl}",
        "--sample-sheet",   f"{samplesheet}",
        "--output-dir",     f"{fastq}/{flowcell}",
        "--stats-dir",      f"{fastq}/{flowcell}/Stats",
        "--reports-dir",    f"{fastq}/{flowcell}/Reports",
        "--no-lane-splitting"]
    
    copy_ss         =   ['sudo','rsync','--ignore-existing',
                        samplesheet, f'{fastq}/{flowcell}/']
    bcl2fastq_log_path  =   f"{fastq}/{flowcell}/bcl2fastq.log"
    bcl2fastq_log       =   open(bcl2fastq_log_path, "w")

    try:
        subprocess.run(
            command,
            stdout  =   bcl2fastq_log,
            stderr  =   subprocess.STDOUT
        )
        subprocess.run( copy_ss, 
                        check    =   True,
                        stdout   =   subprocess.PIPE,
                        stderr   =   subprocess.PIPE)
        
        print("✅ bcl2fastq successfully completed")
        print("✅ Rsync SampleSheet completed!")
        bcl2fastq_log.close()
        fastq_res   =   f'{fastq}/{flowcell}'

    except subprocess.CalledProcessError as e:
        print(f"❌ bcl2fastq error\nError code: {e.returncode}")
        fastq_res   =   False
    return fastq_res
    
def bcl2fastq_atac(
            bcl:str,
            fastq:str)-> Optional[str]:
    """
    Run bcl2fastq tool for ATAC folder.

    :param bcl      : Location BCL flowcell folder (1.Data/BCL/FLOWCELL).
    :param fastq    : Location FASTQ folder (1.Data/FASTQ).
    :return         : Location FASTQ flowcell folder (1.Data/FASTQ/FLOWCELL).
    """
    
    flowcell        =   bcl.split('/')[-1]
    samplesheet     =   glob(f'{bcl}/*csv')[0]
    runinfo         =   glob(f'{bcl}/RunInfo.xml')[0]
    runinfo_mask    =   get_runinfo(runinfo)

    command = [
        "bcl2fastq",
        "-l", "WARNING",
        f"--use-bases-mask={runinfo_mask}",
        "--runfolder-dir",                  f"{bcl}",
        "--sample-sheet",                   f"{samplesheet}",
        "--output-dir",                     f"{fastq}/{flowcell}",
        "--stats-dir",                      f"{fastq}/{flowcell}/Stats",
        "--reports-dir",                    f"{fastq}/{flowcell}/Reports",
        "--create-fastq-for-index-reads",
        "--minimum-trimmed-read-length",    "8",
        "--mask-short-adapter-read",        "8",
        "--no-lane-splitting"]
    
    copy_ss         =   ['sudo','rsync','--ignore-existing',
                        samplesheet, f'{fastq}/{flowcell}/']
    bcl2fastq_log_path  =   f"{fastq}/{flowcell}/bcl2fastq.log"
    bcl2fastq_log       =   open(bcl2fastq_log_path, "w")

    try:
        subprocess.run(
            command,
            stdout  =   bcl2fastq_log,
            stderr  =   subprocess.STDOUT
        )
        subprocess.run( copy_ss, 
                        check    =   True,
                        stdout   =   subprocess.PIPE,
                        stderr   =   subprocess.PIPE)
        
        print("✅[Demultiplex] bcl2fastq successfully completed")
        print("✅[Demultiplex] Rsync SampleSheet completed!")
        bcl2fastq_log.close()
        fastq_res   =   f'{fastq}/{flowcell}'

    except subprocess.CalledProcessError as e:
        print(f"❌[Demultiplex] bcl2fastq error\nError code: {e.returncode}")
        fastq_res   =   False
    return fastq_res




#def get_runinfo(file):
#    with open(file, 'r', encoding='utf-8') as xml:
#        soup = Soup(xml.read(), features='xml')
#
#    reads = soup.find_all('Reads')
#    str_reads = str(reads)
#
#    ind_read    = ['Y','I','Y','Y']
#    cycles      = re.findall(r'NumCycles="\d*"',str_reads) 
#
#    need_str = ''
#    for i in range(len(cycles)):
#        a = ind_read[i]
#        b = cycles[i].replace('"', '').replace('NumCycles=','')
#        if i != 3:
#            c = f'{a}{b},'
#        else: 
#            c = f'{a}{b}'
#
#        need_str = need_str + c
#    
#    return need_str