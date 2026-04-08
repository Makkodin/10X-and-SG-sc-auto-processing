import os
import warnings
import time
import json
import re
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"

def load_processed_flowcells(path_to_file:str):
    PROCESSED_FLOWCELLS_FILE     =   f'{path_to_file}/processed_flowcells.json'
    if os.path.exists(PROCESSED_FLOWCELLS_FILE):
        try:
            with open(PROCESSED_FLOWCELLS_FILE, 'r') as f:
                data            =   json.load(f)
                processed_list  =   data.get('processed_flowcells', [])
                print(f"✅[3.0 Processed list] Loaded {len(processed_list)} processed_flowcells")
                return processed_list
        except Exception as e:
            print(f"\033[91m⚠️[3.0 Processed list] Error loading processed_flowcells: {e}\033[0m")
            print(f"🕐[3.0 Processed list] Creating new file...")
            return []
    else:
        print(f"⚠️[3.0 Processed list] processed_flowcells file does not exist, creating new one")
        initial_data = {
            'processed_flowcells': [
            ],
            'last_updated': time.strftime('%Y-%m-%d %H:%M:%S'),
            'created': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        try:
            with open(PROCESSED_FLOWCELLS_FILE, 'w') as f:
                json.dump(initial_data, f, indent=2)
            print(f"🕐[3.0 Processed list] Created initial processed_flowcells file: {PROCESSED_FLOWCELLS_FILE}")
            return initial_data['processed_flowcells']
        except Exception as e:
            print(f"\033[91m❌[3.0 Processed list] Error creating processed_flowcells file: {e}\033[0m")
            return []

def save_processed_flowcells(path_to_file:str,
                            processed_list:list):
    PROCESSED_FLOWCELLS_FILE     =   f'{path_to_file}/processed_flowcells.json'
    try:
        os.makedirs(os.path.dirname(PROCESSED_FLOWCELLS_FILE), exist_ok=True)
        data = {
            'processed_flowcells'   :   processed_list,
            'last_updated'          :   time.strftime('%Y-%m-%d %H:%M:%S')
        }
        with open(PROCESSED_FLOWCELLS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\033[92m✅[3.0 Processed list] processed_flowcells list updated. Total: {len(processed_list)}\033[0m")
    except Exception as e:
        print(f"\033[91m❌[3.0 Processed list] Error saving processed_flowcells: {e}\033[0m")

def add_to_processed_flowcells( path_to_file:str, 
                                flowcell:str,
                                reason=""):
    processed_list  =   load_processed_flowcells(path_to_file   =   path_to_file)
    if flowcell not in processed_list:
        processed_list.append(flowcell)
        save_processed_flowcells(path_to_file   =   path_to_file,
                                 processed_list =   processed_list)
        print(f"\033[92m✅[3.0 Processed list] Added to processed_flowcells: {flowcell} - {reason}\033[0m")
    else:
        print(f"\033[93m⚠️[3.0 Processed list] Flowcell {flowcell} already in processed_flowcells list\033[0m")