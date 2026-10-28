# -*- coding: utf-8 -*-
"""
Knowledge Ocean - Self-Signed Authenticode Digital Code Signing Tool
Signs Windows PE executables (.exe, .dll) using a self-signed code signing certificate
associated with 'Knowledge Ocean / ABDULSALAM S. HASAN'.
"""
from __future__ import annotations

import os
import sys
import subprocess
import tempfile
from pathlib import Path

CERT_SUBJECT = "CN=Knowledge Ocean, O=ABDULSALAM S. HASAN"

def sign_file(target_file: str | Path) -> bool:
    """Signs an executable with an Authenticode signature using PowerShell."""
    target_path = Path(target_file).resolve()
    if not target_path.exists():
        print(f"[X] Sign target does not exist: {target_path}")
        return False

    ps_code = f"""
    $ErrorActionPreference = 'Stop'
    $cert = Get-ChildItem Cert:\\CurrentUser\\My -CodeSigningCert | Where-Object {{ $_.Subject -like "*{CERT_SUBJECT}*" }} | Select-Object -First 1
    if (-not $cert) {{
        Write-Host "[*] Creating Self-Signed Code Signing Certificate ({CERT_SUBJECT})..."
        $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject "{CERT_SUBJECT}" -CertStoreLocation "Cert:\\CurrentUser\\My" -NotAfter (Get-Date).AddYears(5)
    }}

    Write-Host "[*] Applying Authenticode Signature to: {target_path}"
    $sig = Set-AuthenticodeSignature -FilePath "{target_path}" -Certificate $cert
    Write-Host "[+] Signature Status: $($sig.Status)"
    Write-Host "[+] Signer: $($sig.SignerCertificate.Subject)"
    """

    with tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False, encoding="utf-8-sig") as tmp:
        tmp.write(ps_code)
        tmp_path = tmp.name

    try:
        res = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", tmp_path],
            capture_output=True,
            text=True
        )
        if res.stdout:
            print(res.stdout.strip())
        if res.stderr and "warning" not in res.stderr.lower():
            print(res.stderr.strip())
        return res.returncode == 0
    except Exception as e:
        print(f"[X] Signing execution failed: {e}")
        return False
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = sys.argv[1]
        ok = sign_file(target)
        sys.exit(0 if ok else 1)
    else:
        print("Usage: python sign_tool.py <path_to_exe>")
