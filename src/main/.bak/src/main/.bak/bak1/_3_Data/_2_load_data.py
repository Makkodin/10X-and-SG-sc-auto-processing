from main._3_Data.load_cmd.load_BCL              import  load_bcl
from main._3_Data.load_cmd.load_FASTQ            import  load_fastq
from main._3_Data.load_cmd.demultiplication      import  bcl2fastq, bcl2fastq_atac
from main._3_Data.preprocess.filter_reads_fastp  import  fastp_reads_with_repair

from typing import Optional


def load_flowcell(
    type_seq:str,
    flowcell:str,
    bcl_save:str,
    fastq_save:str,
    bcl_load:str,
    fastq_load:str,
    username:str,
    password:str,
    filter_reads =  True,
    type_load_data:str = 'fastq',
    ) -> Optional[str]:

    """
    Load flowcell data (BCL/FASTQ).

    :param type_seq         : SeqType (load from parse sheet)).
    :param flowcell         : Flowcell name.
    :param bcl_save         : Path to save BCL.
    :param fastq_save       : Path to save FASTQ.
    :param bcl_load         : Path to load BCL from ceph.
    :param fastq_load       : Path to load FASTQ from ceph.
    :param username         : Username for download from another server.
    :param password         : Password for download from another server.
    :param type_load_data   : Data to load ('bcl' or 'fastq').
    :return                 : Path to FASTQ folder witj loaded files or False if error.
    """
    print(f"🕒[Load data] Start to load/preprocessing flowcell \033[1m{flowcell}\033[0m")
    if type_load_data == 'bcl':
        bcl_res_folder      =   load_bcl( 
                                    flowcell    =   flowcell,
                                    user        =   username,
                                    save_bcl    =   bcl_save,
                                    load_bcl    =   bcl_load,
                                    password    =   password
                                    )
        if 'atac' in type_seq.lower():
            fastq_res_folder    =   bcl2fastq_atac(
                                        bcl     =   bcl_res_folder,
                                        fastq   =   fastq_save
                                    )
        else:
           
            fastq_res_folder    =   bcl2fastq(
                                        bcl     =   bcl_res_folder,
                                        fastq   =   fastq_save
                                    )

    elif type_load_data == 'fastq':
        fastq_res_folder    =   load_fastq( 
                                    flowcell    =   flowcell,
                                    user        =   username,
                                    save_fastq  =   fastq_save,
                                    load_bcl    =   bcl_load,
                                    load_fastq  =   fastq_load,
                                    password    =   password
                                    )
    
    if  type_seq    ==  'SC_SeekGene_FullRNA' and filter_reads == True:
        fastq_res_folder    =   fastp_reads_with_repair(
                                            fastq_save          =   fastq_save,
                                            flowcell            =   flowcell,
                                            core                =   16,
                                            min_length          =   60,
                                            max_len1            =   150,
                                            more_arg            =   [],
                                            run_repair          =   True)
    return fastq_res_folder
        
    