from    typing                                      import  Optional, Dict, Any, List, Tuple
import sys
import os
import importlib.util

def choose_resources(sample_count: int) -> Tuple[int, int]:
    num_cores   =   100
    memory      =   1000

    MAX_CORES_PER_SAMPLE    =   30
    MAX_MEMOR_PER_SAMPLE    =   300

    cores_per_sample  =   int(num_cores / sample_count)
    memor_per_sample  =   int(memory / sample_count)

    cores_per_sample    =   min([cores_per_sample, MAX_CORES_PER_SAMPLE])
    memor_per_sample    =   min([memor_per_sample, MAX_MEMOR_PER_SAMPLE])
    
    return cores_per_sample, memor_per_sample 

def dynamic_import(script_path: str) -> Any:
    module_name = os.path.basename(script_path).replace(".py", "")
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if not spec or not spec.loader:
        raise ImportError(f"Failed to load module from {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module