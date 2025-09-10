import warnings
warnings.filterwarnings("ignore")
from    tabulate import tabulate
from    glob    import  glob
import  pandas  as      pd

from    typing  import  Optional,Tuple
def extract_slide_info(img_path: Optional[str]) -> Optional[str]:
    if not img_path:
        return None
    try:
        return img_path.split('/')[-1].replace('.tif', '').split('_')[1]
    except (IndexError, AttributeError):
        return None

def extract_area_info(img_path: Optional[str]) -> Optional[str]:
    if not img_path:
        return None
    try:
        return img_path.split('/')[-1].replace('.tif', '').split('_')[2]
    except (IndexError, AttributeError):
        return None

def find_image_path(sample_id: str, img_save_dir: str) -> Optional[str]:
    pattern = f"{img_save_dir}/{sample_id}*.tif"
    image_files = glob.glob(pattern)
    return image_files[0] if image_files else None

def extract_vdj_type(description: str) -> Optional[str]:
    TYPE_VDJ_MAPPING        =   {'SGSC5V'   :   '5',
                                 'SGSC5TCR' :   'TR', 
                                 'SGSC5BCR' :   'IG'}
    for key, value in TYPE_VDJ_MAPPING.items():
        if key in description:
            return value
    return None

def extract_tissue(row_string):
    pairs = row_string.split(';')
    data_dict = {}
    for pair in pairs:
        if '=' in pair:
            key, value = pair.split('=', 1)
            data_dict[key.strip()] = value.strip()
    if 'tissue' in data_dict:
        x   =    data_dict['tissue']
    elif 'biotype' in data_dict:
        x   =   data_dict['biotype']
    else:
        return None
    
    if 'nuclei' in x:
        x   =   'PBMC;nuclei'
    elif x == 'blood':
        x   =   'PBMC;cells'
    elif 'PBMC' in x:
        x   =   'PBMC;cells'
    
    return x

def create_run_sheet(fastq_save:str,
                     infosheet:pd.DataFrame,
                     runsheet_save:str,
                     img_save:str,
                     flowcell:str,
                     supported_type:list
                     )-> Tuple[Optional[str], Optional[pd.DataFrame]]:
    """
    Create Sheet with Flowcell info (SeqType, Organism...).

    :param fastq_save       : Path to save FASTQ flowcell.
    :param infosheet        : Path to table with parse ceph info.
    :param img_save         : Path to image stored location (for VisiumFFPE).
    :param runsheet_save    : Path to save FLOWCELL-run_sheet.csv.

    :return                 : Path to save FLOWCELL-run_sheet.csv and run_sheet.csv in DF format
    """
    SEQ_TYPE_VISIUM         =   'SC_TENX_Visium_FFPE'
    SEQ_TYPE_SEEKGENE       =   'SC_SeekGene_VDJ'

    organ_dict              =   {'human'    :   'GRCh38',
                                 'mouse'    :   'MM10',
                                 'mulatta'  :   'MacMul'}
    CODE_TYPE_VDJ_MAPPING   =   {'5'        :   'SC_SeekGene_RNA',
                                 'TR'       :   'SC_SeekGene_VDJ', 
                                 'IG'       :   'SC_SeekGene_VDJ'}
    _path_to_process        =   {'SC_TENX_RNA'           :   'src/main/_2_Commands/10X/_10X_scRNA.py',
                                 'SC_TENX_ATAC'          :   'src/main/_2_Commands/10X/_10X_scATAC.py',
                                 'SC_TENX_Visium_FFPE'   :   'src/main/_2_Commands/10X/_10X_VisiumFFPE.py',
                                 'SC_SeekGene_RNA'       :   'src/main/_2_Commands/SG/_SG_scRNA.py',
                                 'SC_SeekGene_VDJ'       :   'src/main/_2_Commands/SG/_SG_scVDJ.py',
                                 'SC_SeekGene_FullRNA'   :   'src/main/_2_Commands/SG/_SG_flRNA.py'}

    # SKIP SEQtype
    skip_types  =   ['SC_TENX_Visium_FF', 'SC_TENX_Multiome_RNA','SC_TENX_Multiome_ATAC']

    flowcell_parse_df           =   infosheet
    flowcell_parse_df           =   flowcell_parse_df.drop(columns=['Sample_NAME']).drop_duplicates()

    infosheet_support           =   infosheet[~infosheet['Desct_TYPE'].isin(skip_types)]
    samples_infosheet_support   =   infosheet_support['Sample_ID'].unique().tolist()

    samples =   []
    for sample_infosheet_support in samples_infosheet_support:
        samples.extend(list(set([x.split('/')[-1].split('_S')[0] for x in glob(f"{fastq_save}/{sample_infosheet_support}_S*.gz")])))

    # Check number of samples and infosheet content
    if len(samples) == len(flowcell_parse_df):
        samples_parse_df                =   flowcell_parse_df[flowcell_parse_df['Sample_ID'].isin(samples)]
        samples_parse_df                =   samples_parse_df[['Flowcell',
                                                              'Sample_ID',
                                                              'Descr_ORG',
                                                              'Check_ORG',
                                                              'Desct_TYPE',
                                                              'Description']].drop_duplicates()
        
        # Chose Reference
        samples_parse_df['Descr_ORG']   =   samples_parse_df['Descr_ORG'].fillna('No')
        samples_parse_df['Tissue']      =   samples_parse_df['Description'].apply(lambda x: extract_tissue(x))
        if 'No'  not in samples_parse_df['Descr_ORG'].to_list():
            ref_col     =   'Descr_ORG'
        else:
            ref_col     =   'Check_ORG'
        samples_parse_df                =   samples_parse_df.rename(columns={   'Desct_TYPE'   :   'SEQtype',
                                                                                ref_col        :   'Reference'})  
        samples_parse_df['Organism_name']         =   samples_parse_df['Reference']
        samples_parse_df['Reference']   =   samples_parse_df['Reference'].replace(organ_dict)

        seq_types   =   samples_parse_df['SEQtype'].tolist()

        if SEQ_TYPE_VISIUM in seq_types:
            img_save_dir                =   img_save
            samples_parse_df['Img']     =   samples_parse_df['Sample_ID'].apply(lambda x: find_image_path(x, img_save_dir))
            samples_parse_df['Slide']   =   samples_parse_df['Img'].apply(extract_slide_info)
            samples_parse_df['Area']    =   samples_parse_df['Img'].apply(extract_area_info)

        elif SEQ_TYPE_SEEKGENE in seq_types:
            samples_parse_df['VDJ_type']    =   samples_parse_df['Description'].apply(extract_vdj_type)
            samples_parse_df['SEQtype']     =   samples_parse_df['VDJ_type'].replace(CODE_TYPE_VDJ_MAPPING)

        samples_parse_df['Cmd']     =   samples_parse_df['SEQtype'].replace(_path_to_process)
        samples_parse_df            =   samples_parse_df.reset_index(drop='index')
        samples_parse_df            =   samples_parse_df[~samples_parse_df['SEQtype'].isin(skip_types)]

        # Create SampleInfoSheet and path to him
        samples_parse_df.to_csv(f"{runsheet_save}/{flowcell}-run_sheet.csv", index=False)
        sample_sheet_info_path      =  f"{runsheet_save}/{flowcell}-run_sheet.csv" 
        print(f"✅[Create sheet] Flowcell info sheet generated: \033[1m{'1.Data' + sample_sheet_info_path.split('/1.Data', 1)[-1]}\033[0m")
        print(f"✅[Create sheet] Info sheet content:")

        print(tabulate(samples_parse_df[['Sample_ID','Flowcell', 'Reference', 
                                         'SEQtype', 'Tissue']], 
                       headers      =   ['Sample_ID','Flowcell', 'Reference', 
                                         'SEQtype', 'Tissue'], 
                       tablefmt     =   'psql'))
    
    else:
        print(f"❌[Create sheet] In flowcell {len(flowcell_parse_df)} samples, loaded {len(samples)}")
        sample_sheet_info_path      =   None
        samples_parse_df            =   None
    return sample_sheet_info_path, samples_parse_df
        
        
    


   


