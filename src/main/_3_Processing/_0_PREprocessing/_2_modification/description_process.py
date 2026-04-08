from    typing  import  Union, Optional,Tuple
from glob import glob

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

def find_image_path(sample_id: str, img_save_dir: str, flowcell: str) -> Optional[str]:
    pattern = f"{img_save_dir}/{flowcell}/{sample_id}*.tif"
    image_files = glob(pattern)
    return image_files[0] if image_files else None

def extract_vdj_type(description: str) -> Optional[str]:
    TYPE_VDJ_MAPPING        =   {'SGSC5V'   :   '5',
                                 'SGSC5TCR' :   'TR', 
                                 'SGSC5BCR' :   'IG'}
    for key, value in TYPE_VDJ_MAPPING.items():
        if key in description:
            return value
    return None

def extract_tissue(description:str):
    pairs = description.split(';')
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