import os
import warnings
import getpass
import sys
import time
import json
from pathlib import Path
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir.endswith('/src'):
    ROOT_DIR = os.path.dirname(current_dir)
else:
    ROOT_DIR = current_dir
sys.path.insert(0, ROOT_DIR)

SKIP_FLOWCELLS_FILE = f'{ROOT_DIR}/skip_flowcells.json'

def load_skip_flowcells():
    if os.path.exists(SKIP_FLOWCELLS_FILE):
        try:
            with open(SKIP_FLOWCELLS_FILE, 'r') as f:
                data = json.load(f)
                skip_list = data.get('skip_flowcells', [])
                print(f"Loaded {len(skip_list)} skip_flowcells")
                return skip_list
        except Exception as e:
            print(f"\033[91mError loading skip_flowcells: {e}\033[0m")
            print(f"Creating new file...")
            return []
    else:
        print(f"skip_flowcells file does not exist, creating new one")
        # Create initial file with empty list
        initial_data = {
            'skip_flowcells': [
                '240918_A00926_0824_BHT35WDMXY'  # multiome
            ],
            'last_updated': time.strftime('%Y-%m-%d %H:%M:%S'),
            'created': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        try:
            with open(SKIP_FLOWCELLS_FILE, 'w') as f:
                json.dump(initial_data, f, indent=2)
            print(f"Created initial skip_flowcells file: {SKIP_FLOWCELLS_FILE}")
            return initial_data['skip_flowcells']
        except Exception as e:
            print(f"\033[91mError creating skip_flowcells file: {e}\033[0m")
            return []

def save_skip_flowcells(skip_list):
    """Save skip_flowcells list to file"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(SKIP_FLOWCELLS_FILE), exist_ok=True)
        
        data = {
            'skip_flowcells': skip_list,
            'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(SKIP_FLOWCELLS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\033[92mSkip_flowcells list updated. Total: {len(skip_list)}\033[0m")
    except Exception as e:
        print(f"\033[91mError saving skip_flowcells: {e}\033[0m")

def add_to_skip_flowcells(flowcell, reason=""):
    """Add flowcell to skip list"""
    skip_list = load_skip_flowcells()
    
    if flowcell not in skip_list:
        skip_list.append(flowcell)
        save_skip_flowcells(skip_list)
        print(f"\033[91mAdded to skip_flowcells: {flowcell} - {reason}\033[0m")
    else:
        print(f"\033[93mFlowcell {flowcell} already in skip_flowcells list\033[0m")
