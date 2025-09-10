def _visiumFFPE( flowcell:str,
            sample:str,
            ref_dir:str,
            result_dir:str,
            data_dir:str,
            core:int,
            memory:int,
            probe_set:str,
            img:str,
            area:str,
            slide:str,
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
        command     =   [   f"{toolpath}/spaceranger","count",
                            f"--id={sample}_{postfix}",
                            f"--sample={sample}",
                            f"--fastqs={data_dir}/{flowcell}",
                            f"--transcriptome={ref_dir}",
                            f"--probe-set={probe_set}",
                            f"--image={img}",
                            f"--area={area}",
                            f"--slide={slide}",
                            f"--localcores={core}",
                            f"--localmem={memory}",
                            f"--create-bam=true"
                        ] + more_arg
        
        # LOG file with full output
        log_file    =   f"{result_dir}/{flowcell}/{sample}_{postfix}_output.log"

        return command, log_file