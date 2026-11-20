#!/usr/bin/env python3
"""Chạy định kỳ bởi systemd timer: provision.py có khóa flock (không chạy chồng).
- Không có việc -> im lặng. Có việc -> ghi ~/.local/state/openclaw-kit-agentweb/provision.log
- Có LỖI -> ghi sự kiện JSON vào loi_su_kien.log; nếu đặt AW_ALERT_TARGET thì nhắn qua 'openclaw message send'
  (chỉ nhắn lại khi nội dung lỗi đổi). Lỗi mạng chập chờn chỉ báo khi kéo dài >=5 lần liên tiếp."""
import datetime, fcntl, hashlib, json, os, subprocess, sys
import awconf as A
D = os.path.dirname(os.path.abspath(__file__))
ST = os.path.expanduser("~/.local/state/openclaw-kit-agentweb"); os.makedirs(ST, exist_ok=True)
LOG, LAST, MANG = ST + "/provision.log", ST + "/loi_cuoi.sha", ST + "/loi_mang.dem"
lk = open(ST + "/tick.lock", "w")
try: fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError: sys.exit(0)
now = lambda: datetime.datetime.now().astimezone().isoformat(timespec="seconds")
try:
    c = subprocess.run([sys.executable, D + "/provision.py"], capture_output=True, text=True, timeout=1500)
    out, rc = (c.stdout + c.stderr).strip(), c.returncode
except subprocess.TimeoutExpired: out, rc = "LOI provision.py chay qua 25 phut", 99
lines = out.splitlines()
co_viec = [l for l in lines if l.startswith(("OK ", "LOI ", "BO_QUA "))]
loi = [l for l in lines if l.startswith("LOI ")] or ([] if rc == 0 else lines[-5:])
if co_viec or rc != 0:
    with open(LOG, "a") as f: f.write(f"--- {now()} rc={rc}\n{out}\n")
if rc == 0 and not loi:
    for p in (LAST, MANG):
        if os.path.exists(p): os.remove(p)
    sys.exit(0)
NET = ("Temporary failure in name resolution", "Network is unreachable", "timed out", "Connection refused", "Connection reset", "No route to host")
if not co_viec and any(k in out for k in NET):
    dem = (int(open(MANG).read() or 0) if os.path.exists(MANG) else 0) + 1; open(MANG, "w").write(str(dem))
    if dem < 5: sys.exit(0)
    loi = ["LOI mang: khong ket noi duoc n8n/Internet tu 5 lan tick lien tiep"]
elif os.path.exists(MANG): os.remove(MANG)
h = hashlib.sha256("\n".join(loi).encode()).hexdigest()
if os.path.exists(LAST) and open(LAST).read().strip() == h: sys.exit(0)
tom = " | ".join(l[:300] for l in loi[:8]).replace("\n", " ")
with open(ST + "/loi_su_kien.log", "a") as f: f.write(json.dumps({"luc": now(), "rc": rc, "loi": tom}, ensure_ascii=False) + "\n")
open(LAST, "w").write(h)
tgt = A.C.get("AW_ALERT_TARGET")
if tgt:
    subprocess.run([A.C.get("OPENCLAW_BIN", "openclaw"), "message", "send", "--channel", A.C.get("AW_ALERT_CHANNEL", "telegram"),
                    "--target", tgt, "--message", f"⚠️ agent-web ({A.TENANT}): tao agent/gan kenh loi {now()}\n" + "\n".join(l[:300] for l in loi[:8])],
                   capture_output=True, text=True, timeout=60)
