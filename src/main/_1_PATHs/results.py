from enum import Enum

class ResultsType(Enum):
    SC_TENX_RNA         = "SC_TENX_RNA"
    SC_TENX_ATAC        = "SC_TENX_ATAC"
    SC_TENX_Visium_FFPE = "SC_TENX_Visium_FFPE"
    SC_SeekGene_RNA     = "SC_SeekGene_RNA"
    SC_SeekGene_VDJ     = "SC_SeekGene_VDJ"
    SC_SeekGene_FullRNA = "SC_SeekGene_FullRNA"

    def _get_params(self):
        CEPH    = "/mnt/cephfs8_rw/functional-genomics"
        path_to_results = {
                "SC_TENX_RNA"           :   {"fastq"    :   "1.Data/FASTQ",
                                            "local"     :   "2.Results/10X/scRNA",
                                            "ceph"      :   f"{CEPH}/10X_SC_RES/scRNA",
                                            "postfix"   :   "outs/web_summary.html",
                                            "stat"      :   "outs/metrics_summary.csv"
                                            },
                "SC_TENX_ATAC"          :   {"fastq"    :   "1.Data/FASTQ",
                                            "local"     :   "2.Results/10X/scATAC",
                                            "ceph"      :   f"{CEPH}/10X_SC_RES/scATAC",
                                            "postfix"   :   "outs/web_summary.html",
                                            "stat"      :   "outs/summary.csv"
                                            },
                "SC_TENX_Visium_FFPE"   :   {"fastq"    :   "1.Data/FASTQ",
                                            "local"     :   "2.Results/10X/visiumFFPE",
                                            "ceph"      :   f"{CEPH}/10X_SC_RES/Visium_FFPE",
                                            "postfix"   :   "outs/web_summary.html",
                                            "stat"      :   "outs/metrics_summary.csv"
                                            },
                "SC_SeekGene_RNA"       :   {"fastq"    :   "1.Data/FASTQ",
                                            "local"     :   "2.Results/SG/scRNA",
                                            "ceph"      :   f"{CEPH}/SG_SC_RES/scRNA",
                                            "postfix"   :   "_report.html",
                                            "stat"      :   "_summary.csv"
                                            },
                "SC_SeekGene_VDJ"       :   {"fastq"    :   "1.Data/FASTQ",
                                            "local"     :   "2.Results/SG/scVDJ",
                                            "ceph"      :   f"{CEPH}/SG_SC_RES/scVDJ",
                                            "postfix"   :   "outs/report.html",
                                            "stat"      :   "outs/metrics_summary.csv"
                                            },
                "SC_SeekGene_FullRNA"   :   {"fastq"    :   "1.Data/FASTQ",
                                            "local"     :   "2.Results/SG/FullLength",
                                            "ceph"      :   f"{CEPH}/SG_SC_RES/flRNA",
                                            "postfix"   :   "_report.html",
                                            "stat"      :   "_summary.csv"
                                            },
                
        }
        return path_to_results[self.value]