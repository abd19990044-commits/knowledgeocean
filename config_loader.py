# -*- coding: utf-8 -*-
"""
Local Configuration File Loader for Knowledge Ocean.
Reads key=value settings from config.txt in the project root directory.
Enables end users to easily configure:
  - APP_PASSWORD = 123
  - UNPAYWALL_EMAIL = researcher@example.com
  - ELSEVIER_API_KEY = your_elsevier_key_here
"""

import os
import logging

log = logging.getLogger("AcademicAPI")

DEFAULT_CONFIG_FILENAME = "config.txt"

def load_local_config(config_path: str = DEFAULT_CONFIG_FILENAME) -> dict:
    """
    Reads config.txt if present and populates os.environ so all modules
    (app, network, providers) seamlessly pick up the configuration.
    """
    loaded = {}
    if not os.path.exists(config_path):
        return loaded

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith(";"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                elif ":" in line:
                    key, val = line.split(":", 1)
                else:
                    continue

                key = key.strip().upper().replace(" ", "_")
                val = val.strip().strip("'\"")

                # Normalize aliases
                if key in ("APP_PASSWORD", "PASSWORD", "VIP_PASSWORD", "PASSCODE"):
                    target_key = "APP_PASSWORD"
                elif key in ("UNPAYWALL_EMAIL", "USER_EMAIL", "EMAIL", "MAILTO"):
                    target_key = "UNPAYWALL_EMAIL"
                elif key in ("ELSEVIER_API_KEY", "ELSEVIER_KEY", "SCOPUS_API_KEY", "SCOPUS_KEY", "ELSEVIER"):
                    target_key = "ELSEVIER_API_KEY"
                else:
                    target_key = key

                if val:
                    if target_key in os.environ and os.environ[target_key].strip():
                        log.info(f"🔒 Keeping existing environment secret for {target_key} (not overwritten by {config_path})")
                        loaded[target_key] = os.environ[target_key]
                    else:
                        os.environ[target_key] = val
                        loaded[target_key] = val
                else:
                    if target_key not in os.environ:
                        os.environ[target_key] = ""
                    loaded[target_key] = os.environ.get(target_key, "")

        if loaded:
            if not (os.environ.get("SPACE_ID") or os.environ.get("HF_SPACE")):
                os.environ["LOCAL_INSTANCE"] = "1"
            masked = {k: ("***" if ("PASS" in k or "KEY" in k) and v else v) for k, v in loaded.items()}
            log.info(f"⚙️ Loaded local configuration from {config_path}: {masked}")
    except Exception as e:
        log.warning(f"Failed to read local {config_path}: {e}")

    return loaded

def kill_port_occupants(port: int = 7860) -> list:
    """Find and terminate any orphaned/ghost processes holding the server port."""
    import subprocess
    cur_pid = str(os.getpid())
    killed = []
    try:
        net = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
        for line in net.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.strip().split()
                if parts:
                    pid = parts[-1]
                    if pid.isdigit() and pid not in ("0", "4", cur_pid):
                        print(f"[*] Terminating ghost process on port {port} (PID: {pid})...")
                        subprocess.run(["taskkill", "/F", "/T", "/PID", pid], capture_output=True)
                        killed.append(pid)
    except Exception:
        pass
    return killed

