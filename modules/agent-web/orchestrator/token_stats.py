#!/usr/bin/env python3
"""Thống kê token theo người (mỗi người dùng = 1 agent riêng, nên thống kê theo agent = theo người). Tuỳ chọn: AW_STATS=yes.
Mỗi agent trong bảng registry (trang_thai=da_tao) -> 'openclaw gateway usage-cost --agent <id> --days N --json' trên máy Gateway
(số liệu do chính OpenClaw ghi). Ghi CSV (~/.local/state/openclaw-kit-agentweb/token_stats.csv) và gửi báo cáo tóm tắt qua
'openclaw message send' tới AW_STATS_TARGET (trống = chỉ ghi CSV).
Dùng: token_stats.py [--ngay YYYY-MM-DD] [--khong-gui] [--in]   (mặc định: hôm qua + luỹ kế tháng)"""
import argparse, csv, datetime, json, os, subprocess, sys
import awconf as A

ST = os.path.expanduser("~/.local/state/openclaw-kit-agentweb"); CSV = ST + "/token_stats.csv"
FIELDS = ["date", "agent_id", "user_id", "ho_ten", "phong_ban", "input", "output", "cacheRead", "cacheWrite", "totalTokens", "totalCost"]
def fmt(n): return format(int(n), ",").replace(",", ".")

def usage(agent, days):
    c = A.gw("openclaw gateway usage-cost --agent " + agent + " --days " + str(days) + " --timeout 120000 --json", timeout=180)
    out = c.stdout; i = out.find("{")
    if c.returncode != 0 or i < 0: raise RuntimeError((c.stderr or out)[-200:].strip() or "rc=" + str(c.returncode))
    return json.loads(out[i:])

def load_csv():
    d = {}
    if os.path.exists(CSV):
        for r in csv.DictReader(open(CSV, encoding="utf-8")): d[(r["date"], r["agent_id"])] = r
    return d

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--ngay"); ap.add_argument("--khong-gui", action="store_true"); ap.add_argument("--in", dest="inra", action="store_true")
    o = ap.parse_args()
    today = datetime.date.today(); ngay = datetime.date.fromisoformat(o.ngay) if o.ngay else today - datetime.timedelta(days=1)
    dau_thang = ngay.replace(day=1); days = (today - dau_thang).days + 1
    reg = A.rows(A.table("registry"), "trang_thai", "da_tao")
    if not reg: print("Chưa có nhân viên nào ở trạng thái da_tao."); return 0
    data = load_csv(); loi = []
    for r in reg:
        try: u = usage(r["agent_id"], days)
        except Exception as e: loi.append(r["user_id"] + ": " + str(e)[:120]); continue
        for d in u.get("daily", []):
            data[(d["date"], r["agent_id"])] = {"date": d["date"], "agent_id": r["agent_id"], "user_id": r["user_id"], "ho_ten": r.get("ho_ten", ""),
                "phong_ban": r.get("phong_ban", ""), "input": d.get("input", 0), "output": d.get("output", 0), "cacheRead": d.get("cacheRead", 0),
                "cacheWrite": d.get("cacheWrite", 0), "totalTokens": d.get("totalTokens", 0), "totalCost": d.get("totalCost", 0)}
    os.makedirs(ST, exist_ok=True)
    tmp = CSV + ".tmp"; fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, FIELDS); w.writeheader()
        for k in sorted(data): w.writerow({x: data[k].get(x, "") for x in FIELDS})
    os.replace(tmp, CSV)
    ids = {r["agent_id"]: r for r in reg}
    hom, thang = {}, {}
    for (d, a), r in data.items():
        if a not in ids: continue
        t = int(float(r["totalTokens"] or 0)); c = float(r["totalCost"] or 0)
        if d == ngay.isoformat(): hom[a] = (t, c)
        if dau_thang.isoformat() <= d <= ngay.isoformat(): x = thang.get(a, (0, 0.0)); thang[a] = (x[0] + t, x[1] + c)
    def bang(m, n=15):
        rows = sorted(m.items(), key=lambda kv: -kv[1][0])[:n]
        return [str(i + 1) + ". " + (ids[a]["ho_ten"] or ids[a]["user_id"]) + " (" + ids[a]["user_id"] + "): " + fmt(t) + " token" + (" ~US$" + format(c, ".2f") if c > 0 else "")
                for i, (a, (t, c)) in enumerate(rows) if t > 0]
    tong_h, tong_t = sum(v[0] for v in hom.values()), sum(v[0] for v in thang.values())
    msg = ["📊 Token " + A.TENANT + " - ngày " + ngay.strftime("%d/%m/%Y") + ": " + fmt(tong_h) + " token (" + str(sum(1 for v in hom.values() if v[0] > 0)) + " người dùng)"]
    msg += bang(hom) or ["(không có người dùng nào dùng trong ngày)"]
    msg += ["Luỹ kế tháng " + ngay.strftime("%m/%Y") + ": " + fmt(tong_t) + " token"] + bang(thang)
    if loi: msg += ["⚠️ Không lấy được: " + " | ".join(loi[:5])]
    text = "\n".join(msg)
    tgt = A.C.get("AW_STATS_TARGET")
    if o.inra or not tgt: print(text)
    if tgt and not o.khong_gui:
        r = subprocess.run([A.C.get("OPENCLAW_BIN", "openclaw"), "message", "send", "--channel", A.C.get("AW_ALERT_CHANNEL", "telegram"),
                            "--target", tgt, "--message", text], capture_output=True, text=True, timeout=90)
        if r.returncode != 0: print("LOI gui bao cao:", (r.stderr or r.stdout)[-200:]); return 1
        print("OK da gui bao cao toi", tgt)
    return 1 if loi else 0
sys.exit(main())
