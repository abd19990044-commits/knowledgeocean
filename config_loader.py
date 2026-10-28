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
                elif key in ("LOW_GPU_MODE", "LOW_GPU", "ENERGY_SAVER", "POWER_SAVING"):
                    target_key = "LOW_GPU_MODE"
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


def save_local_config(settings: dict, config_path: str = DEFAULT_CONFIG_FILENAME) -> bool:
    """
    Saves or updates key=value settings in config.txt and updates os.environ.
    Preserves existing lines and comments in config.txt.
    """
    try:
        updated_keys = set()
        new_lines = []

        normalized_settings = {}
        for k, v in settings.items():
            k_clean = str(k).strip().upper().replace(" ", "_")
            if k_clean in ("APP_PASSWORD", "PASSWORD", "VIP_PASSWORD", "PASSCODE"):
                normalized_settings["APP_PASSWORD"] = str(v).strip()
            elif k_clean in ("UNPAYWALL_EMAIL", "USER_EMAIL", "EMAIL", "MAILTO"):
                normalized_settings["UNPAYWALL_EMAIL"] = str(v).strip()
            elif k_clean in ("ELSEVIER_API_KEY", "ELSEVIER_KEY", "SCOPUS_API_KEY", "SCOPUS_KEY", "ELSEVIER"):
                normalized_settings["ELSEVIER_API_KEY"] = str(v).strip()
            elif k_clean in ("LOW_GPU_MODE", "LOW_GPU", "ENERGY_SAVER", "POWER_SAVING"):
                normalized_settings["LOW_GPU_MODE"] = str(v).strip()
            else:
                normalized_settings[k_clean] = str(v).strip()

        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line in lines:
                raw = line.strip()
                matched_key = None
                if "=" in raw and not raw.startswith("#") and not raw.startswith(";"):
                    k_part = raw.split("=", 1)[0].strip().upper().replace(" ", "_")
                    for norm_k in normalized_settings:
                        if k_part == norm_k:
                            matched_key = norm_k
                            break
                elif ":" in raw and not raw.startswith("#") and not raw.startswith(";"):
                    k_part = raw.split(":", 1)[0].strip().upper().replace(" ", "_")
                    for norm_k in normalized_settings:
                        if k_part == norm_k:
                            matched_key = norm_k
                            break

                if matched_key:
                    new_val = normalized_settings[matched_key]
                    new_lines.append(f"{matched_key} = {new_val}\n")
                    updated_keys.add(matched_key)
                else:
                    new_lines.append(line)
        else:
            new_lines.append("# ===============================================================================\n")
            new_lines.append("#                     محيط المعرفة | Knowledge Ocean Local Config\n")
            new_lines.append("# ===============================================================================\n")

        # Append any new keys that weren't present in the file
        for k, v in normalized_settings.items():
            if k not in updated_keys:
                new_lines.append(f"{k} = {v}\n")
                updated_keys.add(k)

        with open(config_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        # Update environment variables
        for k, v in normalized_settings.items():
            os.environ[k] = v

        log.info(f"💾 Updated configuration in {config_path} for keys: {list(normalized_settings.keys())}")
        return True
    except Exception as e:
        log.error(f"Failed to save local config to {config_path}: {e}")
        return False


