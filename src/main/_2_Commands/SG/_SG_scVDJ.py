from    glob import glob

def _scVDJ( flowcell:str,
            sample:str,
            ref_dir:str,
            result_dir:str,
            data_dir:str,
            core:int,
            toolpath:str,
            org_prefix:str,
            organism:str,
            log_file:str,
            chain:str,
            chemistry:str = 'DD5V1',
            more_arg:list = []
           ):
        fastqs      =   sorted(glob(f"{data_dir}/{sample}_S*gz"))
        fastqs_cmd  = []
        for f_fq in fastqs:
            if '_R1_' in f_fq:
                fastqs_cmd.extend(['--fq1', f'{f_fq}'])
            elif '_R2_' in f_fq:
                fastqs_cmd.extend(['--fq2', f'{f_fq}'])

        command     =   [f"{toolpath}/seeksoultools","vdj","run",
                         "--samplename",      f"{sample}_{org_prefix}",
                         "--outdir",          f"{result_dir}/{sample}_{org_prefix}",
                         "--chain",           f"{chain}",
                         "--organism",        f"{organism}",
                         "--chemistry",       f"{chemistry}",
                         "--core",            f"{core}"
                        ] + more_arg + fastqs_cmd
    
        return command, log_file