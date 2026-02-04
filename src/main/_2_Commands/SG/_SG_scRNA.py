from    glob import glob

def _scRNA( flowcell:str,
            sample:str,
            ref_dir:str,
            result_dir:str,
            data_dir:str,
            core:int,
            toolpath:str,
            org_prefix:str,
            log_file:str,
            chemistry:str = 'DDV2',
            more_arg:list = []
           ):

        fastqs      =   sorted(glob(f"{data_dir}/{sample}_S*gz"))
        fastqs_cmd  = []
        for f_fq in fastqs:
            if '_R1_' in f_fq:
                fastqs_cmd.extend(['--fq1', f'{f_fq}'])
            elif '_R2_' in f_fq:
                fastqs_cmd.extend(['--fq2', f'{f_fq}'])
        
        command     =   [f"{toolpath}/seeksoultools","rna","run",
                         "--samplename",      f"{sample}_{org_prefix}",
                         "--outdir",          f"{result_dir}",
                         "--genomeDir",       f"{ref_dir}/star",
                         "--gtf",             f"{ref_dir}/genes/genes.gtf",
                         "--chemistry",       f"{chemistry}",
                         "--core",            f"{core}",
                         "--include-introns"
                        ] + more_arg + fastqs_cmd

        return command, log_file