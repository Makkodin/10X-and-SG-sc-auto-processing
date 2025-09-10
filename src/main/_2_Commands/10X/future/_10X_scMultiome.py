import  os
import  sys
import  subprocess
import  pandas as pd
import  time


#FLOWCELL=sys.argv[1]

def _10X_scRNA( flowcell=   None,
                flowcell_shell  =   None,
                core    =   None,
                mem     =   None,
                fastq   =   FASTQ,
                results =   RES_10X_scRNA,
                ref_hum =   CELLRANGER_SCRNA_HUMAN,
                ref_mus =   CELLRANGER_SCRNA_MUS,
                ref_more=   None,
                tool    =   CELLRANGER):
    RunSheet    =   fastq.rsplit('/', maxsplit=1)[0] + f'/RunSheet/{flowcell_shell}_run-sheet.csv'
    df_RunSheet =   pd.read_csv(RunSheet)

    if not os.path.exists(f'{results}/{flowcell}'):
        os.makedirs(f'{results}/{flowcell}')

    print(f'Количество обрабатываемых образцов в ячейке {flowcell}: {len(df_RunSheet)}')

    processes = []
    for i in range(len(df_RunSheet)):
        sample_row_RunSheet = df_RunSheet.iloc[i]
        sample  = sample_row_RunSheet['Sample_ID']
        s_id    = sample_row_RunSheet['S_ID']
        ref     = sample_row_RunSheet['Ref']

        if ref == 'GRCh38':
            ref     = ref_hum
            postfix = 'h' 
        elif ref == 'MM10':
            ref     = ref_mus
            postfix = 'm'

        if os.path.exists == False:
            os.mkdir(f'{results}/{flowcell}')

        command = [f"{tool}/cellranger","count",
                   "--id",              f"{sample}_{postfix}",
                   "--sample",          f"{sample}",
                   "--fastqs",          f"{fastq}/{flowcell}",
                   "--transcriptome",   f"{ref}",
                   "--localcores",      f"{core}",
                   "--localmem",        f"{mem}",
                   "--create-bam",      "true",
                   ]
        process = subprocess.Popen( command,
                                    stdout=subprocess.DEVNULL, 
                                    stderr=subprocess.DEVNULL,
                                    cwd=f"{results}/{flowcell}"
                                   )
        processes.append(process)
        time.sleep(5)


    for process in processes:
        process.wait()

        if process.returncode != 0:
            print(f"Процесс завершился с ошибкой (код: {process.returncode})")
        else:
            print("Процесс успешно завершился.")
    return f"{flowcell} - over!"

#_10X_scRNA(flowcell=FLOWCELL)