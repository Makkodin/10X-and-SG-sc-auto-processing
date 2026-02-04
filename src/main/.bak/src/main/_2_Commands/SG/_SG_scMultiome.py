from glob import glob

def _scMultiome(flowcell:list,
                sample:str,
                ref_dir:str,
                result_dir:str,
                data_dir:str,
                core:int,
                toolpath:str,
                more_arg:list = []
               ):
    flowcell_rna = flowcell.split('-')[0]
    flowcell_atac = flowcell.split('-')[1]
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
    
    if 'grch38' in ref_dir.lower():
        postfix = 'h' 
    elif 'mm10' in ref_dir.lower():
        postfix = 'm'
    elif 'macmul' in ref_dir.lower():
        postfix = 'mmul'
    
    command = [f"{toolpath}/bin/seekarctools_py", "arc", "run",
               "--samplename", f"{sample}_{postfix}",
               "--outdir", f"{result_dir}/{flowcell}/{sample}_{postfix}",
               "--refpath", f"{ref_dir}",
               "--include-introns",
               "--core", f"{core}",
              ] + more_arg + fastqs_cmd
    
    log_file = f"{result_dir}/{flowcell}/{sample}_{postfix}_output.log"
    
    shell_command = f"""
source {toolpath}/bin/activate
{toolpath}/bin/conda-unpack
{' '.join(command)} 2>&1 | tee {log_file}
"""
    shell_cmd_list = ["bash", "-c", shell_command]
    
    return shell_cmd_list, log_file