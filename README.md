# 10X and SG SingleCell pipeline

## Начало работы

### Типы данных для обработки (29/12/2025)

-  **10X scRNA**
-  **10X scATAC**
-  **10X VisiumFFPE**
-  **10X Multiome**
-  **SeekGene scRNA**
-  **SeekGene scVDJ**
-  **SeekGene Multiome**

### Предустановка

1.  Клонирование GIT репозитория

        git clone https://gitlab.cspfmba.ru/functionalgenomics/10x-and-sg-singlecell-pipeline.git

2.  Установка окружения (Pipfile)

        cd 10x-and-sg-singlecell-pipeline
        conda env create -f SC_process_v3.yml
        conda activate SC_processing
        pip install -e .

3.  Установка инструментов (На серверах cs11 и cs12 уже установлено)

        cellranger      v9.0.1  (https://www.10xgenomics.com/support/software/cell-ranger/latest)
        cellranger-atac v2.2.0  (https://www.10xgenomics.com/support/software/cell-ranger-atac/latest)
        cellranger-arc  v2.1.0  (https://www.10xgenomics.com/support/software/cell-ranger-arc/latest)
        spaceranger     v3.1.2  (https://www.10xgenomics.com/support/software/space-ranger/latest)
        SeekSoulTools   v1.2.2  (http://seeksoul.seekgene.com/en/v1.2.2/index.html)
        SeekArc         v1.0.0  (https://seeksoul.online/cloudplatform-doc/zh/document/SeekARC%20Document/1_%E6%A6%82%E8%BF%B0.html)

4.  Загрузка референсов (можно найти по пути или скачать из интернета)

        /mnt/cephfs8_rw/functional-genomics/ofateev/refs

### Проверка и настройка конфига

        Расположение референсов_____: src/_1_PATHs/referens.py
        Расположение инструментов___: src/_1_PATHs/tools.py

### Запуск

1. Пример запуска команды: **sc-processing** (после запуска скачает таблицу и запросит username и password), команда будет гоняться без перерыва, если нет ячеек для обработки - уходит в спячку на 1 час, потом проверяет. 
Также можно запустить обработку определенного типа ячейки **sc-processing** **FLOWCELL**, после чего обработка завершится

2. Для определения организма требуется файл **1.Data/Info/results_parsing.csv**, он обновляется каждые 4 часа (~12:00PM) автоматически, для подгрузки новых ячеек


### Пример запуска
```
=====================================================
🕐[Processing] Processing specified flowcell: 241216_A00923_0850_BHJ5LGDRX2
🕒[3.1.1 Load flowcell] Starting 'fastq' loading for 1 flowcells
🕒[3.1.1 Load SampleSheet] Loading SampleSheet for 1 flowcells
✅[3.0.1 Load SampleSheet] SampleSheet loaded for 241216_A00923_0850_BHJ5LGDRX2
🕒[3.1.1 Load FASTQ Parallel] Parallel loading of 2 samples
✅[3.0.1 Load FASTQ] Files already exist for 241216_A00923_0850_BHJ5LGDRX2:770934980000_770931790000_770931980000_770930380000_1 (4 files)
✅[3.0.1 Load FASTQ] Files already exist for 241216_A00923_0850_BHJ5LGDRX2:770934980000_770931790000_770931980000_770930380000_2 (4 files)
✅[3.1.1 Load FASTQ 1/2] Success: 241216_A00923_0850_BHJ5LGDRX2:770934980000_770931790000_770931980000_770930380000_1
✅[3.1.1 Load FASTQ 2/2] Success: 241216_A00923_0850_BHJ5LGDRX2:770934980000_770931790000_770931980000_770930380000_2
✅[3.1.1 Load FASTQ Parallel] Total: 2/2 samples loaded successfully
✅[3.1.1 Load flowcell] Loading completed. Success: 2/2
+-------------------------------------------------------+-------------------------------+-------------+-----------------+------------+---------+-------------+--------------+
|                                             Sample_ID | Flowcell                      | Reference   | SEQtype         | Tissue     | Load    | Processed   | Annotation   |
|                                                       |                               |             |                 |            | Fastq   | status      | status       |
|-------------------------------------------------------+-------------------------------+-------------+-----------------+------------+---------+-------------+--------------|
| 770934980000_770931790000_770931980000_770930380000_1 | 241216_A00923_0850_BHJ5LGDRX2 | human       | SC_SeekGene_VDJ | PBMC;cells | ✅      | ❌          | ❌           |
| 770934980000_770931790000_770931980000_770930380000_2 | 241216_A00923_0850_BHJ5LGDRX2 | human       | SC_SeekGene_VDJ | PBMC;cells | ✅      | ❌          | ❌           |
+-------------------------------------------------------+-------------------------------+-------------+-----------------+------------+---------+-------------+--------------+
┌───────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│              3.1.2 Flowcell processing info                                                                   │
├───────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ ℹ️ Start to processed flowcells_:   ['241216_A00923_0850_BHJ5LGDRX2']
│ ℹ️ Sample number________________:   2
│ ℹ️ Organism reference___________:   ['human']
│ ℹ️ Type seq_____________________:   ['SC_SeekGene_VDJ']
│ ⚙️ Total resources allocated____:   100 cores, 1000 GB RAM
│ ⚙️ Resources per sample_________:   50 cores, 500 GB RAM
└───────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
✅[3.1.2 Processing] Results already exist for 770934980000_770931790000_770931980000_770930380000_1.
✅[3.1.2 Processing] Results already exist for 770934980000_770931790000_770931980000_770930380000_2.
🔄[3.1.2 Processing] Updating sample status...
ℹ️[3.1.2 Processing] Updated 'Processed status' to True for 770934980000_770931790000_770931980000_770930380000_1
ℹ️[3.1.2 Processing] Added 'Annotation status' = False for 770934980000_770931790000_770931980000_770930380000_1
ℹ️[3.1.2 Processing] Updated 'Processed status' to True for 770934980000_770931790000_770931980000_770930380000_2
ℹ️[3.1.2 Processing] Added 'Annotation status' = False for 770934980000_770931790000_770931980000_770930380000_2
🧬[3.1.2 Processing] Checking samples for annotation...
✅[3.1.2 Processing] All successful samples: ['770934980000_770931790000_770931980000_770930380000_1', '770934980000_770931790000_770931980000_770930380000_2']
🧬[3.1.2 Annotation] Sample 770934980000_770931790000_770931980000_770930380000_1 added for annotation (SeqType: SC_SeekGene_VDJ, VDJ type: 5)
🧬[3.1.2 Annotation] Starting annotation for 1 samples...
✅[3.1.2 Annotation] Successfully annotated 770934980000_770931790000_770931980000_770930380000_1
🧬[3.1.2 Annotation] Completed annotation for 1 samples
+-------------------------------------------------------+-------------------------------+-------------+-----------------+------------+---------+-------------+--------------+
|                                             Sample_ID | Flowcell                      | Reference   | SEQtype         | Tissue     | Load    | Processed   | Annotation   |
|                                                       |                               |             |                 |            | Fastq   | status      | status       |
|-------------------------------------------------------+-------------------------------+-------------+-----------------+------------+---------+-------------+--------------|
| 770934980000_770931790000_770931980000_770930380000_1 | 241216_A00923_0850_BHJ5LGDRX2 | human       | SC_SeekGene_VDJ | PBMC;cells | ✅      | ✅          | ✅           |
| 770934980000_770931790000_770931980000_770930380000_2 | 241216_A00923_0850_BHJ5LGDRX2 | human       | SC_SeekGene_VDJ | PBMC;cells | ✅      | ✅          | ❌           |
+-------------------------------------------------------+-------------------------------+-------------+-----------------+------------+---------+-------------+--------------+
🕒[3.1.3 Create Summary Dir] Collecting statistics...
✅[3.2.r Statistic summary] Statistics collected and formatted for sample: 770934980000_770931790000_770931980000_770930380000_1
✅[3.2.r Statistic summary] Statistics collected and formatted for sample: 770934980000_770931790000_770931980000_770930380000_2
✅[3.1.3 Create Summary Dir] Statistics collect: /mnt/raid0/ofateev/projects/SC_auto/2.Results/SG/scVDJ/241216_A00923_0850_BHJ5LGDRX2/241216_A00923_0850_BHJ5LGDRX2-sum/241216_A00923_0850_BHJ5LGDRX2_stat.csv
✅[3.1.3 Create Summary Dir] Copied plot 770934980000_770931790000_770931980000_770930380000_1_filtered_feature_bc_matrix_annotated_scParadise_Human_PBMC.png
✅[3.1.3 Create Summary Dir] Copied report for 770934980000_770931790000_770931980000_770930380000_1
✅[3.1.3 Create Summary Dir] Copied report for 770934980000_770931790000_770931980000_770930380000_2
✅[3.1.3 Create Summary Dir] Moved to sum dir: 2/2 reports
✅[3.1.3 Create Summary Dir] Moved to sum dir: 1 plots
/mnt/raid0/ofateev/projects/SC_auto/src/main/_1_Config/email_config.ini
🕒[3.2.r Email report] Creating single archive to check size: 241216_A00923_0850_BHJ5LGDRX2_reports.zip
📊[3.2.r Email report] Total archive size: 9.6 MB (limit: 25 MB)
✅[3.2.r Email report] Single archive is within size limit
📦[3.2.r Email report] Found 1 archive(s) to send
📦[3.2.r Email report] Processing archive 1/1: 241216_A00923_0850_BHJ5LGDRX2_reports.zip (9.6 MB)
🕒[3.2.r Email report] Creating email body...
🕒[3.2.r Email report] Sending email 1/1...
🕒[3.2.r Email report] Trying SMTP...
✅[3.2.r Email report] Email sent via SMTP (fallback)
✅[3.2.r Email report] Successfully sent archive 1/1
🧹[3.2.r Email report] Cleaned up temporary archive: 2.Results/SG/scVDJ/241216_A00923_0850_BHJ5LGDRX2/241216_A00923_0850_BHJ5LGDRX2-sum/241216_A00923_0850_BHJ5LGDRX2_reports.zip
✅[3.2.r Email report] All 1 email(s) sent successfully!
✅[3.2 Move and remove] Found 1 HTML files for 241216_A00923_0850_BHJ5LGDRX2:770934980000_770931790000_770931980000_770930380000_1
✅[3.2 Move and remove] Found 1 stat files for 241216_A00923_0850_BHJ5LGDRX2:770934980000_770931790000_770931980000_770930380000_1
✅[3.2 Move and remove] Found 1 HTML files for 241216_A00923_0850_BHJ5LGDRX2:770934980000_770931790000_770931980000_770930380000_2
✅[3.2 Move and remove] Found 1 stat files for 241216_A00923_0850_BHJ5LGDRX2:770934980000_770931790000_770931980000_770930380000_2
✅[3.2 Move and remove] Found 2 HTML files in summary directory
✅[3.2 Move and remove] Directory /mnt/cephfs8_rw/functional-genomics/SG_SC_RES/scVDJ/seeksoultools.1.2.2/241216_A00923_0850_BHJ5LGDRX2 created/verified
🕒[3.2 Move and remove] Starting rsync for flowcell 241216_A00923_0850_BHJ5LGDRX2...
✅[3.2 Move and remove] Rsync completed successfully for flowcell 241216_A00923_0850_BHJ5LGDRX2
✅[3.2 Move and remove] All samples copied successfully
🕒[3.2 Move and remove] Removed local results: /mnt/raid0/ofateev/projects/SC_auto/2.Results/SG/scVDJ/241216_A00923_0850_BHJ5LGDRX2
✅[3.2 Move and remove] Removed data directory: /mnt/raid0/ofateev/projects/SC_auto/1.Data/FASTQ/241216_A00923_0850_BHJ5LGDRX2
✅[3.2 Move and remove] All operations completed successfully
✅[3.2 Move and remove] Saved processing info to /mnt/cephfs8_rw/functional-genomics/SG_SC_RES/scVDJ/seeksoultools.1.2.2/241216_A00923_0850_BHJ5LGDRX2/flowcell_sample_processed_count-1.json
```