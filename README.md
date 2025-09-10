# 10X and SG SingleCell pipeline

## Начало работы

### Типы данных для обработки (20/08/2025)

-  **10X scRNA**
-  **10X scATAC**
-  **10X VisiumFFPE**
-  **SeekGene scRNA**
-  **SeekGene scVDJ**

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
        spaceranger     v3.1.2  (https://www.10xgenomics.com/support/software/space-ranger/latest)
        SeekSoulTools   v1.3.0  (http://seeksoul.seekgene.com/en/v1.3.0/index.html)

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
⚙️ [Authorization] Enter username: ofateev
⚙️ [Authorization] Enter password:
✅[Login] Using username: ofateev
✅[Login] Using password: ***************
⚙️ [Authorization] Enter user mail: ofateev@cspfmba.ru
⚙️ [Authorization] Enter mail password:
✅[Login] Using mail username: ofateev
✅[Login] Using mail password: ***************
=====================================================
✅[Load sheet info] Rsync 1.Data/Info/results_parsing.csv complete!
Loaded 4 skip_flowcells
=====================================================
Processing specified flowcell: 241118_VH00195_177_AAAJYJNHV
🕒[Load data] Start to load/preprocessing flowcell 241118_VH00195_177_AAAJYJNHV
✅[Load FASTQ] Rsync 1.Data/FASTQ/241118_VH00195_177_AAAJYJNHV complete!
✅[Load FASTQ] Rsync 1.Data/FASTQ/241118_VH00195_177_AAAJYJNHV/2024_11_18_10X_SC_RNA_Pool0088.csv complete!
✅[Create sheet] Flowcell info sheet generated: 1.Data/RunSheet/241118_VH00195_177_AAAJYJNHV-run_sheet.csv
✅[Create sheet] Info sheet content:
+----+--------------+------------------------------+-------------+-------------+------------+
|    |    Sample_ID | Flowcell                     | Reference   | SEQtype     | Tissue     |
|----+--------------+------------------------------+-------------+-------------+------------|
|  0 | 962210414501 | 241118_VH00195_177_AAAJYJNHV | MM10        | SC_TENX_RNA | PBMC;cells |
|  1 | 962210514501 | 241118_VH00195_177_AAAJYJNHV | MM10        | SC_TENX_RNA | PBMC;cells |
|  2 | 962210714501 | 241118_VH00195_177_AAAJYJNHV | MM10        | SC_TENX_RNA | PBMC;cells |
|  3 | 962210814501 | 241118_VH00195_177_AAAJYJNHV | MM10        | SC_TENX_RNA | PBMC;cells |
|  4 | 962211314501 | 241118_VH00195_177_AAAJYJNHV | MM10        | SC_TENX_RNA | PBMC;cells |
|  5 | 962211514501 | 241118_VH00195_177_AAAJYJNHV | MM10        | SC_TENX_RNA | PBMC;cells |
+----+--------------+------------------------------+-------------+-------------+------------+
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│              Flowcell processing info                                                          │
├────────────────────────────────────────────────────────────────────────────────────────────────┤
│ ℹ️ Start to processed flowcells_:   ['241118_VH00195_177_AAAJYJNHV']
│ ℹ️ Sample number________________:   6
│ ℹ️ Organism reference___________:   ['MM10']
│ ℹ️ Type seq_____________________:   ['SC_TENX_RNA']
│ ⚙️ Total resources allocated____:   120 cores, 1200 GB RAM
│ ⚙️ Resources per sample_________:   20 cores, 200 GB RAM
└────────────────────────────────────────────────────────────────────────────────────────────────┘
✅[Processing] Results already exist for 962210414501.
✅[Processing] Results already exist for 962210514501.
✅[Processing] Results already exist for 962210714501.
✅[Processing] Results already exist for 962210814501.
✅[Processing] Results already exist for 962211314501.
✅[Processing] Results already exist for 962211514501.
✅[Processing] ['241118_VH00195_177_AAAJYJNHV'] - processing complete!
-----------------------------------------------------
🕒[Check & move] Collecting statistics for SC_TENX_RNA...
✅ Statistics summary saved to: 2.Results/10X/scRNA/241118_VH00195_177_AAAJYJNHV/241118_VH00195_177_AAAJYJNHV-sum/241118_VH00195_177_AAAJYJNHV_statistics_summary.csv
📊 Processed 6 samples successfully, 0 with errors
📋 Total samples: 6
✅[Check & move] Move to sum dir SC_TENX_RNA: 6/6 reports
✅[Check & move] Move to sum dir SC_TENX_RNA: 0 plots
✅[Check & move] Move SampleSheet to sum dir: 241118_VH00195_177_AAAJYJNHV-run_sheet.csv
🕒 Creating archive 241118_VH00195_177_AAAJYJNHV_reports.zip...
✅ Archive created: /mnt/raid0/ofateev/projects/SC_auto/2.Results/10X/scRNA/241118_VH00195_177_AAAJYJNHV/241118_VH00195_177_AAAJYJNHV-sum/241118_VH00195_177_AAAJYJNHV_reports.zip
🕒 Creating email body...
🕒 Sending email to recipients: ['ofateev@cspfmba.ru', 'KDeynichenko@cspfmba.ru', 'AShaimardanov@cspfmba.ru']...
❌ Error creating SOAP client: 401 Client Error: Unauthorized for url: https://mail2.cspfmba.ru:444/EWS/Services.wsdl
⚠️ SOAP failed, trying SMTP...
✅ Email sent via SMTP (fallback)
🕒[Check & move] Start move results to ceph: /mnt/cephfs8_rw/functional-genomics/10X_SC_RES/scRNA/cellranger-9.0.1
✅[Check & move] Move to /mnt/cephfs8_rw/functional-genomics/10X_SC_RES/scRNA/cellranger-9.0.1 ready!
❌[Check & move] Transfer 15602/15554 files. Not all files transferred.
✅[Check & move] All FASTQ files and temporary files removed!
Successfully processed flowcell: 241118_VH00195_177_AAAJYJNHV
=====================================================
```