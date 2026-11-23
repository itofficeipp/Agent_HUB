#!/usr/bin/env python3
"""Test cục bộ cho receiver tích hợp (AW_BACKEND=local), AW_EXPOSE, thống kê token, module n8n mẫu.
KHÔNG chạm OpenClaw/n8n/Telegram/Cloudflare thật: openclaw giả + HOME tạm. Chạy: python3 tests/test_local.py (cần python3, openssl)."""
import base64, hashlib, hmac, http.client, json, os, re, shutil, socket, subprocess, sys, tempfile, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="kit-local-"); H = T + "/home"; os.makedirs(H + "/bin")
shim = H + "/bin/openclaw"
open(shim, "w").write("#!/bin/sh\nexec python3 " + ROOT + "/tests/fake_openclaw.py \"$@\"\n"); os.chmod(shim, 0o755)
LOG = T + "/oc.log"
ENV = dict(os.environ, HOME=H, KIT_USER_HOME=H, KIT_HOME=T + "/cfg", OPENCLAW_BIN=shim, FAKE_OC_CFG=H + "/.openclaw/openclaw.json", FAKE_OC_LOG=LOG,
           KIT_NO_SYSTEMD="1", KIT_NO_PROBE="1", PATH=H + "/bin:" + os.environ["PATH"])
KIT = [sys.executable, ROOT + "/bin/kit"]
bad = 0
def ok(cond, name, extra=""):
    global bad; print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  " + str(extra)[:400])); bad += (not cond)
def sh(argv, inp=None, env=None): return subprocess.run(argv, capture_output=True, text=True, input=inp, env=env or ENV)
def freeport():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p
PORT = freeport()

# ---- 1. enable + apply (receiver tích hợp, expose=tunnel, stats=yes) ----
ok(sh(KIT + ["init", "t2"]).returncode == 0, "kit init t2")
r = sh(KIT + ["enable", "base", "--yes", "--set", "COMPANY_NAME=Cty Hai", "--set", "OWNER_NAME=Anh B", "--set", "WORKSPACE_DIR=" + H + "/ws"]); ok(r.returncode == 0, "enable base", r.stderr)
r = sh(KIT + ["enable", "agent-web", "--yes", "--set", "AW_LISTEN_PORT=%d" % PORT, "--set", "AW_PUBLIC_URL=https://agents.example.invalid", "--set", "AW_MCP_PROFILE=example",
              "--set", "AW_AGENT_ROOT=" + H + "/agents", "--set", "AW_STATS=yes", "--set", "AW_STATS_TARGET=12345"]); ok(r.returncode == 0, "enable agent-web (mac dinh local, tunnel)", r.stderr + r.stdout)
P = json.load(open(T + "/cfg/tenants/t2/params.json"))
ok(P["AW_BACKEND"] == "local" and P["AW_EXPOSE"] == "tunnel", "mac dinh: backend=local, expose=tunnel", P)
ok("AW_N8N_URL" not in P and "AW_REGISTRY_TABLE_ID" not in P, "backend local khong hoi tham so n8n", sorted(P))
r = sh(KIT + ["apply"]); ok(r.returncode == 0, "kit apply", r.stdout[-500:] + r.stderr)
A = T + "/cfg/tenants/t2/agent-web"; U = H + "/.config/systemd/user"
ok(os.path.exists(A + "/expose/cloudflared-config.yml") and not os.path.exists(A + "/expose/Caddyfile"), "expose=tunnel: chi co cloudflared-config.yml")
cf = open(A + "/expose/cloudflared-config.yml").read()
ok("agents.example.invalid" in cf and "127.0.0.1:%d" % PORT in cf and "{{" not in cf and re.search(r"webhook/[0-9a-f]{12}", cf), "cloudflared: dung hostname, cong, duong dan webhook", cf)
ok(oct(os.stat(A + "/expose/cloudflared-config.yml").st_mode & 0o777) == "0o600", "cloudflared-config.yml chmod 600")
ok(os.path.exists(A + "/expose/HUONG_DAN.md") and "cloudflared tunnel login" in open(A + "/expose/HUONG_DAN.md").read(), "co HUONG_DAN.md (tunnel)")
ok(os.path.exists(U + "/openclaw-kit-agentweb-receiver.service") and os.path.exists(U + "/openclaw-kit-agentweb-stats.timer"), "unit receiver + stats.timer da sinh")
ok("OnCalendar=*-*-* 08:00:00" in open(U + "/openclaw-kit-agentweb-stats.timer").read(), "stats.timer dung gio")
ok(not os.path.exists(A + "/orchestrator/n8n_tables.py") and not os.path.exists(A + "/orchestrator/build_workflow.py"), "backend local: khong cai script n8n")
ok(sh(KIT + ["apply"]).stdout.count("không đổi") >= 5, "apply lan 2 idempotent")

# ---- 2. keygen, add-caller, khởi động receiver ----
ok(sh(KIT + ["run", "agent-web", "keygen"]).returncode == 0, "keygen")
r = sh(KIT + ["run", "agent-web", "add-caller", "cty"]); ok("không cần khởi động lại" in r.stdout, "add-caller (local: khong can deploy workflow)", r.stdout)
PW = re.search(r"password\s+= (\S+)", r.stdout).group(1); HK = re.search(r"hmac_key\s+= (\S+)", r.stdout).group(1)
ENV2 = dict(ENV, KIT_TENANT="t2")
rcv = subprocess.Popen([sys.executable, A + "/orchestrator/receiver.py"], env=ENV2, stderr=open(T + "/receiver.log", "w"), stdout=subprocess.DEVNULL)
for _ in range(50):
    try: socket.create_connection(("127.0.0.1", PORT), 0.2).close(); break
    except OSError: time.sleep(0.1)
WP = "/webhook/" + P["AW_WEBHOOK_PATH"]
def req(method, path, body=None, headers=None):
    c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=20); c.request(method, path, body, headers or {}); r = c.getresponse(); t = r.read().decode(); c.close()
    try: return r.status, json.loads(t)
    except ValueError: return r.status, t
def call(body, user="cty", pw=None, secret=None, ts=None, sign=True, extra=None, path=None, raw=None):
    raw = raw if raw is not None else json.dumps(body, ensure_ascii=False).encode(); ts = str(ts or int(time.time()))
    h = {"Content-Type": "application/json", "Authorization": "Basic " + base64.b64encode(f"{user}:{pw or PW}".encode()).decode()}
    if sign: h["X-Timestamp"] = ts; h["X-Signature"] = "sha256=" + hmac.new((secret or HK).encode(), ts.encode() + b"." + raw, hashlib.sha256).hexdigest()
    h.update(extra or {}); return req("POST", path or WP, raw, h)
try:
    ok(req("GET", "/healthz") == (200, {"ok": True}), "GET /healthz")
    ok(req("GET", "/webhook/x")[0] == 404 and req("POST", "/khac", b"{}")[0] == 404, "duong dan la -> 404")
    B = {"user_id": "NV-A", "ho_ten": "Nguyen Van A", "email": "A@Example.com", "phong_ban": "IT"}
    T0 = int(time.time())
    st, js = call(B, ts=T0 - 5); ok(st == 201 and js["created"] and js["agent_id"].startswith("u_nv_a_"), "tao moi -> 201", (st, js))
    AGENT = js["agent_id"]
    st, js = call(B, ts=T0 - 4); ok(st == 200 and not js["created"] and js["agent_id"] == AGENT, "goi lai (ky moi) -> 200, giu agent cu", (st, js))
    st, js = call(B, ts=T0 - 5); ok(st == 409, "gui lai Y HET yeu cau da ky -> 409 (chong replay)", (st, js))
    ok(call(B, secret="sai")[0] == 401, "sai secret HMAC -> 401")
    ok(call(B, ts=int(time.time()) - 600)[0] == 401, "timestamp cu -> 401")
    ok(call(B, sign=False)[0] == 401, "khong chu ky (HMAC bat buoc) -> 401")
    ok(call(B, pw="sai")[0] == 403 and call(B, user="la")[0] == 403, "sai mat khau / sai user -> 403")
    ok(req("POST", WP, b"{}", {})[0] == 401, "khong Authorization -> 401")
    ok(call({"user_id": "NV-X"})[0] == 422, "thieu ho_ten -> 422")
    ok(call({"user_id": "a b c", "ho_ten": "X"})[0] == 422, "user_id sai -> 422")
    ok(call({"user_id": "NV-X", "ho_ten": "X", "email": "khong-phai-email"})[0] == 422, "email sai -> 422")
    ok(call(None, raw=b"khong phai json")[0] == 422, "body khong phai JSON -> 422")
    ok(req("POST", WP, b"x" * 70000, {"Authorization": "Basic eDp5"})[0] == 413, "body qua 64KB -> 413")
    ok(req("GET", WP)[0] == 404, "GET vao duong webhook -> 404")
    # Lỗi tìm thấy khi thử qua Cloudflare Tunnel thật: POST sai đường dẫn không đọc body -> body lọt vào yêu cầu kế tiếp trên cùng kết nối (HTTP 400)
    c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=10)
    c.request("POST", "/khac", b"x" * 200, {"Content-Type": "application/json"}); r1 = c.getresponse(); r1.read()
    c.request("GET", "/healthz"); r2 = c.getresponse(); b2 = r2.read(); c.close()
    ok(r1.status == 404 and r2.status == 200 and b'"ok"' in b2, "keep-alive: POST bi tu choi khong lam hong yeu cau ke tiep", (r1.status, r2.status))
    from datetime import datetime, timedelta, timezone
    hh = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    C = {"user_id": "NV-B", "ho_ten": "Tran B", "telegram_bot_username": "tranb_bot", "telegram_user_id": "123456789", "telegram_bot_token": "123456789:" + "A" * 35,
         "mcp_url": "https://mcp.example.com/mcp", "mcp_token": "tokenmcp-secret-12345", "mcp_pham_vi": "doc", "mcp_het_han": hh, "can_mcp": True}
    st, js = call(C); ok(st == 201 and js["telegram"]["trang_thai"] == "cho_gan", "tao NV-B co Telegram+MCP -> 201", (st, js))
    ok("123456789:AAAA" not in json.dumps(js) and "tokenmcp" not in json.dumps(js) and "bi_mat" not in json.dumps(js), "phan hoi khong chua token")
    ok(call(dict(C, user_id="NV-C", mcp_url="http://mcp.example.com/mcp"))[0] == 422, "mcp http -> 422")
    ok(call(dict(C, user_id="NV-C", mcp_pham_vi="la"))[0] == 422, "mcp pham vi la -> 422")
    ok(call(dict(C, user_id="NV-C", mcp_het_han="2020-01-01T00:00:00Z"))[0] == 422, "mcp het han da qua -> 422")
    ok(call(dict(C, user_id="NV-C", telegram_bot_token="sai"))[0] == 422, "token telegram sai dinh dang -> 422")
    ok(call({"user_id": "NV-C", "ho_ten": "C", "can_mcp": True})[0] == 422, "can_mcp thieu truong -> 422")
    import sqlite3
    db = sqlite3.connect(A + "/data/agent-web.db"); db.row_factory = sqlite3.Row
    ok(oct(os.stat(A + "/data/agent-web.db").st_mode & 0o777) == "0o600", "agent-web.db chmod 600")
    rg = {r["user_id"]: dict(r) for r in db.execute("select * from agent_registry")}; kn = {r["user_id"]: dict(r) for r in db.execute("select * from agent_kenh")}
    ok(set(rg) == {"NV-A", "NV-B"} and rg["NV-A"]["trang_thai"] == "cho_tao" and rg["NV-A"]["email"] == "a@example.com", "registry dung (2 nguoi, email chuan hoa)", rg)
    ok(list(kn) == ["NV-B"] and kn["NV-B"]["trang_thai"] == "cho_gan" and kn["NV-B"]["agent_id"] == rg["NV-B"]["agent_id"], "kenh chi co NV-B, cho_gan", kn)
    blob = open(A + "/data/agent-web.db", "rb").read().decode("latin1")
    ok("tokenmcp" not in blob and "AAAAAAAAAA" not in blob, "DB khong chua token ro")
    dec = subprocess.run("base64 -d | openssl pkeyutl -decrypt -inkey " + H + "/.config/agentweb/bi_mat.pem -pkeyopt rsa_padding_mode:oaep -pkeyopt rsa_oaep_md:sha256 -pkeyopt rsa_mgf1_md:sha256",
                         shell=True, input=kn["NV-B"]["bi_mat"], capture_output=True, text=True)
    d = json.loads(dec.stdout) if dec.returncode == 0 else {}
    ok(d.get("mcp") == "tokenmcp-secret-12345" and d.get("tg") == "123456789:" + "A" * 35, "bi_mat giai ma duoc bang khoa bi mat Gateway (giong gan_kenh.sh)", dec.stderr)
    log = open(T + "/receiver.log").read()
    ok("tokenmcp" not in log and PW not in log and HK not in log and "AAAAAAAAAA" not in log, "log receiver khong lo token/mat khau/khoa")

    # ---- 3. khoá khi sai xác thực liên tiếp (theo IP thật qua CF-Connecting-IP) ----
    ip = {"CF-Connecting-IP": "203.0.113.9"}
    codes = [call(B, pw="sai", extra=ip)[0] for _ in range(12)]
    ok(codes[:10] == [403] * 10 and codes[10:] == [429, 429], "10 lan sai -> khoa IP (429)", codes)
    ok(call(B, extra=ip)[0] == 429, "IP bi khoa: ca yeu cau dung cung 429")
    ok(call(B, ts=T0 - 3)[0] == 200, "IP khac khong bi anh huong")

    # ---- 4. provision.py (backend local) tạo agent thật qua create_agent.sh ----
    r = sh([sys.executable, A + "/orchestrator/provision.py", "--chi", "NV-A"], env=ENV2); print(r.stdout, r.stderr[-300:])
    ok(r.returncode == 0 and "OK NV-A" in r.stdout, "provision.py --chi NV-A: OK", r.stdout + r.stderr)
    db2 = sqlite3.connect(A + "/data/agent-web.db"); db2.row_factory = sqlite3.Row
    ra = dict(db2.execute("select * from agent_registry where user_id='NV-A'").fetchone())
    ok(ra["trang_thai"] == "da_tao" and ra["gateway_id"] == "gw1", "registry NV-A -> da_tao", ra)
    cfg = json.load(open(ENV["FAKE_OC_CFG"])); e = cfg["agents"]["entries"][ra["agent_id"]]
    ok(e["sandbox"]["mode"] == "all" and os.path.exists(H + "/agents/" + ra["agent_id"] + "/SOUL.md"), "agent that: sandbox=all + workspace co SOUL.md")
    ok(dict(db2.execute("select * from agent_registry where user_id='NV-B'").fetchone())["trang_thai"] == "cho_tao", "NV-B chua bi dong (--chi)")

    # ---- 5. thống kê token ----
    r = sh(KIT + ["run", "agent-web", "stats", "--in"], env=ENV2); print(r.stdout, r.stderr[-300:])
    ok(r.returncode == 0 and "Token t2" in r.stdout and "NV-A" in r.stdout, "token_stats: bao cao co NV-A", r.stdout + r.stderr)
    csvp = H + "/.local/state/openclaw-kit-agentweb/token_stats.csv"
    ok(os.path.exists(csvp) and oct(os.stat(csvp).st_mode & 0o777) == "0o600" and "NV-A" in open(csvp).read() and "NV-B" not in open(csvp).read(), "CSV chmod 600, chi nguoi da_tao")
    ok(os.path.exists(LOG) and "12345" in open(LOG).read() and "Token t2" in open(LOG).read(), "da gui bao cao toi AW_STATS_TARGET qua openclaw message send")

    # ---- 6. doctor ----
    r = sh(KIT + ["doctor"], env=ENV); print(r.stdout)
    ok("OK   [agent-web] receiver chỉ nghe loopback" in r.stdout, "doctor: receiver chi nghe loopback")
    ok("OK   [agent-web] receiver trả healthz" in r.stdout, "doctor: receiver healthz")
    ok("LOI  [agent-web] địa chỉ công khai" in r.stdout, "doctor: dia chi cong khai gia -> bao LOI (khong im lang)")
    s0 = socket.socket(); s0.bind(("0.0.0.0", 0)); s0.listen(1); p0 = s0.getsockname()[1]
    r = sh([sys.executable, A + "/orchestrator/check_listen.py", str(p0)]); ok(r.returncode == 1 and "nghe ra ngoài" in r.stderr, "check_listen bat cong nghe 0.0.0.0", r.stderr); s0.close()
    r = sh([sys.executable, A + "/orchestrator/check_listen.py", str(freeport())]); ok(r.returncode == 1 and "không có tiến trình" in r.stderr, "check_listen: cong khong ai nghe -> LOI")
    r = sh([sys.executable, A + "/orchestrator/check_public.py", "https://khong-ton-tai.example.invalid"]); ok(r.returncode != 0 and ("DNS" in r.stderr or "lỗi mạng" in r.stderr), "check_public chan doan DNS", r.stderr)
finally:
    rcv.terminate(); rcv.wait(10)

# ---- 7. AW_EXPOSE=port / none ----
for tn, mode, want, notwant in (("t3", "port", "Caddyfile", "cloudflared-config.yml"), ("t4", "none", None, None)):
    sh(KIT + ["init", tn]); sh(KIT + ["--tenant", tn, "enable", "base", "--yes", "--set", "COMPANY_NAME=X", "--set", "OWNER_NAME=Y", "--set", "WORKSPACE_DIR=" + H + "/ws" + tn])
    args = ["--tenant", tn, "enable", "agent-web", "--yes", "--set", "AW_EXPOSE=" + mode, "--set", "AW_AGENT_ROOT=" + H + "/a" + tn] + (["--set", "AW_PUBLIC_URL=https://agents.example.invalid"] if mode == "port" else [])
    r = sh(KIT + args); ok(r.returncode == 0, "enable agent-web expose=" + mode, r.stderr)
    r = sh(KIT + ["--tenant", tn, "apply", "agent-web", "--dry-run"]); o = r.stdout
    if want: ok(want in o and notwant not in o and "HUONG_DAN.md" in o, "expose=%s: sinh %s, khong sinh %s" % (mode, want, notwant), o[-300:])
    else: ok("Caddyfile" not in o and "cloudflared" not in o and "HUONG_DAN" not in o, "expose=none: khong sinh file expose")
r = sh(KIT + ["--tenant", "t3", "apply", "agent-web"]); ok(r.returncode == 0, "apply expose=port", r.stdout[-300:] + r.stderr)
cad = open(T + "/cfg/tenants/t3/agent-web/expose/Caddyfile").read()
ok("agents.example.invalid {" in cad and "reverse_proxy 127.0.0.1:8787" in cad and "/webhook/" in cad and "{{" not in cad, "Caddyfile dung hostname/cong/duong dan", cad)
r = sh(KIT + ["--tenant", "t3", "enable", "agent-web", "--yes", "--set", "AW_PUBLIC_URL=http://khong-https.example.com"]); ok(r.returncode != 0, "AW_PUBLIC_URL khong https bi tu choi")

# ---- 8. tenant cũ (có AW_N8N_URL, chưa có AW_BACKEND) không bị đổi sang local ----
os.makedirs(T + "/cfg/tenants/t6", exist_ok=True)
json.dump({"AW_N8N_URL": "https://n8n.example.com", "AW_WEBHOOK_PATH": "abcdef123456", "COMPANY_NAME": "Cu", "OWNER_NAME": "Cu", "WORKSPACE_DIR": H + "/wscu", "AW_AGENT_ROOT": H + "/acu"}, open(T + "/cfg/tenants/t6/params.json", "w"))
open(T + "/cfg/tenants/t6/secrets.env", "w").write("AW_N8N_API_KEY=k123456789\n")
r = sh(KIT + ["--tenant", "t6", "enable", "agent-web", "--yes"]); P6 = json.load(open(T + "/cfg/tenants/t6/params.json"))
ok(r.returncode == 0 and P6.get("AW_BACKEND") == "n8n", "tenant cu co AW_N8N_URL -> AW_BACKEND=n8n (khong doi hanh vi)", (P6, r.stderr))

# ---- 9. module n8n (chỉ sinh compose mẫu) ----
sh(KIT + ["init", "t7"]); sh(KIT + ["--tenant", "t7", "enable", "base", "--yes", "--set", "COMPANY_NAME=N", "--set", "OWNER_NAME=N", "--set", "WORKSPACE_DIR=" + H + "/wsn"])
r = sh(KIT + ["--tenant", "t7", "enable", "n8n", "--yes", "--set", "N8N_PUBLIC_URL=https://n8n.example.invalid", "--set", "N8N_DIR=" + H + "/n8n", "--set", "N8N_EXPOSE=tunnel"]); ok(r.returncode == 0, "enable n8n", r.stderr)
r = sh(KIT + ["--tenant", "t7", "apply", "n8n"]); ok(r.returncode == 0, "apply n8n", r.stdout[-300:] + r.stderr)
dc = open(H + "/n8n/docker-compose.yml").read()
ok("127.0.0.1:5678:5678" in dc and "WEBHOOK_URL=https://n8n.example.invalid/" in dc and "N8N_PROTOCOL=https" in dc and "N8N_SECURE_COOKIE=true" in dc and "{{" not in dc and "${N8N_ENCRYPTION_KEY}" in dc, "docker-compose.yml dung", dc)
ev = open(H + "/n8n/.env").read(); ok(oct(os.stat(H + "/n8n/.env").st_mode & 0o777) == "0o600" and re.search(r"^N8N_ENCRYPTION_KEY=\S{30,}$", ev, re.M), ".env chmod 600, co khoa ngau nhien")
ok("N8N_ENCRYPTION_KEY" not in open(T + "/cfg/tenants/t7/params.json").read(), "khoa n8n khong nam trong params.json")
ok(os.path.exists(H + "/n8n/expose/cloudflared-config.yml") and "n8n.example.invalid" in open(H + "/n8n/expose/cloudflared-config.yml").read(), "n8n: expose=tunnel sinh cloudflared-config.yml")
ok("webhook/.*" in open(H + "/n8n/expose/cloudflared-config.yml").read(), "n8n: tunnel chi cho /healthz va /webhook/*")

# ---- 10. mo_cong_cu (AW_TOOLS_*): mở web/browser/runtime cho agent sandbox, bỏ qua agent quyền rộng, idempotent ----
sh(KIT + ["init", "t8"]); sh(KIT + ["--tenant", "t8", "enable", "base", "--yes", "--set", "COMPANY_NAME=M", "--set", "OWNER_NAME=M", "--set", "WORKSPACE_DIR=" + H + "/wsm"])
r = sh(KIT + ["--tenant", "t8", "enable", "agent-web", "--yes", "--set", "AW_EXPOSE=none", "--set", "AW_AGENT_ROOT=" + H + "/am"]); ok(r.returncode == 0, "enable agent-web (AW_TOOLS_WEB mac dinh no)", r.stderr)
P8 = json.load(open(T + "/cfg/tenants/t8/params.json")); ok(P8["AW_TOOLS_WEB"] == "no" and "AW_TOOLS_BROWSER" not in P8, "mac dinh: AW_TOOLS_WEB=no, khong hoi tuy chon con", P8)
ok(sh(KIT + ["--tenant", "t8", "apply", "agent-web"]).returncode == 0, "apply agent-web t8 (tools tat)")
ocj = H + "/.config/agentweb/mo_cong_cu.json"; ok(os.path.exists(ocj) and json.load(open(ocj)) == {"web": False}, "tools tat: mo_cong_cu.json = {web:false}", open(ocj).read() if os.path.exists(ocj) else "")
STRICT = ["group:runtime", "group:sessions", "group:ui", "group:nodes", "group:automation", "group:agents", "group:messaging"]
cf = json.load(open(ENV["FAKE_OC_CFG"])); ent = cf.setdefault("agents", {}).setdefault("entries", {})
for aid, sbm in (("u_tt_norm", "all"), ("u_tt_full", "all"), ("u_tt_host", "off")):
    ent[aid] = {"workspace": H + "/x", "tools": {"deny": list(STRICT), "fs": {"workspaceOnly": True}}, "sandbox": {"mode": sbm}}
json.dump(cf, open(ENV["FAKE_OC_CFG"], "w")); snap = json.dumps(cf, sort_keys=True)
r = sh(KIT + ["--tenant", "t8", "run", "agent-web", "open-tools"]); ok(r.returncode != 0 and "AW_TOOLS_WEB=no" in (r.stderr + r.stdout), "tools tat: open-tools tu choi", r.stdout + r.stderr)
r = sh(["python3", H + "/openclaw-kit-agentweb/mo_cong_cu.py"]); ok(r.returncode == 0 and "XONG" in r.stdout and json.dumps(json.load(open(ENV["FAKE_OC_CFG"])), sort_keys=True) == snap, "tools tat: mo_cong_cu.py khong doi cau hinh", r.stdout)
r = sh(KIT + ["--tenant", "t8", "enable", "agent-web", "--yes", "--set", "AW_TOOLS_WEB=yes", "--set", "AW_TOOLS_BROWSER=yes", "--set", "AW_TOOLS_RUNTIME=yes", "--set", "AW_SANDBOX_IMAGE=img:test", "--set", "AW_SEARCH_PROVIDER=prov-x", "--set", "AW_FULL_AGENTS=u_tt_full"]); ok(r.returncode == 0, "enable AW_TOOLS_*=yes", r.stderr)
ok(sh(KIT + ["--tenant", "t8", "apply", "agent-web"]).returncode == 0, "apply agent-web t8 (tools bat)")
o8 = json.load(open(ocj)); ok(o8["web"] and o8["browser"] and o8["runtime"] and o8["full_agents"] == ["u_tt_full"] and o8["sandbox_image"] == "img:test" and oct(os.stat(ocj).st_mode & 0o777) == "0o600", "mo_cong_cu.json dung + chmod 600", o8)
r = sh(KIT + ["--tenant", "t8", "run", "agent-web", "open-tools", "--dry-run"]); ok(r.returncode == 0 and "SE " in r.stdout and json.dumps(json.load(open(ENV["FAKE_OC_CFG"])), sort_keys=True) == snap, "open-tools --dry-run: liet ke, khong ghi", r.stdout)
r = sh(KIT + ["--tenant", "t8", "run", "agent-web", "open-tools"]); ok(r.returncode == 0 and r.stdout.strip().endswith("XONG"), "open-tools: chay OK", r.stdout + r.stderr)
cf = json.load(open(ENV["FAKE_OC_CFG"])); en = cf["agents"]["entries"]
n = en["u_tt_norm"]["tools"]; f = en["u_tt_full"]["tools"]; h = en["u_tt_host"]["tools"]
ok("group:runtime" not in n["deny"] and "group:ui" not in n["deny"] and "terminal" in n["deny"] and "group:sessions" in n["deny"], "agent thuong: bo runtime + ui, thay ui bang danh sach hep, giu sessions", n["deny"])
ok(n["sandbox"]["tools"]["alsoAllow"] == ["web_search", "web_fetch", "browser"], "agent thuong: alsoAllow web_search/web_fetch/browser", n["sandbox"])
ok("gateway" in n["sandbox"]["tools"]["deny"] and "telegram" in n["sandbox"]["tools"]["deny"], "agent thuong: sandbox.deny chan gateway/kenh nhan tin")
ok("deny" not in f.get("sandbox", {}).get("tools", {}) and f["sandbox"]["tools"]["alsoAllow"][:2] == ["web_search", "web_fetch"], "agent quyen rong: co web nhung KHONG bi ghi de sandbox.deny", f)
ok(h == {"deny": STRICT, "fs": {"workspaceOnly": True}}, "agent khong sandbox: khong bi dong vao", h)
ok(cf["tools"]["web"]["search"]["provider"] == "prov-x" and cf["agents"]["defaults"]["sandbox"]["docker"]["image"] == "img:test" and cf["agents"]["defaults"]["sandbox"]["browser"]["enabled"] is True, "toan cuc: search provider, image sandbox, browser.enabled")
snap2 = json.dumps(cf, sort_keys=True); r = sh(KIT + ["--tenant", "t8", "run", "agent-web", "open-tools"])
ok(r.returncode == 0 and "OK " not in r.stdout and json.dumps(json.load(open(ENV["FAKE_OC_CFG"])), sort_keys=True) == snap2, "open-tools lan 2 idempotent (khong thay doi)", r.stdout)

cf = json.load(open(ENV["FAKE_OC_CFG"])); cf["agents"]["entries"]["u_tt_new"] = {"workspace": H + "/x", "tools": {"deny": list(STRICT), "fs": {"workspaceOnly": True}}, "sandbox": {"mode": "all"}}; json.dump(cf, open(ENV["FAKE_OC_CFG"], "w"))
r = sh([sys.executable, T + "/cfg/tenants/t8/agent-web/orchestrator/provision.py"], env=dict(ENV, KIT_TENANT="t8"))
cf = json.load(open(ENV["FAKE_OC_CFG"])); nw = cf["agents"]["entries"]["u_tt_new"]["tools"]
ok(r.returncode == 0 and "OK mo cong cu" in r.stdout and nw["sandbox"]["tools"]["alsoAllow"] == ["web_search", "web_fetch", "browser"] and "group:runtime" not in nw["deny"], "provision.py: agent moi tao duoc mo cong cu tu dong (AW_TOOLS_WEB=yes)", r.stdout + r.stderr)

# ---- 11. kit setup: cai tung buoc co goi y (tuong tac qua pty + khong tuong tac) + preflight ----
import pty, select
def drive(argv, rules, env, tmo=120):
    """Chay lenh trong pty, tra loi cac cau hoi theo rules [(regex, [cac tra loi lan luot])]; chua khop = Enter."""
    pid, fd = pty.fork()
    if pid == 0:
        os.execvpe(argv[0], argv, env)
    out = ""; seg = ""; t0 = time.time(); used = {}
    while time.time() - t0 < tmo:
        r, _, _ = select.select([fd], [], [], 0.6)
        if r:
            try: d = os.read(fd, 4096).decode("utf-8", "replace")
            except OSError: break
            if not d: break
            out += d; seg += d; continue
        # im lang: dang cho nhap
        if not seg.strip(): continue
        ans = ""
        for i, (rx, lst) in enumerate(rules):
            if re.search(rx, out[out.rfind("\r\n\r\n"):]):
                n = used.get(i, 0)
                if n < len(lst): ans = lst[n]; used[i] = n + 1
                break
        os.write(fd, (ans + "\n").encode()); seg = ""
    try: _, st = os.waitpid(pid, 0)
    except ChildProcessError: st = 0
    return os.waitstatus_to_exitcode(st), out

pp = freeport()
rules = [
    (r"Ví dụ: congty-abc", ["Sai Ten!", "cty-pty"]),
    (r"Tên công ty/đơn vị", ["", "Cty Pty"]),
    (r"Tên người chủ", ["Chu Pty"]),
    (r"\[base\] Múi giờ", ["gio sai", ""]),
    (r"Thư mục workspace của agent chính", [H + "/wspty"]),
    (r"Cổng receiver", [str(pp)]),
    (r"Địa chỉ công khai", ["https://agents.pty.example.invalid"]),
    (r"Thư mục workspace các agent", [H + "/agpty"]),
    (r"tên bên gọi", ["hrm"]),
]
rc, out = drive(KIT + ["setup"], rules, ENV)
ok(rc == 0, "kit setup (tuong tac): ket thuc rc=0", out[-1200:][-600:])
ok("gợi ý:" in out and "ví dụ:" in out, "kit setup: hien goi y + vi du khi hoi")
ok("chưa nhập (bắt buộc)" in out and "sai định dạng" in out and "nhập lại" in out, "kit setup: nhap sai thi bao loi va hoi lai (khong thoat)")
ok("Tóm tắt" in out and out.index("Tóm tắt") < out.index("Dựng và kiểm tra"), "kit setup: co tom tat truoc khi dung")
SP = T + "/cfg/tenants/cty-pty"
Pp = json.load(open(SP + "/params.json")) if os.path.exists(SP + "/params.json") else {}
ok(Pp.get("COMPANY_NAME") == "Cty Pty" and Pp.get("OWNER_NAME") == "Chu Pty" and Pp.get("TIMEZONE") == "Asia/Ho_Chi_Minh" and Pp.get("AW_LISTEN_PORT") == str(pp), "kit setup: luu dung gia tri (sau khi nhap lai), mac dinh khi Enter", Pp)
stp = json.load(open(SP + "/state.json")) if os.path.exists(SP + "/state.json") else {}
ok(set(stp.get("applied", {})) >= {"base", "agent-web"} and "n8n" not in stp.get("enabled", []), "kit setup: da bat + apply base, agent-web; n8n khong bat", stp)
ok(os.path.exists(SP + "/agent-web/gateway_pub.pem") and os.path.exists(SP + "/agent-web/users.json") and "hrm" in open(SP + "/agent-web/users.json").read(), "kit setup: da keygen + tao ben goi 'hrm'")
ok("kit doctor" in out and "BƯỚC TIẾP" in out, "kit setup: chay doctor va in buoc tiep")
ok("sk-" not in out, "kit setup: khong in bi mat ra man hinh")
# khong tuong tac
cfgf = T + "/p11.json"; json.dump({"COMPANY_NAME": "Cty 11", "OWNER_NAME": "Chu 11", "WORKSPACE_DIR": H + "/ws11", "AW_LISTEN_PORT": str(freeport()), "AW_PUBLIC_URL": "https://a11.example.invalid", "AW_AGENT_ROOT": H + "/ag11", "_ghi_chu": "bo qua"}, open(cfgf, "w"))
r = sh(KIT + ["setup", "cty-11", "--yes", "--modules", "base,agent-web", "--params-file", cfgf, "--no-apply"]); ok(r.returncode == 0 and "--no-apply" in r.stdout and "cty-11" in os.listdir(T + "/cfg/tenants"), "kit setup --yes --no-apply: luu + xem truoc, khong dung", r.stdout[-400:] + r.stderr)
ok(json.load(open(T + "/cfg/tenants/cty-11/state.json")).get("applied", {}) == {}, "kit setup --no-apply: chua apply gi")
r = sh(KIT + ["setup", "cty-11", "--yes", "--modules", "base,agent-web", "--params-file", cfgf]); ok(r.returncode == 0 and "BƯỚC TIẾP" in r.stdout, "kit setup --yes: dung thuc + doctor + buoc tiep", r.stdout[-300:] + r.stderr)
ok(set(json.load(open(T + "/cfg/tenants/cty-11/state.json"))["applied"]) >= {"base", "agent-web"}, "kit setup --yes (tenant co san): da apply", r.stdout[-400:] + r.stderr)
r = sh(KIT + ["setup", "cty-12", "--yes", "--modules", "base", "--no-apply"]); ok(r.returncode != 0 and "COMPANY_NAME" in r.stderr, "kit setup --yes thieu tham so bat buoc: loi ro, nen noi ten tham so", r.stderr)
r = sh(KIT + ["setup", "cty-13", "--yes", "--modules", "khong-co"]); ok(r.returncode != 0 and "khong-co" in r.stderr, "kit setup: module khong ton tai bi tu choi", r.stderr)
r = sh(KIT + ["setup", "--yes"]); ok(r.returncode != 0 and "tên tenant" in r.stderr, "kit setup --yes khi co nhieu tenant ma khong chi ten: tu choi", r.stderr)
r = sh(KIT + ["preflight"]); ok(r.returncode == 0 and "openclaw" in r.stdout and "sẵn sàng" in r.stdout, "kit preflight: OK voi openclaw gia", r.stdout[-400:])
env2 = dict(ENV, OPENCLAW_BIN="/khong/co/openclaw"); r = sh(KIT + ["preflight"], env=env2); ok(r.returncode == 1 and "LOI" in r.stdout and "openclaw onboard" in r.stdout, "kit preflight: thieu openclaw -> LOI + goi y cai", r.stdout[-400:])
# umask 002 (Ubuntu mac dinh): kit khong duoc tao ~/.config nhom-ghi-duoc (OpenClaw tu choi cai service)
nh = T + "/newhome"; os.makedirs(nh)
r = subprocess.run(KIT + ["init", "cty-um"], capture_output=True, text=True, preexec_fn=lambda: os.umask(0o002), env=dict(ENV, KIT_HOME=nh + "/.config/openclaw-kit", KIT_USER_HOME=nh))
md = lambda p: oct(os.stat(p).st_mode & 0o777)
ok(r.returncode == 0 and not (os.stat(nh + "/.config").st_mode & 0o022) and md(nh + "/.config/openclaw-kit/tenants/cty-um") == "0o700", "umask 002: kit init khong tao ~/.config nhom-ghi-duoc; tenant 0700", md(nh + "/.config"))
os.chmod(nh + "/.config", 0o775); r = sh(KIT + ["preflight"], env=dict(ENV, KIT_HOME=nh + "/.config/openclaw-kit", KIT_USER_HOME=nh)); ok(r.returncode == 1 and "chmod go-w" in r.stdout, "preflight: ~/.config nhom-ghi-duoc -> LOI + goi y chmod go-w", r.stdout[-300:])
r = sh(KIT + ["--tenant", "cty-pty", "doctor"], env=dict(ENV, FAKE_OC_WARN="1")); ok("CANH BAO openclaw: plugins.entries.duckduckgo" in r.stdout and "openclaw config validate" in r.stdout and "LOI  openclaw config validate" not in r.stdout, "doctor: in canh bao cua openclaw config validate (khong tinh la loi)", r.stdout[-500:])
# tenant mac dinh: tao/cau hinh tenant thu hai KHONG doi tenant dang dung; kit use moi doi
th = T + "/h2"; os.makedirs(th); E3 = dict(ENV, KIT_HOME=th + "/cfg", KIT_USER_HOME=th)
cur = lambda: open(th + "/cfg/current").read().strip()
sh(KIT + ["init", "ten-a"], env=E3); ok(cur() == "ten-a", "tenant dau tien thanh mac dinh")
r = sh(KIT + ["init", "ten-b"], env=E3); ok(cur() == "ten-a" and "kit use ten-b" in r.stdout, "kit init tenant thu hai: KHONG doi mac dinh + huong dan kit use", r.stdout)
sh(KIT + ["setup", "ten-c", "--yes", "--modules", "base", "--no-apply", "--set", "COMPANY_NAME=C", "--set", "OWNER_NAME=C"], env=E3); ok(cur() == "ten-a", "kit setup tenant moi (--no-apply): KHONG doi mac dinh", cur())
r = sh(KIT + ["use", "ten-b"], env=E3); ok(r.returncode == 0 and cur() == "ten-b", "kit use ten-b: doi mac dinh", r.stdout + r.stderr)
r = sh(KIT + ["use", "khong-co"], env=E3); ok(r.returncode != 0 and "ten-a" in r.stderr and cur() == "ten-b", "kit use tenant khong ton tai: tu choi, liet ke tenant co", r.stderr)

# moi module.json: moi tham so co hint
for mn in ("base", "agent-web", "n8n"):
    miss = [s["key"] for s in json.load(open(ROOT + "/modules/" + mn + "/module.json"))["params"] if not s.get("hint")]
    ok(not miss, "module " + mn + ": moi tham so deu co goi y (hint)", miss)

print("\n=== KET QUA test_local:", "TAT CA PASS" if not bad else str(bad) + " LOI", "(thu muc tam:", T + ")")
if not bad: shutil.rmtree(T, ignore_errors=True)
sys.exit(1 if bad else 0)
