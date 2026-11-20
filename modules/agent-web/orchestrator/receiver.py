#!/usr/bin/env python3
"""Receiver tích hợp: nhận webhook tạo nhân viên (thay workflow n8n), ghi vào SQLite cục bộ. Chỉ stdlib (+ lệnh 'openssl').
Giữ nguyên giao thức của bản n8n: POST /webhook/<AW_WEBHOOK_PATH>, Basic auth + HMAC (X-Timestamp, X-Signature = sha256(ts.body)).
Thêm: chống gửi lại (mỗi chữ ký chỉ dùng được 1 lần trong 10 phút), giới hạn tần suất theo IP, khoá tạm khi sai xác thực nhiều lần.
Chỉ nghe 127.0.0.1 (đưa ra Internet bằng Cloudflare Tunnel hoặc Caddy, xem module AW_EXPOSE). Không bao giờ ghi token/mật khẩu vào log."""
import base64, datetime, hashlib, hmac, http.server, json, os, re, subprocess, sys, threading, time
import awconf as A
import store

PATH = "/webhook/" + A.need("AW_WEBHOOK_PATH")
HOST = A.C.get("AW_LISTEN_HOST") or "127.0.0.1"
PORT = int(A.C.get("AW_LISTEN_PORT") or 8787)
MAX_BODY = 64 * 1024
RATE_PER_MIN = int(A.C.get("AW_RATE_PER_MIN") or 60)       # số yêu cầu/phút/IP
FAIL_MAX, FAIL_WINDOW, LOCK_SEC = 10, 300, 300             # sai xác thực >=10 lần/5 phút -> khoá 5 phút
TRUST_PROXY = (A.C.get("AW_TRUST_PROXY") or "yes") == "yes"  # tin X-Forwarded-For/CF-Connecting-IP khi kết nối đến từ loopback

_lock = threading.Lock()
_hits, _fails, _locked = {}, {}, {}
_cfg = {"mtime": None, "users": {}, "salt": ""}
_scopes = None

def now_iso(): return datetime.datetime.now().astimezone().isoformat(timespec="seconds")

def users():
    p = A.AWDIR + "/users.json"
    try: m = os.stat(p).st_mtime
    except OSError: return {}, ""
    if _cfg["mtime"] != m:
        d = json.load(open(p, encoding="utf-8")); _cfg.update(mtime=m, users=d.get("users", {}), salt=d.get("salt", ""))
    return _cfg["users"], _cfg["salt"]

def scopes():
    global _scopes
    if _scopes is None:
        p = A.AWDIR + "/mcp_profile.json"
        _scopes = sorted(json.load(open(p, encoding="utf-8")).get("scopes", {})) if os.path.exists(p) else []
    return _scopes

def rsa_encrypt(plain: bytes) -> str:
    r = subprocess.run(["openssl", "pkeyutl", "-encrypt", "-pubin", "-inkey", A.AWDIR + "/gateway_pub.pem",
                        "-pkeyopt", "rsa_padding_mode:oaep", "-pkeyopt", "rsa_oaep_md:sha256", "-pkeyopt", "rsa_mgf1_md:sha256"],
                       input=plain, capture_output=True, timeout=20)
    if r.returncode != 0 or not r.stdout: raise RuntimeError("openssl khong ma hoa duoc")
    return base64.b64encode(r.stdout).decode()

def parse_iso(s):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})", s): return None
    m = re.fullmatch(r"(.*?)(\.\d+)?(Z|[+-]\d{2}:\d{2})", s)
    head, frac, tz = m.group(1), (m.group(2) or ""), ("+00:00" if m.group(3) == "Z" else m.group(3))
    if len(head) == 16: head += ":00"
    frac = (frac + "000000")[:7] if frac else ""
    try: return datetime.datetime.fromisoformat(head + frac + tz)
    except ValueError: return None

class Fail(Exception):
    def __init__(self, code, loi, auth=False): self.code, self.loi, self.auth = code, loi, auth

def validate(user, rec, headers, raw):
    """Trả dict dữ liệu đã chuẩn hoá (như node 'Xác thực' của n8n)."""
    ts = headers.get("x-timestamp", ""); sig = headers.get("x-signature", "").lower()
    sig = sig[7:] if sig.startswith("sha256=") else sig
    if sig or rec["hmac"] == "bat_buoc":
        if not sig: raise Fail(401, "thieu_x-signature", True)
        if not re.fullmatch(r"\d{10}", ts): raise Fail(401, "thieu_hoac_sai_x-timestamp", True)
        if abs(time.time() - int(ts)) > 300: raise Fail(401, "x-timestamp_lech_qua_5_phut", True)
        exp = hmac.new(rec["secret"].encode(), ts.encode() + b"." + raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, exp): raise Fail(401, "sai_chu_ky", True)
    try: b = json.loads(raw.decode("utf-8"))
    except Exception: raise Fail(422, "body_khong_phai_json")
    if not isinstance(b, dict): raise Fail(422, "body_khong_phai_json")
    s = lambda v: "" if v is None else str(v).strip()
    user_id, ho_ten, email, phong_ban = s(b.get("user_id")), s(b.get("ho_ten")), s(b.get("email")).lower(), s(b.get("phong_ban"))
    if not re.fullmatch(r"[A-Za-z0-9_.@-]{1,64}", user_id): raise Fail(422, "user_id_bat_buoc_1-64_ky_tu_A-Z_0-9_._@-")
    if not ho_ten or len(ho_ten) > 200: raise Fail(422, "ho_ten_bat_buoc_toi_da_200")
    if email and (len(email) > 200 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email)): raise Fail(422, "email_sai_dinh_dang")
    if len(phong_ban) > 200: raise Fail(422, "phong_ban_toi_da_200")
    slug = re.sub(r"^_+|_+$", "", re.sub(r"[^a-z0-9]+", "_", user_id.lower()))[:40] or "x"
    agent_id = "u_" + slug + "_" + hashlib.sha256(user_id.encode()).hexdigest()[:8]
    tg_bot, tg_uid, tg_tok = s(b.get("telegram_bot_username")).lstrip("@"), s(b.get("telegram_user_id")), s(b.get("telegram_bot_token"))
    mcp_url, mcp_tok, mcp_pv, mcp_hh = s(b.get("mcp_url")), s(b.get("mcp_token")), s(b.get("mcp_pham_vi")).lower(), s(b.get("mcp_het_han"))
    co_tg, co_mcp = bool(tg_bot or tg_uid or tg_tok), bool(mcp_url or mcp_tok or mcp_pv or mcp_hh)
    can_mcp = b.get("can_mcp") is True or s(b.get("can_mcp")).lower() == "true"
    if can_mcp and not (mcp_url and mcp_tok and mcp_pv and mcp_hh): raise Fail(422, "thieu_mcp")
    PV = scopes()
    if (can_mcp or co_mcp) and not PV: raise Fail(422, "mcp_khong_duoc_bat_cho_tenant_nay")
    if co_tg:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{3,30}bot", tg_bot, re.I): raise Fail(422, "telegram_bot_username_sai_dinh_dang")
        if not re.fullmatch(r"[1-9][0-9]{4,14}", tg_uid): raise Fail(422, "telegram_user_id_phai_la_so")
        if not re.fullmatch(r"[0-9]{6,12}:[A-Za-z0-9_-]{30,60}", tg_tok): raise Fail(422, "telegram_bot_token_sai_dinh_dang")
    if co_mcp:
        if not re.fullmatch(r"https://[A-Za-z0-9.-]+(:[0-9]{2,5})?(/[A-Za-z0-9._~/-]*)?", mcp_url) or len(mcp_url) > 300: raise Fail(422, "mcp_url_phai_la_https")
        if not re.fullmatch(r"[A-Za-z0-9_.-]{8,200}", mcp_tok): raise Fail(422, "mcp_token_sai_dinh_dang")
        pv = [v.strip() for v in mcp_pv.split(",") if v.strip()]
        if not pv or any(v not in PV for v in pv): raise Fail(422, "mcp_pham_vi_chi_gom_" + ",".join(PV))
        t = parse_iso(mcp_hh)
        if t is None: raise Fail(422, "mcp_het_han_phai_la_ISO8601")
        if t.timestamp() <= time.time(): raise Fail(422, "mcp_het_han_da_qua")
    bi_mat = ""
    if co_tg or co_mcp:
        plain = json.dumps({"tg": tg_tok if co_tg else "", "mcp": mcp_tok if co_mcp else ""}, separators=(",", ":")).encode()
        if len(plain) > 300: raise Fail(422, "token_qua_dai")
        try: bi_mat = rsa_encrypt(plain)
        except Exception: raise Fail(500, "khong_ma_hoa_duoc_bi_mat")
    return dict(user_id=user_id, ho_ten=ho_ten, email=email, phong_ban=phong_ban, agent_id=agent_id, goi_boi=user,
                co_kenh=co_tg or co_mcp, telegram_bot_username=tg_bot if co_tg else "", telegram_user_id=tg_uid if co_tg else "",
                mcp_url=mcp_url if co_mcp else "", mcp_pham_vi=mcp_pv if co_mcp else "", mcp_het_han=mcp_hh if co_mcp else "", bi_mat=bi_mat)

_db = threading.local()
def db():
    if not hasattr(_db, "c"): _db.c = store.connect(A.DB)
    return _db.c

def ghi(r):
    c = db(); c.execute("BEGIN IMMEDIATE")
    try:
        ex = store.rows(c, "agent_registry", "user_id", r["user_id"], 1)
        if ex: moi, agent_id, tt = False, ex[0]["agent_id"], ex[0]["trang_thai"]
        else:
            moi, agent_id, tt = True, r["agent_id"], "cho_tao"
            store.upsert(c, "agent_registry", "user_id", dict(user_id=r["user_id"], agent_id=agent_id, ho_ten=r["ho_ten"], email=r["email"],
                         phong_ban=r["phong_ban"], gateway_id="", trang_thai="cho_tao", ghi_chu="tao qua webhook " + now_iso()))
        if r["co_kenh"]:
            store.upsert(c, "agent_kenh", "user_id", dict(user_id=r["user_id"], agent_id=agent_id, telegram_bot_username=r["telegram_bot_username"],
                         telegram_user_id=r["telegram_user_id"], mcp_url=r["mcp_url"], mcp_pham_vi=r["mcp_pham_vi"], mcp_het_han=r["mcp_het_han"],
                         bi_mat=r["bi_mat"], trang_thai="cho_gan", cap_nhat_luc=now_iso(), ghi_chu="webhook goi boi " + r["goi_boi"]))
        c.execute("COMMIT")
    except Exception:
        c.execute("ROLLBACK"); raise
    out = {"ok": True, "created": moi, "user_id": r["user_id"], "agent_id": agent_id, "trang_thai": tt}
    if r["telegram_bot_username"]: out["telegram"] = {"bot": "@" + r["telegram_bot_username"], "telegram_user_id": r["telegram_user_id"], "trang_thai": "cho_gan"}
    if r["mcp_url"]: out["mcp"] = {"url": r["mcp_url"], "pham_vi": r["mcp_pham_vi"], "het_han": r["mcp_het_han"], "trang_thai": "da_luu_chua_bat"}
    return (201 if moi else 200), out

def rate_ok(ip):
    t = time.time()
    with _lock:
        if _locked.get(ip, 0) > t: return False
        h = [x for x in _hits.get(ip, []) if x > t - 60]; h.append(t); _hits[ip] = h
        if len(_hits) > 5000: _hits.clear()
        return len(h) <= RATE_PER_MIN

def note_fail(ip):
    t = time.time()
    with _lock:
        f = [x for x in _fails.get(ip, []) if x > t - FAIL_WINDOW]; f.append(t); _fails[ip] = f
        if len(f) >= FAIL_MAX: _locked[ip] = t + LOCK_SEC; _fails[ip] = []

class H(http.server.BaseHTTPRequestHandler):
    server_version = "aw-receiver"; protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass
    def client_ip(self):
        ip = self.client_address[0]
        if TRUST_PROXY and ip in ("127.0.0.1", "::1"):
            ip = (self.headers.get("CF-Connecting-IP") or (self.headers.get("X-Forwarded-For") or "").split(",")[0].strip() or ip)[:64]
        return ip
    def send_json(self, code, obj, extra=None):
        b = json.dumps(obj, ensure_ascii=False).encode()
        if self.command == "POST" and not getattr(self, "_body_read", False): self.close_connection = True  # chưa đọc body: không dùng lại kết nối (tránh lẫn body vào yêu cầu sau)
        self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        if self.close_connection: self.send_header("Connection", "close")
        for k, v in (extra or {}).items(): self.send_header(k, v)
        self.end_headers(); self.wfile.write(b)
    def log(self, ip, who, code, note=""):
        sys.stderr.write(f"{now_iso()} {ip} user={who or '-'} {self.command} {code} {note}\n"); sys.stderr.flush()
    def do_GET(self):
        if self.path == "/healthz": return self.send_json(200, {"ok": True})
        self.send_json(404, {"ok": False, "loi": "khong_co"})
    def do_POST(self):
        ip = self.client_ip(); who = ""; self._body_read = False
        try:
            if self.path.split("?")[0] != PATH: return self.send_json(404, {"ok": False, "loi": "khong_co"})
            if not rate_ok(ip):
                self.log(ip, who, 429); return self.send_json(429, {"ok": False, "loi": "qua_nhieu_yeu_cau"}, {"Retry-After": "60"})
            try: n = int(self.headers.get("Content-Length", "-1"))
            except ValueError: n = -1
            if n < 0: return self.send_json(411, {"ok": False, "loi": "thieu_content-length"})
            if n > MAX_BODY: return self.send_json(413, {"ok": False, "loi": "body_qua_lon"})
            raw = self.rfile.read(n); self._body_read = True
            hd = {k.lower(): v for k, v in self.headers.items()}
            m = re.fullmatch(r"Basic\s+([A-Za-z0-9+/=]+)", hd.get("authorization", ""), re.I)
            if not m: raise Fail(401, "thieu_xac_thuc", True)
            try: dec = base64.b64decode(m.group(1)).decode("utf-8")
            except Exception: raise Fail(401, "thieu_xac_thuc", True)
            i = dec.find(":"); user, pw = (dec[:i], dec[i + 1:]) if i > 0 else ("", "")
            U, salt = users(); rec = U.get(user) if user in U else None
            ph = hashlib.sha256((salt + ":" + pw).encode()).hexdigest()
            if not rec or not hmac.compare_digest(ph, rec["h"]): raise Fail(403, "sai_user_hoac_mat_khau", True)
            who = user
            r = validate(user, rec, hd, raw)
            sig = (hd.get("x-signature", "") or "").lower()
            if sig and not store.claim_replay(db(), hashlib.sha256((user + ":" + sig).encode()).hexdigest()):
                raise Fail(409, "yeu_cau_lap_lai_hay_ky_lai_voi_x-timestamp_moi", True)
            code, out = ghi(r)
            self.log(ip, who, code, ("created " if out["created"] else "existing ") + r["user_id"]); self.send_json(code, out)
        except Fail as f:
            if f.auth: note_fail(ip)
            self.log(ip, who, f.code, f.loi); self.send_json(f.code, {"ok": False, "loi": f.loi})
        except Exception as e:
            self.log(ip, who, 500, type(e).__name__); self.send_json(500, {"ok": False, "loi": "loi_may_chu"})

class S(http.server.ThreadingHTTPServer):
    daemon_threads = True; request_queue_size = 64

def main():
    db()  # tạo bảng sớm, lỗi quyền hiện ngay khi khởi động
    srv = S((HOST, PORT), H)
    sys.stderr.write(f"{now_iso()} receiver nghe {HOST}:{srv.server_port} duong dan {PATH[:13]}...\n"); sys.stderr.flush()
    try: srv.serve_forever()
    except KeyboardInterrupt: pass

if __name__ == "__main__": main()
