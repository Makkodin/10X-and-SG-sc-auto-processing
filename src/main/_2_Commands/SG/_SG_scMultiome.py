from glob import glob

def _scMultiome(flowcell:str,
                sample:str,
                ref_dir:str,
                result_dir:str,
                data_dir:str,
                core:int,
                toolpath:str,
                org_prefix:str,
                log_file:str,
                more_arg:list = []
               ):
    flowcell_rna = flowcell.split('-')[0]
    flowcell_atac = flowcell.split('-')[1]

    data_dir       =   data_dir.rsplit('/', 1)[0]

    fastqs_rna = sorted(glob(f"{data_dir}/{flowcell_rna}/{sample}_S*gz"))
    fastqs_atac = sorted(glob(f"{data_dir}/{flowcell_atac}/{sample}_S*gz"))
    
    fastqs_cmd = []
    for f_fq in fastqs_rna:
        if '_R1_' in f_fq:
            fastqs_cmd.extend(['--rnafq1', f'{f_fq}'])
        elif '_R2_' in f_fq:
            fastqs_cmd.extend(['--rnafq2', f'{f_fq}'])
    
    for f_fq in fastqs_atac:
        if '_R1_' in f_fq:
            fastqs_cmd.extend(['--atacfq1', f'{f_fq}'])
        elif '_R2_' in f_fq:
            fastqs_cmd.extend(['--atacfq2', f'{f_fq}'])
    
    
    command = [f"{toolpath}/bin/seekarctools_py", "arc", "run",
               "--samplename", f"{sample}_{org_prefix}",
               "--outdir", f"{result_dir}/{sample}_{org_prefix}",
               "--refpath", f"{ref_dir}",
               "--include-introns",
               "--core", f"{core}",
              ] + more_arg + fastqs_cmd
    
    shell_command = f"""
source {toolpath}/bin/activate
{toolpath}/bin/conda-unpack
{' '.join(command)} 2>&1 | tee {log_file}
"""
    shell_cmd_list = ["bash", "-c", shell_command]
    
    return shell_cmd_list, log_file