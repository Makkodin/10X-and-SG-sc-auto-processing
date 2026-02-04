from main._3_Processing._0_PREprocessing._2_modification.create_ss_Multiome import create_ss_tenx_multiome

def _scМultiome(flowcell:str,
            sample:str,
            ref_dir:str,
            result_dir:str,
            data_dir:str,
            core:int,
            toolpath:str,
            org_prefix:str,
            mutiome_tenx_path:str,
            log_file:str,
            memory:int,
            more_arg:list = []
           ):
        

        path_to_sample_tenx_multiome_sheet  =   create_ss_tenx_multiome(sample          =   sample,
                                                                        flowcell        =   flowcell,
                                                                        fastq_dir       =   data_dir,
                                                                        multiome_ss_dir =   mutiome_tenx_path,
                                                                       )
        
        # CMD for run tool
        command     =   [f"{toolpath}/cellranger-arc","count",
                         "--id",            f"{sample}_{org_prefix}",
                         "--libraries",     f"{path_to_sample_tenx_multiome_sheet}",
                         "--create-bam",    f"true",
                         "--reference",     f"{ref_dir}",
                         "--localcores",    f"{core}",
                         "--localmem",      f"{memory}"    
                        ] + more_arg

        return command, log_file