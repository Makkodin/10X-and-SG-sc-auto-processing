WORK_DIR=/mnt/raid0/ofateev/projects/SC_auto

FLOWCELL_RNA=$1
FLOWCELL_ATAC=$2

SAVE_DIR_FASTQ=${WORK_DIR}/1.Data/FASTQ
SAVE_DIR_MATRIX=${WORK_DIR}/2.Results/10X/Multiome
SAVE_PATH_MATRIX=${SAVE_DIR_MATRIX}/${FLOWCELL_RNA}-${FLOWCELL_ATAC}

SAMPLESHEET=${WORK_DIR}/1.Data/RunSheet/${FLOWCELL_RNA}-${FLOWCELL_ATAC}_run-sheet.csv

#--------------------------------------------------------------------------------------------------
# ЗАПУСК cellranger count

# Читаем SampleSheet
# Сортируем и унифицируем 
# Запускаем попарное параллельное вычисление с разделителем запятой 
# --include-introns  по умолчанию - на версии 6 выключен, а на 7 включен (если сравнивать с ячейками сделанными Абусаидом)

# Загружаем из ЦЕФА fastq файлы
#function load_from_ceph () {
#    python $WORK_DIR/scripts/OTHER/load_from_ceph.py $FLOWCELL_RNA  $WORK_DIR; 
#    python $WORK_DIR/scripts/OTHER/load_from_ceph.py $FLOWCELL_ATAC $WORK_DIR
#}

# Создание SS
function create_ss () {
    python ${WORK_DIR}/src/main/_2_Commands/10X/future/create_ss_Multiome.py $FLOWCELL_RNA $FLOWCELL_ATAC
}

# Главный скрипт
function run_count_arc () {

    echo START work FLOWCELL 
    mkdir -p ${SAVE_PATH_MATRIX}
    cd ${SAVE_PATH_MATRIX}
    cat ${SAMPLESHEET} | sort -u | 
    parallel --colsep ',' -j 8 \
    "if [[ {1} == m* ]]; then
        /mnt/raid0/ofateev/soft/cellranger-arc-2.1.0/cellranger-arc count \
            --id={1} \
            --libraries={2} \
            --create-bam true \
            --reference=/mnt/raid0/ofateev/refs/10X_scMultiome_MM10 \
            --localcores=10 \
            --localmem=100
    else
        /mnt/raid0/ofateev/soft/cellranger-arc-2.1.0/cellranger-arc count \
            --id={1} \
            --libraries={2} \
            --create-bam true \
            --reference=/mnt/raid0/ofateev/refs/10x_scRNA_GRCh38 \
            --localcores=10 \
            --localmem=100
    fi"
}

echo _______________________________________________
echo CELLRANGER COUNT start :

DATE=$(date)
echo "Start : $DATE"

#load_from_ceph
create_ss
run_count_arc
#move_2_exchange

DATE=$(date)
echo "STOP : $DATE"



