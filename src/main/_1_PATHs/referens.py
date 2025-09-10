from enum import Enum

class RefsType(Enum):
    SC_TENX_RNA         = "SC_TENX_RNA"
    SC_TENX_ATAC        = "SC_TENX_ATAC"
    SC_TENX_Visium_FFPE = "SC_TENX_Visium_FFPE"
    SC_SeekGene_RNA     = "SC_SeekGene_RNA"
    SC_SeekGene_VDJ     = "SC_SeekGene_VDJ"
    SC_SeekGene_FullRNA = "SC_SeekGene_FullRNA"
    
    def _get_params(self):
        path_to_refs = {
                'SC_TENX_RNA'         :   {
                                            'GRCh38'    :   {'ref':'10x_scRNA_GRCh38'},
                                            'MM10'      :   {'ref':'10x_scRNA_MM10'},
                                            'MacMul'    :   {'ref':'10x_scRNA_MacMul'}
                                            },
                'SC_TENX_ATAC'        :   {
                                            'GRCh38'    :   {'ref':'10x_scATAC_GRCh38'},
                                            'MM10'      :   {'ref':'10x_scATAC_MM10'}
                                            },
                'SC_TENX_Visium_FFPE' :   {
                                            'GRCh38'    :   {'ref':'10X_VisiumFFPE_GRCh38',
                                                             'probe-set':'external/tenx_feature_references/targeted_panels/Visium_Human_Transcriptome_Probe_Set_v1.0_GRCh38-2020-A.csv'},
                                            'MM10'      :   {'ref':None,
                                                             'probe-set':'external/tenx_feature_references/targeted_panels/Visium_Mouse_Transcriptome_Probe_Set_v1.0_mm10-2020-A.csv'},
                                            },
                'SC_SeekGene_RNA'     :   {
                                            'GRCh38'    :   {'ref':'SG_scRNA_GRCh38'},
                                            'MM10'      :   {'ref':None},
                                            },
                'SC_SeekGene_VDJ'     :   {
                                            'GRCh38'    :   {'ref':'SC_SeekGene_VDJ_GRCh38'},
                                            'MM10'      :   {'ref':'SC_SeekGene_VDJ_MM10'},
                                            },
                'SC_SeekGene_FullRNA' :   {
                                            'GRCh38'    :   {'ref':'SG_scRNA_GRCh38'},
                                            'MM10'      :   {'ref':None},
                                            },
        }
        return path_to_refs[self.value]