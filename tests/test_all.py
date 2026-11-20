#!/usr/bin/env python3
"""Test cục bộ, KHÔNG chạm OpenClaw/n8n/Telegram thật: openclaw giả + n8n giả (HTTP) + HOME tạm.
Chạy: python3 tests/test_all.py     (cần python3, node, openssl)"""
import base64, http.server, json, os, shutil, subprocess, sys, tempfile, threading, urllib.parse
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="kit-test-"); H = T + "/home"; os.makedirs(H + "/bin")
shim = H + "/bin/openclaw"
open(shim, "w").write("#!/bin/sh\nexec python3 " + ROOT + "/tests/fake_openclaw.py \"$@\"\n"); os.chmod(shim, 0o755)
ENV = dict(os.environ, HOME=H, KIT_USER_HOME=H, KIT_HOME=T + "/cfg", OPENCLAW_BIN=shim, FAKE_OC_CFG=H + "/.openclaw/openclaw.json",
           KIT_NO_SYSTEMD="1", PATH=H + "/bin:" + os.environ["PATH"])
KIT = [sys.executable, ROOT + "/bin/kit"]
bad = 0
def ok(cond, name, extra=""):
    global bad; print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  " + str(extra)[:300])); bad += (not cond)
def sh(argv, inp=None, env=None):
    return subprocess.run(argv, capture_output=True, text=True, input=inp, env=env or ENV)

# ---- mock n8n ----
ROWS = {"REGTBL01": [{"user_id": "NV-1", "agent_id": "u_nv_1_a1b2c3d4", "ho_ten": "An", "email": "", "phong_ban": "IT", "trang_thai": "cho_tao", "ghi_chu": ""}], "KENTBL01": []}
WF = {}
class H_(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, o, code=200):
        b = json.dumps(o).encode(); self.send_response(code); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b)
    def _match(self, row, f): return all(row.get(x["columnName"]) == x["value"] for x in f["filters"])
    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query); p = u.path.split("/")
        if "rows" in p:
            rows = ROWS[p[p.index("data-tables") + 1]]
            if "filter" in q: rows = [r for r in rows if self._match(r, json.loads(q["filter"][0]))]
            return self._send({"data": rows})
        if p[-1].startswith("workflows") or "workflows" in p: return self._send({"data": []})
        self._send({}, 404)
    def do_PATCH(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"]))); t = self.path.split("/")[self.path.split("/").index("data-tables") + 1]
        n = 0
        for r in ROWS[t]:
            if self._match(r, body["filter"]): r.update(body["data"]); n += 1
        self._send({"updatedCount": n})
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0)); body = json.loads(self.rfile.read(n)) if n else {}
        if self.path.endswith("/workflows"): WF["body"] = body; return self._send({"id": "WF123"})
        if self.path.endswith("/activate"): return self._send({"active": True})
        self._send({}, 404)
srv = http.server.HTTPServer(("127.0.0.1", 0), H_); threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_port}"

# ---- 1. kit init/enable/apply ----
r = sh(KIT + ["init", "t1"]); ok(r.returncode == 0, "kit init", r.stderr)
r = sh(KIT + ["enable", "base", "--yes", "--set", "COMPANY_NAME=Cty Thu", "--set", "OWNER_NAME=Anh A", "--set", "WORKSPACE_DIR=" + H + "/ws"]); ok(r.returncode == 0, "enable base", r.stderr)
r = sh(KIT + ["enable", "agent-web", "--yes", "--set", "AW_BACKEND=n8n", "--set", "AW_N8N_URL=" + URL, "--set", "AW_N8N_API_KEY=dummy-key-123", "--set", "AW_REGISTRY_TABLE_ID=REGTBL01",
              "--set", "AW_CHANNEL_TABLE_ID=KENTBL01", "--set", "AW_MCP_PROFILE=example", "--set", "AW_AGENT_ROOT=" + H + "/agents"]); ok(r.returncode == 0, "enable agent-web", r.stderr + r.stdout)
r = sh(KIT + ["apply"]); ok(r.returncode == 0, "kit apply (base + agent-web)", r.stdout[-400:] + r.stderr)
cfg = json.load(open(ENV["FAKE_OC_CFG"])); ok(cfg["agents"]["defaults"]["userTimezone"] == "Asia/Ho_Chi_Minh", "config patch da ap")
ok(os.path.exists(H + "/ws/AGENTS.md") and os.path.exists(H + "/openclaw-kit-agentweb/gan_mcp.py"), "file workspace + gateway da dung")
sec = T + "/cfg/tenants/t1/secrets.env"; ok(oct(os.stat(sec).st_mode & 0o777) == "0o600", "secrets.env chmod 600")
ok("dummy-key-123" not in open(T + "/cfg/tenants/t1/params.json").read(), "bi mat khong nam trong params.json")
r = sh(KIT + ["apply"]); ok("không đổi" in r.stdout and r.returncode == 0, "apply lan 2 idempotent", r.stdout[-300:])
r = sh(KIT + ["doctor"]); print(r.stdout)

# ---- 2. keygen + add-caller + build workflow ----
r = sh(KIT + ["run", "agent-web", "keygen"]); ok(r.returncode == 0, "keygen", r.stderr + r.stdout)
r = sh(KIT + ["run", "agent-web", "add-caller", "cty"]); ok(r.returncode == 0 and "password" in r.stdout, "add-caller", r.stderr)
ok(oct(os.stat(T + "/cfg/tenants/t1/agent-web/users.json").st_mode & 0o777) == "0o600", "users.json chmod 600")
r = sh(KIT + ["run", "agent-web", "deploy-workflow"]); ok(r.returncode == 0 and "WF123" in r.stdout, "deploy-workflow (n8n giả)", r.stdout + r.stderr)
w = WF.get("body", {}); ok(len(w.get("nodes", [])) == 11, "workflow co 11 node", len(w.get("nodes", [])))
js = [n for n in w.get("nodes", []) if n["name"] == "Xác thực"][0]["parameters"]["jsCode"]
ok("__" not in js.replace("__proto__", "") and '"doc"' in js, "placeholder da thay, scopes tu profile")
ok("dummy-key-123" not in json.dumps(w), "workflow khong chua API key")
pw_line = [l for l in r.stdout.splitlines()]  # noqa

# ---- 3. logic webhook bang node + giải mã RSA như gan_kenh ----
open(T + "/xt.js", "w").write(js)
pub = T + "/cfg/tenants/t1/agent-web/gateway_pub.pem"
n = sh(["node", ROOT + "/tests/test_xac_thuc.js", ROOT + "/modules/agent-web/n8n/code/xac_thuc.js", pub, T + "/out.json"]); print(n.stdout); ok(n.returncode == 0, "xac_thuc.js node tests", n.stdout[-500:] + n.stderr)
try:
    bm = json.load(open(T + "/out.json.mcp"))["bi_mat"]
    dec = subprocess.run("base64 -d | openssl pkeyutl -decrypt -inkey " + H + "/.config/agentweb/bi_mat.pem -pkeyopt rsa_padding_mode:oaep -pkeyopt rsa_oaep_md:sha256 -pkeyopt rsa_mgf1_md:sha256",
                         shell=True, input=bm, capture_output=True, text=True)
    ok(json.loads(dec.stdout)["mcp"] == "tokenmcp-secret-12345", "bi_mat giai ma duoc bang khoa bi mat gateway (RSA-OAEP-SHA256)", dec.stderr)
except Exception as e: ok(False, "giai ma bi_mat", e)

# ---- 4. orchestrator -> gateway (provision.py tao agent that qua create_agent.sh) ----
ENV2 = dict(ENV, KIT_TENANT="t1")
r = sh([sys.executable, T + "/cfg/tenants/t1/agent-web/orchestrator/provision.py"], env=ENV2); print(r.stdout, r.stderr[-300:])
ok(r.returncode == 0 and ROWS["REGTBL01"][0]["trang_thai"] == "da_tao", "provision.py: cho_tao -> da_tao", r.stdout + r.stderr)
ws = H + "/agents/u_nv_1_a1b2c3d4"
ok(os.path.exists(ws + "/SOUL.md") and not os.path.exists(ws + "/BOOTSTRAP.md") and "An" in open(ws + "/USER.md").read(), "workspace agent co SOUL/USER")
cfg = json.load(open(ENV["FAKE_OC_CFG"])); e = cfg["agents"]["entries"]["u_nv_1_a1b2c3d4"]
ok(e["sandbox"]["mode"] == "all" and "group:runtime" in e["tools"]["deny"], "agent moi: sandbox=all + deny nhom nguy hiem")

# ---- 5. co lap MCP giua agent ----
cfg["agents"]["entries"]["main"] = {"workspace": H + "/ws"}
for a in ("u_a_11111111", "u_b_22222222"): cfg["agents"]["entries"][a] = {"workspace": H + "/agents/" + a, "sandbox": {"mode": "all"}, "tools": {"deny": ["group:runtime"]}}
json.dump(cfg, open(ENV["FAKE_OC_CFG"], "w"))
os.makedirs(H + "/.config/agentweb/secrets", exist_ok=True)
for a, tk in (("u_a_11111111", "tokenAAAAAAAAAAAAAAAAAAAAA"), ("u_b_22222222", "tokenBBBBBBBBBBBBBBBBBBBBB")): open(H + f"/.config/agentweb/secrets/mcp_{a}.token", "w").write(tk)
G = H + "/openclaw-kit-agentweb/gan_mcp.py"
r = sh([sys.executable, G, "u_a_11111111", "doc,viet", "https://mcp.example.com/mcp"]); ok(r.stdout.startswith("OK"), "gan_mcp agent A", r.stdout + r.stderr)
r = sh([sys.executable, G, "u_b_22222222", "doc", "https://mcp.example.com/mcp"]); ok(r.stdout.startswith("OK"), "gan_mcp agent B", r.stdout + r.stderr)
r = sh([sys.executable, G, "--kiem"]); ok(r.stdout.startswith("OK"), "gan_mcp --kiem", r.stdout)
c = json.load(open(ENV["FAKE_OC_CFG"])); E = c["agents"]["entries"]
ok("cty_*" in E["main"]["tools"]["deny"], "agent khong sandbox (main) deny cty_*")
ok("cty_u_a_11111111__*" in E["u_b_22222222"]["tools"]["deny"] and "cty_u_b_22222222__*" in E["u_a_11111111"]["tools"]["deny"], "B deny server cua A va nguoc lai")
aa = E["u_a_11111111"]["tools"]["sandbox"]["tools"]["alsoAllow"]; ok(all(x.startswith("cty_u_a_11111111__") for x in aa) and len(aa) > 0, "A chi duoc tool server cua A", aa[:3])
cnt = int(sh([sys.executable, G, "--count", "doc,viet"]).stdout); ok(len(aa) == cnt, "so tool = profile (doc+viet)", (len(aa), cnt))
ok(c["mcp"]["servers"]["cty_u_a_11111111"]["headers"]["Authorization"] == "Bearer tokenAAAAAAAAAAAAAAAAAAAAA", "token A dung server A")
st = json.loads(sh([sys.executable, G, "--state"]).stdout); ok(st["tk"]["u_a_11111111"] and not st["thieu_deny"], "--state: token khop, du deny")
print("\n=== KET QUA:", "TAT CA PASS" if not bad else f"{bad} LOI", "(thu muc tam:", T + ")")
shutil.rmtree(T, ignore_errors=True) if not bad else None
sys.exit(1 if bad else 0)
