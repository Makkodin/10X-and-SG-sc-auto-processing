def _scATAC(flowcell:str,
            sample:str,
            ref_dir:str,
            result_dir:str,
            data_dir:str,
            core:int,
            toolpath:str,
            org_prefix:str,
            log_file:str,
            memory:int,
            more_arg:list = []
           ):
       
        command     =   [f"{toolpath}/cellranger-atac","count",
                         "--id",            f"{sample}_{org_prefix}",
                         "--sample",        f"{sample}",
                         "--fastqs",        f"{data_dir}",
                         "--reference",     f"{ref_dir}",
                         "--localcores",    f"{core}",
                         "--localmem",      f"{memory}"
                        ] + more_arg

        return command, log_file