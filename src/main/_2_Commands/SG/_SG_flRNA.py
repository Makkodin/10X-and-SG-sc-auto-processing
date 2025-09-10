from    glob import glob

def _flRNA( flowcell:str,
            sample:str,
            ref_dir:str,
            result_dir:str,
            data_dir:str,
            core:int,
            toolpath:str,
            chemistry:str = 'DD-Q',
            more_arg:list = [],
           ):
        # Find all fastq.gz files for sample
        # Example: 
        # sample_S1_L001_R1_001.fastq.gz
        # sample_S1_L001_R2_001.fastq.gz 
        fastqs      =   sorted(glob(f"{data_dir}/{flowcell}/{sample}*gz"))

        # Create cmd list of fastq.gz files (by R1, R2)
        # Example: 
        # --fq1 sample_S1_L001_R1_001.fastq.gz
        # --fq2 sample_S1_L001_R2_001.fastq.gz 
        fastqs_cmd  = []
        for f_fq in fastqs:
            if '_R1_' in f_fq:
                fastqs_cmd.extend(['--fq1', f'{f_fq}'])
            elif '_R2_' in f_fq:
                fastqs_cmd.extend(['--fq2', f'{f_fq}'])
        
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
        command     =   [f"{toolpath}/seeksoultools","fast","run",
                         "--samplename",      f"{sample}_{postfix}",
                         "--outdir",          f"{result_dir}/{flowcell}",
                         "--genomeDir",       f"{ref_dir}/star",
                         "--gtf",             f"{ref_dir}/genes/genes.gtf",
                         "--chemistry",       f"{chemistry}",
                         "--core",            f"{core}",
                         "--include-introns"
                        ] + more_arg + fastqs_cmd
        
        # LOG file with full output
        log_file    =   f"{result_dir}/{flowcell}/{sample}_{postfix}_output.log"

        return command, log_file