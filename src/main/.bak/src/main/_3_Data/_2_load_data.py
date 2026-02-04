from main._3_Data.load_cmd.load_BCL              import  load_bcl
from main._3_Data.load_cmd.load_FASTQ            import  load_fastq
from main._3_Data.load_cmd.demultiplication      import  bcl2fastq, bcl2fastq_atac
from main._3_Data.preprocess.filter_reads_fastp  import  fastp_reads_with_repair

from typing import Optional


def load_flowcell(
    sample_id:str,
    flowcell:str,
    type_seq:str,
    bcl_save:str,   bcl_load:str,
    fastq_save:str, fastq_load:str,
    username:str,   password:str,
    filter_reads =  True,
    type_load_data:str = 'fastq',
    ) -> Optional[str]:
    print(f"🕒[Load data] Start to load/preprocessing flowcell \033[1m{flowcell}\033[0m")
    if type_load_data == 'bcl':
        bcl_res_folder      =   load_bcl( 
                                    flowcell    =   flowcell,
                                    user        =   username,
                                    save_bcl    =   bcl_save,
                                    load_bcl    =   bcl_load,
                                    password    =   password
                                    )
        if isinstance(type_seq, list) and any('atac' in str(item).lower() for item in type_seq) and any('tenx' in str(item).lower() for item in type_seq):
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
                                    sample_id   =   sample_id,
                                    flowcell    =   flowcell,
                                    user        =   username,   password    =   password,
                                    save_fastq  =   fastq_save, load_fastq  =   fastq_load,
                                    load_bcl    =   bcl_load,
                                    )
    
    if 'SC_SeekGene_FullRNA' in type_seq  and filter_reads == True:
        fastq_res_folder    =   fastp_reads_with_repair(
                                            fastq_save          =   fastq_save,
                                            flowcell            =   flowcell,
                                            core                =   16,
                                            min_length          =   60,
                                            max_len1            =   150,
                                            more_arg            =   [],
                                            run_repair          =   True)
    return fastq_res_folder
        
    