#!/usr/bin/env python3
"""Đưa script Gateway (create_agent.sh, gan_kenh.sh, gan_mcp.py) + mcp_profile.json lên máy Gateway. local: sao chép; ssh: scp."""
import os, shlex, subprocess, sys
import awconf as A
src = A.AWDIR + "/gateway"; gdir = A.C.get("AW_GATEWAY_DIR", "~/openclaw-kit-agentweb"); host = A.C.get("AW_GATEWAY_SSH", "local")
prof = A.AWDIR + "/mcp_profile.json"
if host == "local":
    cmds = f"mkdir -p {gdir} ~/.config/agentweb && cp {shlex.quote(src)}/* {gdir}/ && chmod 755 {gdir}/*"
    if os.path.exists(prof): cmds += f" && cp {shlex.quote(prof)} ~/.config/agentweb/mcp_profile.json"
    r = subprocess.run(["bash", "-c", cmds], capture_output=True, text=True)
else:
    ssh = ["-o", "BatchMode=yes"] + (["-i", os.path.expanduser(A.C["AW_GATEWAY_SSH_KEY"])] if A.C.get("AW_GATEWAY_SSH_KEY") else [])
    r = subprocess.run(["ssh"] + ssh + [host, f"mkdir -p {gdir} ~/.config/agentweb"], capture_output=True, text=True)
    if r.returncode == 0:
        r = subprocess.run(["scp", "-q"] + ssh + [f"{src}/{f}" for f in os.listdir(src)] + [f"{host}:{gdir}/"], capture_output=True, text=True)
    if r.returncode == 0 and os.path.exists(prof):
        r = subprocess.run(["scp", "-q"] + ssh + [prof, f"{host}:.config/agentweb/mcp_profile.json"], capture_output=True, text=True)
    if r.returncode == 0: r = A.gw(f"chmod 755 {gdir}/*")
if r.returncode != 0: sys.exit("LOI deploy_gateway: " + r.stderr[-300:])
print("OK da dua script gateway ->", host, gdir)
