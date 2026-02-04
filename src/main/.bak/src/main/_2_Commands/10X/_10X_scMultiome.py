from main._3_Data.preprocess.create_ss_Multiome import create_ss_tenx_multiome

def _scМultiome(flowcell:list,
            sample:str,
            ref_dir:str,
            result_dir:str,
            data_dir:str,
            core:int,
            memory:int,
            toolpath:str,
            more_arg:list = []
           ):
        


        if 'grch38' in ref_dir.lower():
            postfix = 'h' 
        elif 'mm10' in ref_dir.lower():
            postfix = 'm'
        elif 'macmul' in ref_dir.lower():
            postfix = 'mmul'

        path_to_sample_tenx_multiome_sheet  =   create_ss_tenx_multiome(sample          =   sample,
                                                                        org_postfix     =   postfix,
                                                                        fastq_dir       =   data_dir,
                                                                        multiome_ss_dir =   result_dir,
                                                                        flowcell        =   flowcell)
        
        # CMD for run tool
        command     =   [f"{toolpath}/cellranger-arc","count",
                         "--id",            f"{sample}_{postfix}",
                         "--libraries",     f"{path_to_sample_tenx_multiome_sheet}",
                         "--create-bam",    f"true",
                         "--reference",     f"{ref_dir}",
                         "--localcores",    f"{core}",
                         "--localmem",      f"{memory}"    
                        ] + more_arg
        # LOG file with full output
        log_file    =   f"{result_dir}/{flowcell}/{sample}_{postfix}_output.log"

        return command, log_file