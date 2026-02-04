from glob import glob
import pandas as pd 
import sys
import os
import re

FLOWCELL_RNA = sys.argv[1]
FLOWCELL_ATAC = sys.argv[2]

WORK_FOLDER = '/mnt/raid0/ofateev/projects/SC_auto'


def create_ss_wordir(workdir, flowcell_rna, flowcell_atac):
    # Получаем пути к файлам
    files_rna = glob(f'{workdir}/1.Data/FASTQ/{flowcell_rna}/*.gz')
    files_atac = glob(f'{workdir}/1.Data/FASTQ/{flowcell_atac}/*.gz')
    
    # Извлекаем названия образцов, исключая Undetermined
    samples_rna = list(set([x.split('/')[-1].split('_')[0] for x in files_rna if 'Undetermined' not in x]))
    samples_atac = list(set([x.split('/')[-1].split('_')[0] for x in files_atac if 'Undetermined' not in x]))

    # Создаем директорию для результатов
    output_dir = f'{workdir}/1.Data/MULTIOME_SS/{flowcell_rna}-{flowcell_atac}'
    os.makedirs(output_dir, exist_ok=True)

    print("RNA samples:", samples_rna)
    print("ATAC samples:", samples_atac)

    # Проверяем соответствие образцов
    if set(samples_rna) == set(samples_atac):
        samples = samples_rna
        print("Samples match between RNA and ATAC")
    else:
        print('Error: RNA and ATAC samples do not match!')
        print(f'RNA only: {set(samples_rna) - set(samples_atac)}')
        print(f'ATAC only: {set(samples_atac) - set(samples_rna)}')
        samples = None

    if samples is not None:
        columns = ['fastqs', 'sample', 'library_type']
        all_ss_path = []
        
        for sample in samples:
            ss_path = f'{output_dir}/{sample}.csv'
            
            # Проверяем существование файла
            if not os.path.exists(ss_path):
                # Создаем строки для RNA и ATAC
                rna_row = [f'{workdir}/1.Data/FASTQ/{flowcell_rna}', sample, 'Gene Expression'] 
                atac_row = [f'{workdir}/1.Data/FASTQ/{flowcell_atac}', sample, 'Chromatin Accessibility'] 
                
                # Создаем DataFrame и сохраняем
                ss_df = pd.DataFrame([rna_row, atac_row], columns=columns)
                ss_df.to_csv(ss_path, index=False)
                all_ss_path.append([sample, ss_path])
                print(f'Created sample sheet: {ss_path}')
            else:
                print(f'Sample sheet {ss_path} already exists!')
                all_ss_path.append([sample, ss_path])
        
        # Создаем общий run-sheet, если были созданы новые sample sheets
        if all_ss_path:
            run_sheet_path = f'{workdir}/1.Data/RunSheet/{flowcell_rna}-{flowcell_atac}_run-sheet.csv'
            os.makedirs(os.path.dirname(run_sheet_path), exist_ok=True)
            
            pd.DataFrame(all_ss_path, columns=['sample', 'path'])\
                .to_csv(run_sheet_path, index=False)
            print(f'Created run sheet: {run_sheet_path}')
        else:
            print('No new sample sheets were created')


# Запускаем функцию
create_ss_wordir(workdir=WORK_FOLDER,
                 flowcell_rna=FLOWCELL_RNA,
                 flowcell_atac=FLOWCELL_ATAC)