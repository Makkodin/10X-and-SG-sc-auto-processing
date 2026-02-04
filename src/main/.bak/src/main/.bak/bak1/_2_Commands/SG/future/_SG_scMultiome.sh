#!/bin/bash

WORK_DIR=/mnt/raid0/ofateev/projects/SC_auto

FLOWCELL_RNA=$1
FLOWCELL_ATAC=$2

SAVE_DIR_FASTQ=${WORK_DIR}/1.Data/FASTQ
SAVE_DIR_MATRIX=${WORK_DIR}/2.Results/SG/Multiome
SAVE_PATH_MATRIX=${SAVE_DIR_MATRIX}/${FLOWCELL_RNA}-${FLOWCELL_ATAC}

# Создаем директорию для результатов если не существует
mkdir -p ${SAVE_PATH_MATRIX}

# Получаем список образцов из RNA flowcell
declare -A samples_set
for file in ${SAVE_DIR_FASTQ}/${FLOWCELL_RNA}/*.gz; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        sample_name=$(echo "$filename" | cut -d'_' -f1)
        samples_set["$sample_name"]=1
    fi
done

# Функция для поиска файлов
find_file() {
    local flowcell=$1
    local sample=$2
    local read_type=$3
    
    local files_pattern="${SAVE_DIR_FASTQ}/${flowcell}/${sample}*${read_type}*.fastq.gz"
    local files_array=($(ls $files_pattern 2>/dev/null))
    
    if [ ${#files_array[@]} -eq 0 ]; then
        echo "Ошибка: Файлы не найдены для шаблона: $files_pattern" >&2
        return 1
    elif [ ${#files_array[@]} -gt 1 ]; then
        echo "Предупреждение: Найдено несколько файлов для ${sample}_${read_type}, используем первый: ${files_array[0]}" >&2
    fi
    
    echo "${files_array[0]}"
}

# Функция для запуска обработки образца
process_sample() {
    local SAMPLE=$1
    
    echo "Обрабатываем образец: $SAMPLE"
    
    # Ищем файлы
    rna_r1_file=$(find_file $FLOWCELL_RNA $SAMPLE "R1")
    rna_r2_file=$(find_file $FLOWCELL_RNA $SAMPLE "R2")
    atac_r1_file=$(find_file $FLOWCELL_ATAC $SAMPLE "R1")
    atac_r2_file=$(find_file $FLOWCELL_ATAC $SAMPLE "R2")
    
    # Проверяем существование файлов
    if [[ ! -f "$rna_r1_file" || ! -f "$rna_r2_file" || ! -f "$atac_r1_file" || ! -f "$atac_r2_file" ]]; then
        echo "Ошибка: Не все файлы найдены для образца $SAMPLE"
        echo "RNA R1: $rna_r1_file - $(test -f "$rna_r1_file" && echo "существует" || echo "не существует")"
        echo "RNA R2: $rna_r2_file - $(test -f "$rna_r2_file" && echo "существует" || echo "не существует")"
        echo "ATAC R1: $atac_r1_file - $(test -f "$atac_r1_file" && echo "существует" || echo "не существует")"
        echo "ATAC R2: $atac_r2_file - $(test -f "$atac_r2_file" && echo "существует" || echo "не существует")"
        return 1
    fi
    
    echo "Найдены файлы:"
    echo "  RNA R1: $(basename $rna_r1_file)"
    echo "  RNA R2: $(basename $rna_r2_file)"
    echo "  ATAC R1: $(basename $atac_r1_file)"
    echo "  ATAC R2: $(basename $atac_r2_file)"
    
    # Запускаем соответствующую команду в зависимости от префикса образца
    if [[ "$SAMPLE" == m* ]]; then
        echo "Запуск для мышиного образца: $SAMPLE"
        seekarctools_py arc run \
            --rnafq1 "$rna_r1_file" \
            --rnafq2 "$rna_r2_file" \
            --atacfq1 "$atac_r1_file" \
            --atacfq2 "$atac_r2_file" \
            --samplename "$SAMPLE" \
            --outdir "${SAVE_PATH_MATRIX}/${SAMPLE}" \
            --refpath /mnt/raid0/ofateev/refs/SG_scMultiome_MM10 \
            --include-introns \
            --core 32
    else
        echo "Запуск для человеческого образца: $SAMPLE"
        seekarctools_py arc run \
            --rnafq1 "$rna_r1_file" \
            --rnafq2 "$rna_r2_file" \
            --atacfq1 "$atac_r1_file" \
            --atacfq2 "$atac_r2_file" \
            --samplename "$SAMPLE" \
            --outdir "${SAVE_PATH_MATRIX}/${SAMPLE}" \
            --refpath /mnt/raid0/ofateev/refs/SG_scMultiome_GRCh38 \
            --include-introns \
            --core 32
    fi
}

# Экспортируем функции для использования в GNU Parallel
export -f process_sample
export -f find_file
export WORK_DIR SAVE_DIR_FASTQ SAVE_DIR_MATRIX SAVE_PATH_MATRIX
export FLOWCELL_RNA FLOWCELL_ATAC

# Запускаем обработку образцов параллельно (по 4 одновременно)
printf "%s\n" "${!samples_set[@]}" | parallel -j 4 process_sample