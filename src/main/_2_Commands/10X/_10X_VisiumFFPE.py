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
            org_prefix:str,
            log_file:str,
            more_arg:list = []
           ):
        
        
        # CMD for run tool
        command     =   [   f"{toolpath}/spaceranger","count",
                            f"--id={sample}_{org_prefix}",
                            f"--sample={sample}",
                            f"--fastqs={data_dir}",
                            f"--transcriptome={ref_dir}",
                            f"--probe-set={probe_set}",
                            f"--image={img}",
                            f"--area={area}",
                            f"--slide={slide}",
                            f"--localcores={core}",
                            f"--localmem={memory}",
                            f"--create-bam=true"
                        ] + more_arg

        return command, log_file