import os
import warnings
import time
import json
import re
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"



def load_skip_flowcells(path_to_file:str):
    SKIP_FLOWCELLS_FILE     =   f'{path_to_file}/skip_flowcells.json'
    if os.path.exists(SKIP_FLOWCELLS_FILE):
        try:
            with open(SKIP_FLOWCELLS_FILE, 'r') as f:
                data = json.load(f)
                skip_list = data.get('skip_flowcells', [])
                print(f"✅[3.0 Skip list] Loaded {len(skip_list)} skip_flowcells")
                return skip_list
        except Exception as e:
            print(f"\033[91m⚠️[3.0 Skip list] Error loading skip_flowcells: {e}\033[0m")
            print(f"🕐[3.0 Skip list] Creating new file...")
            return []
    else:
        print(f"⚠️[3.0 Skip list] skip_flowcells file does not exist, creating new one")
        # Create initial file with empty list
        initial_data = {
            'skip_flowcells': [
                '250312_A00926_0873_BHJ57LDRX5'  # multiome
            ],
            'last_updated': time.strftime('%Y-%m-%d %H:%M:%S'),
            'created': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        try:
            with open(SKIP_FLOWCELLS_FILE, 'w') as f:
                json.dump(initial_data, f, indent=2)
            print(f"🕐[3.0 Skip list] Created initial skip_flowcells file: {SKIP_FLOWCELLS_FILE}")
            return initial_data['skip_flowcells']
        except Exception as e:
            print(f"\033[91m❌[3.0 Skip list] Error creating skip_flowcells file: {e}\033[0m")
            return []

def save_skip_flowcells(path_to_file:str,
                        skip_list:list):
    SKIP_FLOWCELLS_FILE     =   f'{path_to_file}/skip_flowcells.json'
    try:
        os.makedirs(os.path.dirname(SKIP_FLOWCELLS_FILE), exist_ok=True)
        data = {
            'skip_flowcells': skip_list,
            'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        with open(SKIP_FLOWCELLS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\033[92m✅[3.0 Skip list] Skip_flowcells list updated. Total: {len(skip_list)}\033[0m")
    except Exception as e:
        print(f"\033[91m❌[3.0 Skip list] Error saving skip_flowcells: {e}\033[0m")

def add_to_skip_flowcells(path_to_file:str, 
                        flowcell:str,
                        reason=""):
    skip_list = load_skip_flowcells(path_to_file   =   path_to_file)
    if flowcell not in skip_list:
        skip_list.append(flowcell)
        save_skip_flowcells(path_to_file    =   path_to_file,
                            skip_list       =   skip_list)
        print(f"\033[91m✅[3.0 Skip list] Added to skip_flowcells: {flowcell} - {reason}\033[0m")
    else:
        print(f"\033[93m⚠️[3.0 Skip list] Flowcell {flowcell} already in skip_flowcells list\033[0m")