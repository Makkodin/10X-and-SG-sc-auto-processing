import os
import subprocess
from typing import Optional


def load_bcl(
        flowcell    :   str,
        user        :   str,
        save_bcl    :   str,
        load_bcl    :   str,
        password    :   str) -> Optional[str]:
    bcl_flowcell_path = f"{load_bcl}/{flowcell}"
    access = []
    if not os.path.exists(bcl_flowcell_path):
        bcl_flowcell_path = f"{user}@cs11:{load_bcl}/{flowcell}"
        access = ["sshpass", "-p", f"{password}"]
    os.makedirs(save_bcl, exist_ok=True)
    load_cmd = access + [
        "rsync", "-r", "--ignore-existing", "--progress",
        bcl_flowcell_path, f"{save_bcl}/"]

    try:
        result = subprocess.run(
            load_cmd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        target_path = f"{save_bcl}/{flowcell}"
        if os.path.exists(target_path):
            print(f"✅[3.0.1 Load BCL] BCL loaded to {target_path}")
            return target_path
        else:
            print(f"❌[3.0.1 Load BCL] Path not exist: {target_path}")
            return None
            
    except Exception as e:
        print(f"❌[3.0.1 Load BCL] Ошибка для {flowcell}: {str(e)}")
        return None