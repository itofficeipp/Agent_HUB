#!/usr/bin/env python3
"""Tạo agent thật từ các dòng 'cho_tao' trong bảng registry (n8n Data table), gắn bot Telegram ('cho_gan') và MCP riêng.
Chạy trên máy orchestrator (có truy cập n8n API); Gateway thao tác qua awconf.gw (local hoặc ssh).
Dùng: provision.py [--chi user_id]   In dòng 'OK ...' / 'LOI ...' / 'BO_QUA ...'; exit 1 nếu có LỖI."""
import argparse, base64, datetime, json, os, sys
import awconf as A

GW_ID = A.C.get("AW_GATEWAY_ID", "gw1"); GDIR = A.C.get("AW_GATEWAY_DIR", "~/openclaw-kit-agentweb")
TB, TK = A.table("registry"), A.table("kenh")
def now(): return datetime.datetime.now().astimezone().isoformat(timespec="seconds")
def last_line(c, prefixes):
    so = [l for l in c.stdout.strip().splitlines() if l.startswith(prefixes)]
    out = (c.stdout + c.stderr).strip().splitlines()
    return so[-1] if so else (out[-1] if out else "")

def tao_agent(only):
    rs = A.rows(TB, "trang_thai", "cho_tao")
    if only: rs = [r for r in rs if r["user_id"] == only]
    print("cho_tao:", len(rs)); loi = 0
    for r in rs:
        p = {k: r.get(k) for k in ("agent_id", "user_id", "ho_ten", "email", "phong_ban")}
        b = base64.b64encode(json.dumps(p, ensure_ascii=False).encode()).decode()
        t0 = datetime.datetime.now()
        c = A.gw(f"AGENT_ROOT={A.C.get('AW_AGENT_ROOT', '/srv/agents')} {GDIR}/create_agent.sh {b}")
        dt = (datetime.datetime.now() - t0).total_seconds(); last = last_line(c, ("OK ", "LOI ", "DA_CO"))
        if c.returncode == 0 and last.startswith(("OK ", "DA_CO")):
            A.update(TB, A.flt("agent_id", p["agent_id"]), {"trang_thai": "da_tao", "gateway_id": GW_ID,
                     "ghi_chu": (r.get("ghi_chu") or "") + f" | da_tao {now()}"})
            print(f"OK {p['user_id']} -> {p['agent_id']} @ {GW_ID} ({dt}s)")
        else:
            loi += 1; print(f"LOI {p['user_id']} rc={c.returncode} ({dt}s): {last}")
    return loi

MCP_LAI = set()
def gan_kenh(only):
    rs = A.rows(TK, "trang_thai", "cho_gan")
    if only: rs = [r for r in rs if r["user_id"] == only]
    print("cho_gan:", len(rs)); loi = 0
    for r in rs:
        reg = A.rows(TB, "user_id", r["user_id"], 5)
        if not reg or reg[0].get("trang_thai") != "da_tao" or reg[0].get("gateway_id") != GW_ID:
            print(f"BO_QUA {r['user_id']}: agent chua tao tren {GW_ID}"); continue
        if not r.get("telegram_bot_username"):
            A.update(TK, A.flt("user_id", r["user_id"]), {"trang_thai": "khong_co_telegram", "cap_nhat_luc": now()}); continue
        p = {"agent_id": reg[0]["agent_id"], "telegram_user_id": r["telegram_user_id"],
             "telegram_bot_username": r["telegram_bot_username"], "bi_mat": r["bi_mat"]}
        c = A.gw(f"{GDIR}/gan_kenh.sh", input=json.dumps(p)); last = last_line(c, ("OK ", "LOI "))
        ok = c.returncode == 0 and last.startswith("OK ")
        # chống ghi đè: chỉ đổi trạng thái nếu cap_nhat_luc chưa đổi kể từ lúc đọc (web có thể gửi lại kênh giữa chừng)
        f2 = {"type": "and", "filters": [{"columnName": "user_id", "condition": "eq", "value": r["user_id"]},
                                         {"columnName": "cap_nhat_luc", "condition": "eq", "value": r.get("cap_nhat_luc")}]}
        A.update(TK, f2, {"trang_thai": "da_gan" if ok else "loi_gan", "cap_nhat_luc": now(), "ghi_chu": last[:300]})
        print(("OK " if ok else "LOI ") + f"{r['user_id']} -> {last}")
        if not ok: loi += 1
        elif r.get("mcp_url") and r.get("mcp_pham_vi"): MCP_LAI.add(reg[0]["agent_id"])
    return loi

def gan_mcp(only):
    if not os.path.exists(A.AWDIR + "/mcp_profile.json"): return 0
    rs = [r for r in A.rows(TK, "trang_thai", "da_gan") if r.get("mcp_url") and r.get("mcp_pham_vi") and r.get("agent_id")]
    if only: rs = [r for r in rs if r["user_id"] == only]
    c = A.gw(f"python3 {GDIR}/gan_mcp.py --state", timeout=60)
    if c.returncode != 0: print("LOI mcp doc cau hinh gateway rc=%d" % c.returncode); return 1
    st = json.loads(c.stdout.strip().splitlines()[-1]); loi = 0
    for r in rs:
        a = r["agent_id"]
        if a not in st["ag"]: continue
        pv = [x.strip() for x in r["mcp_pham_vi"].split(",") if x.strip()]
        n = A.gw(f"python3 {GDIR}/gan_mcp.py --count {','.join(pv)}", timeout=30)
        can = int(n.stdout.strip() or -1) if n.returncode == 0 else -1
        if a not in MCP_LAI and st["ag"][a] == can and st.get("tk", {}).get(a): continue  # đủ server, đủ tool, token khớp
        k = A.gw(f"python3 {GDIR}/gan_mcp.py {a} {','.join(pv)} {r['mcp_url']}", timeout=600); last = last_line(k, ("OK ", "LOI "))
        ok = k.returncode == 0 and last.startswith("OK ")
        print(("OK " if ok else "LOI ") + f"mcp {r['user_id']} -> {last[:200]}"); loi += (not ok)
    if st.get("thieu_deny"):
        s = A.gw(f"python3 {GDIR}/gan_mcp.py --sua", timeout=120); last = last_line(s, ("OK", "LOI"))
        ok = s.returncode == 0 and last.startswith("OK"); print(("OK " if ok else "LOI ") + f"mcp dong bo -> {last[:200]}"); loi += (not ok)
    return loi

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--chi"); o = ap.parse_args()
    loi = tao_agent(o.chi) + gan_kenh(o.chi) + gan_mcp(o.chi)
    sys.exit(1 if loi else 0)
main()
