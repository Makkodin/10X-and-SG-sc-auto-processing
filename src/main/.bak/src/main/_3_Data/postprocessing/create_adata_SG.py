import gzip
import anndata as ad
from scipy import io
import scipy.sparse as sp
import pandas as pd

def create_anndata_from_mtx(mtx_dir: str, output_h5ad: str = None) -> ad.AnnData:
    """
    Create AnnData object from 10x Genomics format files.
    
    :param mtx_dir: Directory containing matrix.mtx.gz, barcodes.tsv.gz, features.tsv.gz
    :param output_h5ad: Optional path to save h5ad file
    :return: AnnData object
    """
    # Read matrix
    matrix_path = f"{mtx_dir}/matrix.mtx.gz"
    with gzip.open(matrix_path, 'rt') as f:
        matrix = io.mmread(f)
    
    # Read barcodes
    barcodes_path = f"{mtx_dir}/barcodes.tsv.gz"
    with gzip.open(barcodes_path, 'rt') as f:
        barcodes = [line.strip() for line in f]
    
    # Read features
    features_path = f"{mtx_dir}/features.tsv.gz"
    with gzip.open(features_path, 'rt') as f:
        features = []
        gene_ids = []
        for line in f:
            parts = line.strip().split('\t')
            gene_ids.append(parts[0])
            features.append(parts[1] if len(parts) > 1 else parts[0])
    
    # Transpose to cells x genes and convert to CSR format
    X = matrix.T.tocsr()
    
    # Create AnnData object with proper structure
    adata = ad.AnnData(
        X=X,  # Main data matrix
        obs=pd.DataFrame(index=barcodes),  # Observations (cells)
        var=pd.DataFrame({
            'gene_ids': gene_ids,
            'feature_types': ['Gene Expression'] * len(features)
        }, index=features)  # Variables (genes)
    )
    
    # Set proper names
    adata.obs_names = barcodes
    adata.var_names = features
    
    if output_h5ad:
        adata.write(output_h5ad)
        print(f"🧬[Annotation] Saved AnnData to {'2.Results' + output_h5ad.split('/2.Results')[-1]}")
    
    return adata