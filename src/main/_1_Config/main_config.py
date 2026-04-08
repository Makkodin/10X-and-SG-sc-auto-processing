from enum import Enum
import os
current_dir     =       os.path.dirname(os.path.abspath(__file__))
path_parts      =       current_dir.split('/')
for i in range(len(path_parts)):
    if path_parts[i].startswith('src'):
        ROOT_DIR = '/'.join(path_parts[:i+1])
        break
else:
    ROOT_DIR = current_dir
WORKDIR = os.path.dirname(ROOT_DIR)

MAX_diff_date_multiome  =   10
WORK_data_type          =   'fastq'
multiome_pattern        =   r'\d{6}_.*-\d{6}_.*'

class SupportedTypes(Enum):
    SUPPORT_types   =   [
                            'SC_TENX_RNA',
                            'SC_SeekGene_FullRNA',
                            'SC_TENX_ATAC',
                            'SC_SeekGene_RNA',
                            'SC_SeekGene_VDJ',
                            'SC_TENX_Multiome_RNA',
                            'SC_TENX_Multiome_ATAC',
                            'SC_SeekGene_Multiome_RNA',
                            'SC_SeekGene_Multiome_ATAC',
                            'SC_TENX_Visium_FFPE',
                            'SC_TENX_CellPlex'
                        ]
    MULTIOME_types  =   [
                        'SC_TENX_Multiome_RNA',
                        'SC_TENX_Multiome_ATAC',
                        'SC_SeekGene_Multiome_RNA',
                        'SC_SeekGene_Multiome_ATAC'
                        ]
    CELLPLEX_types  =   [
                        'SC_TENX_CellPlex'
                        ]

class Paths(Enum):

    str_path        =   'src'
    BCL_load                =       '/mnt/cephfs3_ro/BCL/uvd*'
    BCL_save                =       '1.Data/BCL'
    FASTQ_load              =       '/mnt/cephfs*_ro/FASTQS/uvd*'
    FASTQ_save              =       '1.Data/FASTQ'
    REFS_local_dir          =       '/mnt/raid0/ofateev/refs'
    SOFT_local_dir          =       '/mnt/raid0/ofateev/soft'
    RUNsheet_save           =       '1.Data/RunSheet'
    CEPH_sheet_parse        =       '1.Data/Info/results_parsing.csv'
    CEPH_sheet_parse_raw    =       '/mnt/cephfs8_rw/functional-genomics/ofateev/Parse_df/results_parsing.csv'
    IMG_save                =       '1.Data/Image'
    SKIP_list_save          =       f'{str_path}/main/_1_Config'

class RefsName(Enum):
    organ_dict              =   {'human'    :   'GRCh38',
                                 'mouse'    :   'MM10',
                                 'mulatta'  :   'MacMul'}

class PrefixName(Enum):
    organ_dict              =   {'human'    :   'h',
                                 'mouse'    :   'm',
                                 'mulatta'  :   'mmul'}

class FilterParams(Enum):
    args    =   {
        'core'         :   16,
        'min_length'   :   60,
        'max_len1'     :   150
    }

class TypeConfig(Enum):
    SC_TENX_RNA             =   "SC_TENX_RNA"
    SC_TENX_ATAC            =   "SC_TENX_ATAC"
    SC_TENX_Visium_FFPE     =   "SC_TENX_Visium_FFPE"
    SC_SeekGene_RNA         =   "SC_SeekGene_RNA"
    SC_SeekGene_VDJ         =   "SC_SeekGene_VDJ"
    SC_SeekGene_FullRNA     =   "SC_SeekGene_FullRNA"
    SC_TENX_Multiome        =   "SC_TENX_Multiome"
    SC_SeekGene_Multiome    =   "SC_SeekGene_Multiome"
    SC_TENX_CellPlex        =   "SC_TENX_CellPlex"

    def _get_tool_version(self):
            path_to_tools = {
                    'SC_TENX_RNA'               :   'cellranger-10.0.0',
                    'SC_TENX_ATAC'              :   'cellranger-atac-2.2.0',
                    'SC_TENX_Visium_FFPE'       :   'spaceranger-3.1.2',
                    'SC_SeekGene_RNA'           :   'seeksoultools.1.2.2', # 'seeksoultools.1.3.0',
                    'SC_SeekGene_VDJ'           :   'seeksoultools.1.2.2', # 'seeksoultools.1.3.0',
                    'SC_SeekGene_FullRNA'       :   'seeksoultools.1.2.2', # 'seeksoultools.1.3.0',
                    'SC_TENX_Multiome'          :   'cellranger-arc-2.1.0',
                    'SC_SeekGene_Multiome'      :   'seekarctools_v1.0.0',
                    'SC_TENX_CellPlex'          :   'cellranger-10.0.0',
            }
            return path_to_tools[self.value]

    def _get_params(self):
            CEPH            =   "/mnt/cephfs8_rw/functional-genomics"
            str_path        =   'src'
            _paths  = {
                    'SC_TENX_RNA'           :   {
                                                'GRCh38'    :   {'ref':'10x_scRNA_GRCh38'},
                                                'MM10'      :   {'ref':'10x_scRNA_MM10'},
                                                'MacMul'    :   {'ref':'10x_scRNA_MacMul'},

                                                "fastq"     :   "1.Data/FASTQ",
                                                "cmd"       :   f"{str_path}/main/_2_Commands/10X/_10X_scRNA.py",
                                                "local"     :   "2.Results/10X/scRNA",
                                                "ceph"      :   f"{CEPH}/10X_SC_RES/scRNA",
                                                "postfix"   :   "outs/web_summary.html",
                                                "stat"      :   "outs/metrics_summary.csv"
                                                },
                    'SC_TENX_ATAC'          :   {
                                                'GRCh38'    :   {'ref':'10x_scATAC_GRCh38'},
                                                'MM10'      :   {'ref':'10x_scATAC_MM10'},
                                                
                                                "fastq"     :   "1.Data/FASTQ",
                                                "cmd"       :   f"{str_path}/main/_2_Commands/10X/_10X_scATAC.py",
                                                "local"     :   "2.Results/10X/scATAC",
                                                "ceph"      :   f"{CEPH}/10X_SC_RES/scATAC",
                                                "postfix"   :   "outs/web_summary.html",
                                                "stat"      :   "outs/summary.csv"
                                                },
                    'SC_TENX_Visium_FFPE'   :   {
                                                'GRCh38'    :   {'ref':'10x_VisiumFFPE_GRCh38',
                                                                'probe-set':'external/tenx_feature_references/targeted_panels/Visium_Human_Transcriptome_Probe_Set_v1.0_GRCh38-2020-A.csv'},
                                                'MM10'      :   {'ref':'10x_VisiumFFPE_MM10',
                                                                'probe-set':'external/tenx_feature_references/targeted_panels/Visium_Mouse_Transcriptome_Probe_Set_v1.0_mm10-2020-A.csv'},
                                                "img"       :   "1.Data/Image",
                                                "fastq"     :   "1.Data/FASTQ",
                                                "cmd"       :   f"{str_path}/main/_2_Commands/10X/_10X_VisiumFFPE.py",
                                                "local"     :   "2.Results/10X/visiumFFPE",
                                                "ceph"      :   f"{CEPH}/10X_SC_RES/Visium_FFPE",
                                                "postfix"   :   "outs/web_summary.html",
                                                "stat"      :   "outs/metrics_summary.csv"},
                    'SC_TENX_Multiome'      :   {
                                                'GRCh38'    :   {'ref':'10x_scMultiome_GRCh38'},
                                                'MM10'      :   {'ref':'10x_scMultiome_MM10'},

                                                "fastq"    :   "1.Data/FASTQ",
                                                "cmd"       :   f"{str_path}/main/_2_Commands/10X/_10X_scMultiome.py",
                                                "local"     :   "2.Results/10X/Multiome",
                                                "ceph"      :   f"{CEPH}/10X_SC_RES/scMultiome",
                                                "postfix"   :   "outs/web_summary.html",
                                                "stat"      :   "outs/summary.csv"
                                                },
                    'SC_SeekGene_RNA'       :   {
                                                'GRCh38'    :   {'ref':'SG_scRNA_GRCh38'},
                                                'MM10'      :   {'ref':'SG_scRNA_MM10'},

                                                "fastq"     :   "1.Data/FASTQ",
                                                "cmd"       :   f"{str_path}/main/_2_Commands/SG/_SG_scRNA.py",
                                                "local"     :   "2.Results/SG/scRNA",
                                                "ceph"      :   f"{CEPH}/SG_SC_RES/scRNA",
                                                "postfix"   :   "_report.html",
                                                "stat"      :   "_summary.csv"
                                                },
                    'SC_SeekGene_VDJ'       :   {
                                                'GRCh38'    :   {'ref':'SG_scRNA_GRCh38'},
                                                'MM10'      :   {'ref':'SG_scRNA_MM10'},
                                                
                                                "fastq"     :   "1.Data/FASTQ",
                                                "cmd"       :   f"{str_path}/main/_2_Commands/SG/_SG_scVDJ.py",
                                                "local"     :   "2.Results/SG/scVDJ",
                                                "ceph"      :   f"{CEPH}/SG_SC_RES/scVDJ",
                                                "postfix"   :   "outs/report.html",
                                                "stat"      :   "outs/metrics_summary.csv"
                                                },
                    'SC_SeekGene_FullRNA'   :   {
                                                'GRCh38'    :   {'ref':'SG_scRNA_GRCh38'},
                                                'MM10'      :   {'ref':'SG_scRNA_MM10'},

                                                "fastq"     :   "1.Data/FASTQ",
                                                "cmd"       :   f"{str_path}/main/_2_Commands/SG/_SG_flRNA.py",
                                                "local"     :   "2.Results/SG/FullLength",
                                                "ceph"      :   f"{CEPH}/SG_SC_RES/flRNA",
                                                "postfix"   :   "_report.html",
                                                "stat"      :   "_summary.csv"
                                                },
                    'SC_SeekGene_Multiome'  :   {
                                                'GRCh38'    :   {'ref':'SG_scMultiome_GRCh38'},
                                                'MM10'      :   {'ref':'SG_scMultiome_MM10'},

                                                "fastq"    :   "1.Data/FASTQ",
                                                "cmd"       :   f"{str_path}/main/_2_Commands/SG/_SG_scMultiome.py",
                                                "local"     :   "2.Results/SG/Multiome",
                                                "ceph"      :   f"{CEPH}/SG_SC_RES/scMultiome",
                                                "postfix"   :   "outs/*_report.html",
                                                "stat"      :   "outs/*_summary.csv"
                                                },    
                    'SC_TENX_CellPlex'      :   {
                                                'GRCh38'    :   {'ref':'10x_scRNA_GRCh38'},
                                                'MM10'      :   {'ref':'10x_scRNA_MM10'},
                                                'MacMul'    :   {'ref':'10x_scRNA_MacMul'},
                    
                                                "fastq"     :   "1.Data/FASTQ",
                                                "cmd"       :   f"{str_path}/main/_2_Commands/10X/_10X_CellPlex.py",
                                                "local"     :   "2.Results/10X/CellPlex",
                                                "ceph"      :   f"{CEPH}/10X_SC_RES/CellPlex",
                                                "postfix"   :   "outs/per_sample_outs/*/web_summary.html",
                                                "stat"      :   "outs/per_sample_outs/*/metrics_summary.csv"
                                                },
            }
            return _paths[self.value]