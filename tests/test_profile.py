#!/usr/bin/env python3
"""Test Gateway OpenClaw RIÊNG theo tenant (kit init --oc-profile): công ty thứ hai trên cùng máy không đụng tenant cũ.
openclaw giả + systemctl giả + HOME tạm; KHÔNG chạm OpenClaw/dịch vụ thật. Chạy: python3 tests/test_profile.py"""
import json, os, re, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="kit-prof-"); H = T + "/home"; os.makedirs(H + "/bin")
shim = H + "/bin/openclaw"; open(shim, "w").write("#!/bin/sh\nexec python3 " + ROOT + "/tests/fake_openclaw.py \"$@\"\n"); os.chmod(shim, 0o755)
open(H + "/bin/systemctl", "w").write("#!/bin/sh\necho \"$@\" >> \"$FAKE_GW_LOG\"\ncase \"$2\" in is-active) [ \"$(cat \"$FAKE_GW_STATE\" 2>/dev/null)\" = active ];; stop) echo inactive > \"$FAKE_GW_STATE\";; start) echo active > \"$FAKE_GW_STATE\";; esac\nexit 0\n"); os.chmod(H + "/bin/systemctl", 0o755)
GWS, GWL, EL = H + "/gw.state", H + "/gw.log", H + "/env.log"
ENV = dict(os.environ, HOME=H, KIT_USER_HOME=H, KIT_HOME=T + "/cfg", OPENCLAW_BIN=shim, FAKE_OC_CFG=H + "/.openclaw/openclaw.json", FAKE_OC_ENVLOG=EL,
           FAKE_GW_STATE=GWS, FAKE_GW_LOG=GWL, KIT_NO_SYSTEMD="1", KIT_NO_PROBE="1", KIT_GW_WAIT="0", PATH=H + "/bin:" + os.environ["PATH"])
ENV.pop("OPENCLAW_PROFILE", None)
KIT = [sys.executable, ROOT + "/bin/kit"]; bad = 0
def ok(c, n, e=""):
    global bad; print(("PASS " if c else "FAIL ") + n + ("" if c else "  " + str(e)[:500])); bad += (not c)
def sh(a, inp=None, env=None): return subprocess.run(a, capture_output=True, text=True, input=inp, env=env or ENV)
def elog(): return [json.loads(l) for l in open(EL).read().splitlines() if l.strip()] if os.path.exists(EL) else []
U = H + "/.config/systemd/user"

# 1. tenant cũ (không profile): mọi thứ như trước
ok(sh(KIT + ["init", "d2d"]).returncode == 0, "init d2d (không profile)")
ok(not os.path.exists(T + "/cfg/tenants/d2d/oc.json"), "tenant cũ không có oc.json")
r = sh(KIT + ["enable", "base", "--yes", "--set", "COMPANY_NAME=D2D", "--set", "OWNER_NAME=A", "--set", "WORKSPACE_DIR=" + H + "/ws1"]); ok(r.returncode == 0, "enable base d2d", r.stderr)
r = sh(KIT + ["enable", "agent-web", "--yes", "--set", "AW_PUBLIC_URL=https://d2d.example.invalid", "--set", "AW_MCP_PROFILE=example", "--set", "AW_AGENT_ROOT=" + H + "/agents1"]); ok(r.returncode == 0, "enable agent-web d2d", r.stderr)
P1 = json.load(open(T + "/cfg/tenants/d2d/params.json"))
ok(P1["AW_LISTEN_PORT"] == "8787" and P1["AW_GATEWAY_DIR"] == "~/openclaw-kit-agentweb", "d2d: cổng 8787 + thư mục Gateway mặc định như cũ", P1)
r = sh(KIT + ["apply"]); ok(r.returncode == 0, "apply d2d", r.stdout[-400:] + r.stderr)
ok(os.path.exists(U + "/openclaw-kit-agentweb-receiver.service") and os.path.exists(U + "/openclaw-kit-agentweb-provision.timer"), "d2d: tên unit như cũ")
ok(all(e["profile"] is None for e in elog()) and all("/.openclaw/openclaw.json" in e["cfg"] for e in elog()), "d2d: openclaw chạy KHÔNG có profile (Gateway mặc định)", elog()[:2])
ok(os.path.exists(H + "/.config/agentweb/bi_mat.pem") is False and sh(KIT + ["run", "agent-web", "keygen"]).returncode == 0 and os.path.exists(H + "/.config/agentweb/bi_mat.pem"), "d2d: khoá ở ~/.config/agentweb như cũ")
d2d_units = sorted(os.listdir(U))

# 2. tenant IPP: kiểm tra đầu vào
r = sh(KIT + ["init", "ipp", "--oc-profile", "ipp"]); ok(r.returncode != 0 and "--oc-port" in r.stderr, "init: thiếu --oc-port -> từ chối", r.stderr)
r = sh(KIT + ["init", "ipp", "--oc-port", "19009"]); ok(r.returncode != 0, "init: --oc-port không kèm profile -> từ chối", r.stderr)
r = sh(KIT + ["init", "ipp", "--oc-profile", "main", "--oc-port", "19009"]); ok(r.returncode != 0 and "mặc định" in r.stderr, "init: profile 'main' bị chặn", r.stderr)
r = sh(KIT + ["init", "ipp", "--oc-profile", "ipp", "--oc-port", "18800"]); ok(r.returncode != 0 and "18789" in r.stderr, "init: cổng sát Gateway mặc định bị chặn", r.stderr)
ok(not os.path.exists(T + "/cfg/tenants/ipp"), "các ca lỗi không để lại thư mục tenant")
r = sh(KIT + ["init", "ipp", "--oc-profile", "ipp", "--oc-port", "19009"]); ok(r.returncode == 0, "init ipp --oc-profile ipp --oc-port 19009", r.stderr)
ok(json.load(open(T + "/cfg/tenants/ipp/oc.json")) == {"profile": "ipp", "port": 19009}, "oc.json đúng")
ok(open(T + "/cfg/current").read().strip() == "d2d", "tenant mặc định vẫn là d2d")
r = sh(KIT + ["init", "kkk", "--oc-profile", "ipp", "--oc-port", "19200"]); ok(r.returncode != 0 and "trùng" in r.stderr, "init: profile trùng tenant khác bị chặn", r.stderr)
r = sh(KIT + ["init", "kkk", "--oc-profile", "kkk", "--oc-port", "19050"]); ok(r.returncode != 0 and "trùng" in r.stderr, "init: cổng cách < 120 bị chặn", r.stderr)
ok(not os.path.exists(T + "/cfg/tenants/kkk"), "ca lỗi của kkk không để lại thư mục")

# 3. enable + apply IPP: tên/cổng/thư mục có hậu tố
r = sh(KIT + ["--tenant", "ipp", "enable", "base", "--yes", "--set", "COMPANY_NAME=IPP", "--set", "OWNER_NAME=B", "--set", "WORKSPACE_DIR=" + H + "/ws2"]); ok(r.returncode == 0, "enable base ipp", r.stderr)
r = sh(KIT + ["--tenant", "ipp", "enable", "agent-web", "--yes", "--set", "AW_PUBLIC_URL=https://ipp.example.invalid", "--set", "AW_MCP_PROFILE=example", "--set", "AW_AGENT_ROOT=" + H + "/agents2"]); ok(r.returncode == 0, "enable agent-web ipp", r.stderr)
P2 = json.load(open(T + "/cfg/tenants/ipp/params.json"))
ok(P2["AW_LISTEN_PORT"] == str(8787 + 19009 - 18789) and P2["AW_GATEWAY_DIR"] == "~/openclaw-kit-agentweb-ipp", "ipp: cổng receiver 9007 + thư mục Gateway có hậu tố", P2)
ok(P2["AW_LISTEN_PORT"] != P1["AW_LISTEN_PORT"], "ipp và d2d không trùng cổng receiver")
open(EL, "w").write("")
r = sh(KIT + ["--tenant", "ipp", "apply"]); ok(r.returncode == 0, "apply ipp", r.stdout[-500:] + r.stderr)
ok(os.path.exists(U + "/openclaw-kit-agentweb-ipp-receiver.service") and os.path.exists(U + "/openclaw-kit-agentweb-ipp-provision.timer"), "ipp: unit có hậu tố -ipp", os.listdir(U))
ok(all(os.path.exists(U + "/" + x) for x in d2d_units) and sorted(set(os.listdir(U)) & set(d2d_units)) == d2d_units, "unit của d2d vẫn còn nguyên")
rc = open(U + "/openclaw-kit-agentweb-ipp-receiver.service").read(); ok("KIT_TENANT=ipp" in rc and "tenants/ipp/" in rc and "{{" not in rc, "unit receiver ipp trỏ đúng tenant", rc)
E = elog(); ok(E and all(e["profile"] == "ipp" and e["port"] == "19009" and "/.openclaw-ipp/" in e["cfg"] for e in E), "ipp: MỌI lệnh openclaw chạy với profile ipp, cổng 19009, cấu hình .openclaw-ipp", E[:3])
ok(not os.path.exists(H + "/.openclaw/openclaw.json") or "ipp" not in open(H + "/.openclaw/openclaw.json").read(), "cấu hình mặc định (d2d) không bị ghi gì của ipp")

# 4. keygen/khoá, thư mục bí mật tách riêng
ok(sh(KIT + ["--tenant", "ipp", "run", "agent-web", "keygen"]).returncode == 0 and os.path.exists(H + "/.config/agentweb-ipp/bi_mat.pem"), "ipp: khoá ở ~/.config/agentweb-ipp")
ok(open(H + "/.config/agentweb/bi_mat.pem").read() != open(H + "/.config/agentweb-ipp/bi_mat.pem").read(), "khoá ipp khác khoá d2d")
ok(os.path.exists(H + "/openclaw-kit-agentweb-ipp/create_agent.sh") and os.path.exists(H + "/openclaw-kit-agentweb/create_agent.sh"), "script Gateway: mỗi tenant một thư mục")

# 5. gateway-install
r = sh(KIT + ["gateway-install", "--yes"]); ok(r.returncode != 0 and "Gateway mặc định" in r.stderr, "gateway-install tenant d2d -> từ chối (dùng Gateway mặc định)", r.stderr)
open(EL, "w").write("")
r = sh(KIT + ["--tenant", "ipp", "gateway-install", "--yes"]); ok(r.returncode == 0 and "openclaw-gateway-ipp" in r.stdout, "gateway-install ipp", r.stdout[-400:] + r.stderr)
E = elog(); inst = [e for e in E if e["argv"][:2] == ["gateway", "install"]]
ok(len(inst) == 1 and inst[0]["profile"] == "ipp" and inst[0]["argv"][-2:] == ["--port", "19009"], "gateway install --port 19009 với profile ipp", inst)
ok(not any(e["profile"] is None for e in E), "gateway-install không có lệnh nào chạy trên Gateway mặc định", E)
r = sh(KIT + ["--tenant", "ipp", "gateway-install"], inp="n\n"); ok(r.returncode != 0 or "chưa cài" in r.stderr + r.stdout, "gateway-install không có --yes mà không có terminal -> không cài", r.stdout[-200:])

# 6. model-backup nhắm đúng dịch vụ Gateway của tenant
open(GWS, "w").write("active\n"); open(GWL, "w").write("")
c = json.load(open(H + "/.openclaw-ipp/openclaw.json")); c["fake_profiles"] = ["anthropic:manual"]; json.dump(c, open(H + "/.openclaw-ipp/openclaw.json", "w"))
r = sh([sys.executable, ROOT + "/tests/../scripts/pty_feed.py", "--help"]) if False else None
import pty, select, time
def drive(argv, rules, env, tmo=60):
    pid, fd = pty.fork()
    if pid == 0: os.execvpe(argv[0], argv, env)
    out = seg = ""; t0 = time.time(); used = {}
    while time.time() - t0 < tmo:
        rr, _, _ = select.select([fd], [], [], 0.5)
        if rr:
            try: d = os.read(fd, 4096).decode("utf-8", "replace")
            except OSError: break
            if not d: break
            out += d; seg += d; continue
        if not seg.strip(): continue
        ans = ""; win = out[-1500:]; best, bi = -1, -1
        for i, (rx, lst) in enumerate(rules):
            for m in re.finditer(rx, win):
                if m.end() > best: best, bi = m.end(), i
        if bi >= 0:
            n = used.get(bi, 0)
            if n < len(rules[bi][1]): ans = rules[bi][1][n]; used[bi] = n + 1
        os.write(fd, (ans + "\n").encode()); seg = ""
    try: _, st = os.waitpid(pid, 0)
    except ChildProcessError: st = 0
    return (os.waitstatus_to_exitcode(st) if hasattr(os, "waitstatus_to_exitcode") else st), out
TOK = "sk" + "-ant-oat01-" + "A" * 60
rc, out = drive(KIT + ["--tenant", "ipp", "model-backup"], [(r"Dán token", [TOK])], ENV)
lg = open(GWL).read()
ok("is-active --quiet openclaw-gateway-ipp" in lg and "stop openclaw-gateway-ipp" in lg and "start openclaw-gateway-ipp" in lg, "model-backup ipp: dừng/bật dịch vụ openclaw-gateway-ipp", (lg, out[-400:]))
ok(not re.search(r"(stop|start|is-active)( --quiet)? openclaw-gateway(\s|$)", lg), "model-backup ipp: KHÔNG đụng dịch vụ Gateway mặc định", lg)
c = json.load(open(H + "/.openclaw-ipp/openclaw.json")); ok(len(c.get("fake_profiles", [])) == 2 and TOK not in out, "model-backup ipp: lưu vào .openclaw-ipp, token không lộ ra màn hình", c.get("fake_profiles"))
cm = json.load(open(H + "/.openclaw/openclaw.json")); ok("fake_profiles" not in cm or len(cm["fake_profiles"]) <= 1, "tài khoản của d2d không bị đụng", cm.get("fake_profiles"))

# 7. wrapper --profile (CLI thật KHÔNG tôn trọng biến OPENCLAW_PROFILE, chỉ cờ --profile) + doctor
W = T + "/cfg/tenants/ipp/bin/openclaw"
ok(os.path.exists(W) and os.access(W, os.X_OK) and "--profile ipp" in open(W).read(), "wrapper tenants/ipp/bin/openclaw = openclaw --profile ipp", open(W).read() if os.path.exists(W) else "thiếu")
ok(not os.path.exists(T + "/cfg/tenants/d2d/bin"), "tenant d2d không có wrapper (Gateway mặc định, không đổi)")
open(EL, "w").write("")
r = sh([W, "config", "get", "gateway.mode"], env=dict(ENV, OPENCLAW_BIN=shim)); E = elog()
ok(E and E[0]["profile"] == "ipp" and "/.openclaw-ipp/" in E[0]["cfg"], "chạy wrapper trực tiếp -> openclaw nhận --profile ipp", E)
open(EL, "w").write("")
r = sh(["openclaw", "config", "get", "gateway.mode"], env=dict(ENV, OPENCLAW_PROFILE="ipp")); E = elog()
ok(E and E[0]["profile"] is None and "/.openclaw/" in E[0]["cfg"], "chỉ đặt biến OPENCLAW_PROFILE (không có --profile) thì KHÔNG đổi Gateway (mô phỏng CLI thật)", E)
open(EL, "w").write("")
r = sh(KIT + ["--tenant", "ipp", "doctor"]); E = elog()
ok(E and any(e["argv"][:2] == ["config", "validate"] for e in E) and all(e["profile"] == "ipp" for e in E), "doctor ipp: mọi lệnh openclaw (kể cả config validate) nhắm profile ipp", E[:3])
open(EL, "w").write("")
r = sh(KIT + ["--tenant", "d2d", "doctor"]); E = elog()
ok(E and all(e["profile"] is None for e in E), "doctor d2d: vẫn Gateway mặc định, không --profile", E[:3])

print("\nTẤT CẢ PASS (0 lỗi)" if not bad else "\n%d LỖI" % bad); sys.exit(1 if bad else 0)
