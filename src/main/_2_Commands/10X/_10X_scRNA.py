def _scRNA( flowcell:str,
            sample:str,
            ref_dir:str,
            result_dir:str,
            data_dir:str,
            core:int,
            memory:int,
            toolpath:str,
            more_arg:list = []
           ):
        
        # Definition postfix (h for human, m for mouse)
        # Example:
        # sample_h
        if 'grch38' in ref_dir.lower():
            postfix = 'h' 
        elif 'mm10' in ref_dir.lower():
            postfix = 'm'
        elif 'macmul' in ref_dir.lower():
            postfix = 'mmul'
        
        # CMD for run tool
        command     =   [f"{toolpath}/cellranger","count",
                         "--id",            f"{sample}_{postfix}",
                         "--sample",        f"{sample}",
                         "--fastqs",        f"{data_dir}/{flowcell}",
                         "--transcriptome", f"{ref_dir}",
                         "--localcores",    f"{core}",
                         "--localmem",      f"{memory}",
                         "--create-bam",      "true"
                        ] + more_arg
        
        # LOG file with full output
        log_file    =   f"{result_dir}/{flowcell}/{sample}_{postfix}_output.log"

        return command, log_file