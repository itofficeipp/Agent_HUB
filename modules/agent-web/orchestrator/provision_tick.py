#!/usr/bin/env python3
"""Chạy định kỳ bởi systemd timer: provision.py có khóa flock (không chạy chồng).
- Không có việc -> im lặng. Có việc -> ghi ~/.local/state/openclaw-kit-agentweb/provision.log
- Có LỖI -> ghi sự kiện JSON vào loi_su_kien.log; nếu đặt AW_ALERT_TARGET thì nhắn qua bot báo lỗi (AW_ALERT_BOT_TOKEN, gửi thẳng Bot API) hoặc dự phòng 'openclaw message send'
  (chỉ nhắn lại khi nội dung lỗi đổi). Lỗi mạng chập chờn chỉ báo khi kéo dài >=5 lần liên tiếp."""
import datetime, fcntl, hashlib, json, os, subprocess, sys
import awconf as A
D = os.path.dirname(os.path.abspath(__file__))
ST = os.path.expanduser("~/.local/state/openclaw-kit-agentweb"); os.makedirs(ST, exist_ok=True)
LOG, LAST, MANG, DAGHI = ST + "/provision.log", ST + "/loi_cuoi.sha", ST + "/loi_mang.dem", ST + "/loi_da_ghi.sha"
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
    for p in (LAST, MANG, DAGHI):
        if os.path.exists(p): os.remove(p)
    sys.exit(0)
NET = ("Temporary failure in name resolution", "Network is unreachable", "timed out", "Connection refused", "Connection reset", "No route to host")
if not co_viec and any(k in out for k in NET):
    dem = (int(open(MANG).read() or 0) if os.path.exists(MANG) else 0) + 1; open(MANG, "w").write(str(dem))
    if dem < 5: sys.exit(0)
    loi = ["LOI mang: khong ket noi duoc n8n/Internet tu 5 lan tick lien tiep"]
elif os.path.exists(MANG): os.remove(MANG)
h = hashlib.sha256("\n".join(loi).encode()).hexdigest()
if os.path.exists(LAST) and open(LAST).read().strip() == h: sys.exit(0)   # lỗi này đã báo thành công rồi
daghi = open(DAGHI).read().strip() if os.path.exists(DAGHI) else ""
tom = " | ".join(l[:300] for l in loi[:8]).replace("\n", " ")
if daghi not in (h, h + "!"):   # ghi sự kiện đúng 1 lần cho mỗi lỗi mới
    with open(ST + "/loi_su_kien.log", "a") as f: f.write(json.dumps({"luc": now(), "rc": rc, "loi": tom}, ensure_ascii=False) + "\n")
    daghi = h; open(DAGHI, "w").write(h)
if A.C.get("AW_ALERT_TARGET"):
    okk, why = A.alert(f"⚠️ agent-web ({A.TENANT}): tao agent/gan kenh loi {now()}\n" + "\n".join(l[:300] for l in loi[:8]))
    if okk: open(LAST, "w").write(h)   # chỉ đánh dấu 'đã báo' khi gửi thật được; chưa được thì tick sau thử gửi lại
    elif daghi != h + "!":
        with open(ST + "/loi_su_kien.log", "a") as f: f.write(json.dumps({"luc": now(), "canh_bao_khong_gui_duoc": why}, ensure_ascii=False) + "\n")
        open(DAGHI, "w").write(h + "!")
else: open(LAST, "w").write(h)
