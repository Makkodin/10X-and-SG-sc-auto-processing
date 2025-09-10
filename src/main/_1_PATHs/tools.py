from enum import Enum

class ToolsType(Enum):
    SC_TENX_RNA         = "SC_TENX_RNA"
    SC_TENX_ATAC        = "SC_TENX_ATAC"
    SC_TENX_Visium_FFPE = "SC_TENX_Visium_FFPE"
    SC_SeekGene_RNA     = "SC_SeekGene_RNA"
    SC_SeekGene_VDJ     = "SC_SeekGene_VDJ"
    SC_SeekGene_FullRNA = "SC_SeekGene_FullRNA"

    def _get_params(self):
        path_to_tools = {
                'SC_TENX_RNA'         :   'cellranger-9.0.1',
                'SC_TENX_ATAC'        :   'cellranger-atac-2.2.0',
                'SC_TENX_Visium_FFPE' :   'spaceranger-3.1.2',
                #'SC_SeekGene_RNA'     :   'seeksoultools.1.3.0',
                #'SC_SeekGene_VDJ'     :   'seeksoultools.1.3.0',
                #'SC_SeekGene_FullRNA' :   'seeksoultools.1.3.0',
                'SC_SeekGene_RNA'     :   'seeksoultools.1.2.2',
                'SC_SeekGene_VDJ'     :   'seeksoultools.1.2.2',
                'SC_SeekGene_FullRNA' :   'seeksoultools.1.2.2',
        }
        return path_to_tools[self.value]
    


