#!/usr/bin/env python3
"""Test bot báo lỗi Telegram (kit alert-bot / alert-test / hỏi lúc enable, awconf.alert, provision_tick).
KHÔNG chạm Telegram thật: API Telegram giả chạy cục bộ (AW_TG_API). Chạy: python3 tests/test_alert.py"""
import http.server, json, os, pty, re, select, shutil, socket, subprocess, sys, tempfile, threading, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT + "/modules/agent-web/orchestrator")
T = tempfile.mkdtemp(prefix="kit-alert-"); H = T + "/home"; os.makedirs(H + "/bin")
shim = H + "/bin/openclaw"
open(shim, "w").write("#!/bin/sh\nexec python3 " + ROOT + "/tests/fake_openclaw.py \"$@\"\n"); os.chmod(shim, 0o755)
TOK = "123456789:" + "A" * 35        # token giả đúng định dạng
BAD = "987654321:" + "B" * 35        # token giả bị Telegram từ chối (401)
SENT, STATE = [], {"fail403": False}
class Fake(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _j(self, code, o):
        b = json.dumps(o).encode(); self.send_response(code); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b)
    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0); body = json.loads(self.rfile.read(n) or b"{}")
        m = re.fullmatch(r"/bot([^/]+)/(\w+)", self.path)
        if not m: return self._j(404, {"ok": False})
        tok, meth = m.groups()
        if tok != TOK: return self._j(401, {"ok": False, "error_code": 401, "description": "Unauthorized"})
        if meth == "getMe": return self._j(200, {"ok": True, "result": {"username": "kit_alert_bot"}})
        if meth == "sendMessage":
            if STATE["fail403"] or body.get("chat_id") == "222222":
                return self._j(403, {"ok": False, "error_code": 403, "description": "Forbidden: bot can't initiate conversation with a user"})
            if body.get("chat_id") == "333333":
                return self._j(400, {"ok": False, "error_code": 400, "description": "Bad Request: chat not found"})
            SENT.append(body); return self._j(200, {"ok": True, "result": {"message_id": len(SENT)}})
        self._j(404, {"ok": False})
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Fake); threading.Thread(target=srv.serve_forever, daemon=True).start()
API = "http://127.0.0.1:%d" % PORT
os.environ["AW_TG_API"] = API
ENV = dict(os.environ, HOME=H, KIT_USER_HOME=H, KIT_HOME=T + "/cfg", OPENCLAW_BIN=shim, FAKE_OC_CFG=H + "/.openclaw/openclaw.json",
           KIT_NO_SYSTEMD="1", AW_TG_API=API, PATH=H + "/bin:" + os.environ["PATH"])
ENV.pop("KIT_NO_PROBE", None)
KIT = [sys.executable, ROOT + "/bin/kit"]
bad = 0
def ok(cond, name, extra=""):
    global bad; print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  " + str(extra)[:500])); bad += (not cond)
def sh(argv, env=None, inp=None): return subprocess.run(argv, capture_output=True, text=True, env=env or ENV, input=inp)

def drive(argv, rules, env, tmo=60):
    """Chạy trong pty; rules [(regex, [câu trả lời lần lượt])]; chưa khớp = Enter."""
    pid, fd = pty.fork()
    if pid == 0: os.execvpe(argv[0], argv, env)
    out = seg = ""; t0 = time.time(); used = {}
    while time.time() - t0 < tmo:
        r, _, _ = select.select([fd], [], [], 0.5)
        if r:
            try: d = os.read(fd, 4096).decode("utf-8", "replace")
            except OSError: break
            if not d: break
            out += d; seg += d; continue
        if not seg.strip(): continue
        ans = ""; win = out[-1500:]; best, bi = -1, -1
        for i, (rx, lst) in enumerate(rules):   # chọn câu hỏi xuất hiện MUỘN nhất = câu đang chờ trả lời
            for m in re.finditer(rx, win): 
                if m.end() > best: best, bi = m.end(), i
        if bi >= 0:
            n = used.get(bi, 0)
            if n < len(rules[bi][1]): ans = rules[bi][1][n]; used[bi] = n + 1
        os.write(fd, (ans + "\n").encode()); seg = ""
    try: _, st = os.waitpid(pid, 0)
    except ChildProcessError: st = 0
    return os.waitstatus_to_exitcode(st), out

import tgalert
# ---- 1. tgalert trực tiếp ----
ok(tgalert.get_me(TOK) == (True, "kit_alert_bot"), "get_me: token đúng -> username")
r = tgalert.get_me(BAD); ok(r[0] is False and "từ chối token" in r[1] and "BBBB" not in r[1], "get_me: 401 -> báo token sai, không lộ token", r)
r = tgalert.get_me("abc"); ok(r[0] is False and "sai định dạng" in r[1], "get_me: token sai dạng bị chặn ngay", r)
ok(tgalert.send(TOK, "111111", "xin chào")[0] is True and SENT[-1]["text"] == "xin chào" and SENT[-1]["chat_id"] == "111111", "send: gửi được, đúng nội dung/ID")
r = tgalert.send(TOK, "222222", "x"); ok(r[0] is False and "Start" in r[1], "send: 403 -> hướng dẫn bấm Start", r)
r = tgalert.send(TOK, "333333", "x"); ok(r[0] is False and "ID" in r[1] and "userinfobot" in r[1], "send: chat not found -> hướng dẫn lấy ID", r)
r = tgalert.send(TOK, "abc", "x"); ok(r[0] is False and "dãy số" in r[1] or "là số" in r[1], "send: ID không phải số bị chặn", r)
os.environ["AW_TG_API"] = "http://127.0.0.1:1"; r = tgalert.send(TOK, "111111", "x"); os.environ["AW_TG_API"] = API
ok(r[0] is False and "không nối được" in r[1] and TOK not in r[1], "send: mất mạng -> báo rõ, không lộ token", r)
n0 = len(SENT); tgalert.send(TOK, "111111", "a" * 9000); ok(len(SENT[-1]["text"]) <= 3500 and len(SENT) == n0 + 1, "send: cắt tin quá dài")

# ---- 2. kit alert-bot (pty): nhập ẩn, lưu 600, gửi thử ----
ok(sh(KIT + ["init", "ta"]).returncode == 0, "kit init ta")
n0 = len(SENT)
rc, out = drive(KIT + ["--tenant", "ta", "alert-bot"], [(r"ID Telegram người nhận", ["111111"]), (r"Token bot", [TOK])], ENV)
ok(rc == 0 and "ĐÃ GỬI được tin thử" in out, "alert-bot: rc=0 và gửi được tin thử", out[-500:])
ok(len(SENT) == n0 + 1 and "kit" in SENT[-1]["text"] and SENT[-1]["chat_id"] == "111111", "alert-bot: tin thử tới đúng ID", SENT[-1:])
ok(TOK not in out and "AAAAAAAAAA" not in out, "alert-bot: token KHÔNG hiện trên màn hình")
sp = T + "/cfg/tenants/ta/secrets.env"
ok(os.path.exists(sp) and oct(os.stat(sp).st_mode & 0o777) == "0o600" and ("AW_ALERT_BOT_TOKEN=" + TOK) in open(sp).read(), "alert-bot: token lưu secrets.env chmod 600")
P = json.load(open(T + "/cfg/tenants/ta/params.json")); ok(P.get("AW_ALERT_TARGET") == "111111" and "AW_ALERT_BOT_TOKEN" not in P and TOK not in json.dumps(P), "alert-bot: ID lưu params, token KHÔNG vào params.json", P)
r = sh(KIT + ["--tenant", "ta", "alert-bot"], inp=""); ok(r.returncode != 0 and "terminal" in r.stderr, "alert-bot: không có terminal -> từ chối (không nhận token qua stdin/tham số)", r.stderr)

# ---- 3. alert-test ----
n0 = len(SENT); r = sh(KIT + ["--tenant", "ta", "alert-test"]); ok(r.returncode == 0 and len(SENT) == n0 + 1 and "OK đã gửi" in r.stdout, "alert-test: gửi được, rc=0", r.stdout + r.stderr)
STATE["fail403"] = True; r = sh(KIT + ["--tenant", "ta", "alert-test"]); STATE["fail403"] = False
ok(r.returncode == 1 and "Start" in r.stdout and TOK not in r.stdout + r.stderr, "alert-test: người nhận chưa Start -> rc=1 + hướng dẫn", r.stdout)
sh(KIT + ["init", "tb"]); r = sh(KIT + ["--tenant", "tb", "alert-test"]); ok(r.returncode != 0 and "alert-bot" in r.stderr, "alert-test: chưa cấu hình -> chỉ cách làm", r.stderr)

# ---- 4. alert-bot khi người nhận chưa Start: báo rõ, cho thử lại/bỏ qua, vẫn lưu ----
n0 = len(SENT)
rc, out = drive(KIT + ["--tenant", "tb", "alert-bot"], [(r"ID Telegram người nhận", ["222222"]), (r"Token bot", [TOK]), (r"Enter = thử lại", ["bo"])], ENV)
ok(rc == 1 and "Start" in out and "CHƯA gửi được" in out and len(SENT) == n0, "alert-bot: 403 -> hướng dẫn Start, rc=1, không gửi", out[-500:])
ok(json.load(open(T + "/cfg/tenants/tb/params.json")).get("AW_ALERT_TARGET") == "222222", "alert-bot: vẫn lưu cấu hình khi gửi thử lỗi")
rc, out = drive(KIT + ["--tenant", "tb", "alert-bot"], [(r"ID Telegram người nhận", ["abc", "444444"]), (r"Token bot", ["sai", BAD]), (r"Enter = thử lại", ["bo"])], ENV)
ok("phải là một dãy số" in out and "token có dạng" in out, "alert-bot: ID/token sai định dạng -> nhập lại", out[-600:])
ok(("401" not in out) and "từ chối token" in out and "AAAAAA" not in out, "alert-bot: token bị Telegram từ chối -> nói rõ", out[-500:])

# ---- 5. hỏi lúc enable agent-web: ID -> token (ẩn) -> gửi thử ----
pf = T + "/pf.json"; json.dump({"AW_LISTEN_PORT": "18787", "AW_PUBLIC_URL": "https://a.example.invalid", "AW_MCP_PROFILE": "example", "AW_AGENT_ROOT": H + "/agents"}, open(pf, "w"))
sh(KIT + ["init", "tc"]); sh(KIT + ["--tenant", "tc", "enable", "base", "--yes", "--set", "COMPANY_NAME=C", "--set", "OWNER_NAME=O", "--set", "WORKSPACE_DIR=" + H + "/ws"])
n0 = len(SENT)
rc, out = drive(KIT + ["--tenant", "tc", "enable", "agent-web", "--params-file", pf], [(r"ID Telegram người nhận báo lỗi", ["111111"]), (r"Token bot Telegram dùng để GỬI", [TOK])], ENV)
ok(rc == 0 and "OK token thuộc bot @kit_alert_bot" in out and "OK đã gửi tin thử tới ID 111111" in out and len(SENT) == n0 + 1, "enable: hỏi ID rồi token, tự gửi thử", out[-700:])
ok(TOK not in out, "enable: token không hiện trên màn hình")
rc, out = drive(KIT + ["--tenant", "tc", "enable", "agent-web", "--params-file", pf], [], ENV)
ok("Token bot Telegram dùng để GỬI" not in out and "ID Telegram người nhận" not in out, "enable lần 2: không hỏi lại (đã có)", out[-300:])
sh(KIT + ["init", "td"]); sh(KIT + ["--tenant", "td", "enable", "base", "--yes", "--set", "COMPANY_NAME=C", "--set", "OWNER_NAME=O", "--set", "WORKSPACE_DIR=" + H + "/ws"])
rc, out = drive(KIT + ["--tenant", "td", "enable", "agent-web", "--params-file", pf], [], ENV)
ok("Token bot Telegram dùng để GỬI" not in out, "enable: bỏ trống ID -> không hỏi token", out[-300:])
d = sh(KIT + ["--tenant", "td", "enable", "agent-web", "--yes", "--set", "AW_ALERT_TARGET=abc"]); ok(d.returncode != 0 and "AW_ALERT_TARGET" in d.stderr, "ID không phải số bị chặn khi --yes", d.stderr)

# ---- 6. doctor ----
def doc(t): return sh(KIT + ["--tenant", t, "doctor"]).stdout
ok("báo lỗi Telegram đã cấu hình" in doc("tc"), "doctor: có token + ID -> OK")
ok("KHÔNG có tin nhắn" in doc("td"), "doctor: thiếu ID -> cảnh báo rõ")

# ---- 7. awconf.alert + provision_tick (lỗi mới thì báo; gửi lỗi thì thử lại; đã báo thì im) ----
OD = T + "/orch"; shutil.copytree(ROOT + "/modules/agent-web/orchestrator", OD)
open(OD + "/provision.py", "w").write("print('LOI tao agent u_x: sandbox hong')\nraise SystemExit(1)\n")
tdir = T + "/cfg/tenants/tc"
H2 = T + "/h2"; os.makedirs(H2)
E2 = dict(ENV, HOME=H2, KIT_TENANT="tc", KIT_HOME=T + "/cfg", PYTHONPATH=OD)
def tick(): return subprocess.run([sys.executable, OD + "/provision_tick.py"], capture_output=True, text=True, env=E2, cwd=OD)
LG = H2 + "/.local/state/openclaw-kit-agentweb/loi_su_kien.log"
n0 = len(SENT); STATE["fail403"] = True; r = tick(); STATE["fail403"] = False
ok(r.returncode == 0 and len(SENT) == n0, "tick 1 (Telegram từ chối): không gửi được", r.stderr[-300:])
ok(os.path.exists(LG) and "canh_bao_khong_gui_duoc" in open(LG).read() and "Start" in open(LG).read(), "tick 1: ghi log rõ 'cảnh báo không gửi được'", open(LG).read() if os.path.exists(LG) else "no log")
n1 = len(open(LG).read().splitlines()); STATE["fail403"] = True; tick(); STATE["fail403"] = False
ok(len(open(LG).read().splitlines()) == n1, "tick 2 (vẫn lỗi gửi): không ghi log lặp")
r = tick(); ok(len(SENT) == n0 + 1 and "sandbox hong" in SENT[-1]["text"] and "tc" in SENT[-1]["text"], "tick 3 (gửi được lại): báo đúng nội dung lỗi", SENT[-1:])
tick(); ok(len(SENT) == n0 + 1, "tick 4: lỗi đã báo thì im lặng")
open(OD + "/provision.py", "w").write("print('LOI tao agent u_y: het dung luong')\nraise SystemExit(1)\n"); tick()
ok(len(SENT) == n0 + 2 and "het dung luong" in SENT[-1]["text"], "tick 5: lỗi MỚI thì báo tiếp")
open(OD + "/provision.py", "w").write("raise SystemExit(0)\n"); tick(); open(OD + "/provision.py", "w").write("print('LOI tao agent u_y: het dung luong')\nraise SystemExit(1)\n"); tick()
ok(len(SENT) == n0 + 3, "tick 6: hết lỗi rồi lỗi lại -> báo lại")
# không token: dự phòng openclaw message send (giả) nhưng vẫn không crash
ok("openclaw" in open(OD + "/awconf.py").read(), "awconf: có đường dự phòng openclaw message send")
c = subprocess.run([sys.executable, "-c", "import awconf as A; print(A.alert('xin chao', target='111111'))"], capture_output=True, text=True, env=E2, cwd=OD)
ok("True" in c.stdout and SENT[-1]["text"] == "xin chao", "awconf.alert: gửi qua bot báo lỗi", c.stdout + c.stderr)

print("\n%s (%d lỗi)" % ("TẤT CẢ PASS" if not bad else "CÓ LỖI", bad)); shutil.rmtree(T, ignore_errors=True); sys.exit(1 if bad else 0)
