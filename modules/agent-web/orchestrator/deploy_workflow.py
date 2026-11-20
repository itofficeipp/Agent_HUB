#!/usr/bin/env python3
"""Tạo hoặc cập nhật workflow n8n từ build_workflow.py, sao lưu bản cũ trước, rồi bật (publish).
Quy ước n8n: PUT chỉ gửi name,nodes,connections,settings (bỏ availableInMCP, timeSavedMode, binaryMode). Lưu workflow id vào state.
Dùng: deploy_workflow.py [--dry-run]"""
import json, os, subprocess, sys, datetime
import awconf as A
dry = "--dry-run" in sys.argv
r = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_workflow.py")], capture_output=True, text=True)
if r.returncode != 0: sys.exit(r.stderr.strip() or "LOI build_workflow")
w = json.loads(r.stdout)
names = {n["name"] for n in w["nodes"]}
for a, c in w["connections"].items():
    assert a in names, a
    for outs in c["main"]:
        for o in outs: assert o["node"] in names, o["node"]
body = {k: w[k] for k in ("name", "nodes", "connections")}
body["settings"] = {k: v for k, v in w["settings"].items() if k not in ("availableInMCP", "timeSavedMode", "binaryMode")}
sf = A.AWDIR + "/workflow_id"; wid = open(sf).read().strip() if os.path.exists(sf) else A.C.get("AW_WORKFLOW_ID", "")
print(f"workflow '{body['name']}': {len(body['nodes'])} node; {'cap nhat ' + wid if wid else 'tao moi'}" + (" (dry-run, khong goi n8n)" if dry else ""))
if dry: sys.exit(0)
if wid:
    bk = os.path.join(A.KIT_HOME, "backups", f"n8n-{wid}-{datetime.datetime.now():%Y%m%d-%H%M%S}.json"); os.makedirs(os.path.dirname(bk), exist_ok=True)
    fd = os.open(bk, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f: json.dump(A.n8n("GET", f"/workflows/{wid}"), f, ensure_ascii=False)
    print("sao luu workflow cu ->", bk)
    d = A.n8n("PUT", f"/workflows/{wid}", body)
else:
    d = A.n8n("POST", "/workflows", body); wid = d["id"]
    fd = os.open(sf, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f: f.write(wid + "\n")
try: A.n8n("POST", f"/workflows/{wid}/activate")
except Exception as e: print("CANH BAO: khong tu bat duoc (bat tay trong n8n neu can):", str(e)[:150])
print("OK workflow id", wid, "-> URL:", A.need("AW_N8N_URL").rstrip("/") + "/webhook/" + A.need("AW_WEBHOOK_PATH"))
