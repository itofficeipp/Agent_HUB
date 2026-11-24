#!/usr/bin/env python3
"""openclaw giả cho test (KHÔNG chạm OpenClaw thật). Cấu hình ở $FAKE_OC_CFG. Chỉ hỗ trợ đúng các lệnh kit/agent-web dùng."""
import json, os, sys
CFG = os.environ["FAKE_OC_CFG"]
load = lambda: json.load(open(CFG)) if os.path.exists(CFG) else {}
def save(c):
    os.makedirs(os.path.dirname(CFG), exist_ok=True); json.dump(c, open(CFG, "w"), indent=1)
def merge(a, b):
    for k, v in b.items():
        if v is None: a.pop(k, None)
        elif isinstance(v, dict) and isinstance(a.get(k), dict): merge(a[k], v)
        else: a[k] = v
def need_offline():
    st = os.environ.get("FAKE_GW_STATE")
    if st and os.path.exists(st) and open(st).read().strip() == "active":
        print("Cannot admit models.auth for system/agent credentials in state root: This operation requires exclusive offline state ownership. No local mutation was attempted.", file=sys.stderr); sys.exit(1)
def opt(a, k, d=None): return a[a.index(k) + 1] if k in a else d
a = sys.argv[1:]
if os.environ.get("FAKE_OC_ARGV"): open(os.environ["FAKE_OC_ARGV"], "a").write(json.dumps(a) + "\n")
if a[:1] == ["--version"]: print("OpenClaw 0.0.0-fake")
elif a[:2] == ["config", "set"]:
    c = load(); d = c; ks = a[2].split(".")
    for k in ks[:-1]: d = d.setdefault(k, {})
    d[ks[-1]] = json.loads(a[3]); save(c)
elif a[:2] == ["config", "patch"]:
    p = json.loads(sys.stdin.read())
    if "--dry-run" not in a: c = load(); merge(c, p); save(c)
elif a[:2] == ["config", "get"]:
    c = load(); v = c
    for k in a[2].split("."):
        v = v.get(k) if isinstance(v, dict) else None
    if v is None: print(json.dumps({"ok": False})); sys.exit(1)
    print(json.dumps(v))
elif a[:2] == ["config", "unset"]:
    c = load(); d = c; ks = a[2].split(".")
    for k in ks[:-1]: d = d.get(k) or {}
    d.pop(ks[-1], None); save(c)
elif a[:2] == ["models", "status"]:
    # agent có credential nếu nằm trong cfg["fake_auth"] (list); thừa hưởng được mô phỏng ở phía kit, không ở đây
    ag = a[a.index("--agent") + 1] if "--agent" in a else "main"
    sys.exit(0 if ag in (load().get("fake_auth") or []) else 1)
elif a[:3] == ["models", "auth", "list"]:
    prov = opt(a, "--provider"); print("Agent: " + opt(a, "--agent", "main") + "\nAuth state store: ~/.openclaw/state/openclaw.sqlite\nProfiles:")
    for pid in (load().get("fake_profiles") or []):
        if not prov or pid.startswith(prov + ":"): print("- %s [anthropic/token; expires 2027-11-24T10:32:34.027Z]" % pid)
elif a[:3] == ["models", "auth", "paste-token"]:
    need_offline(); prov = opt(a, "--provider")
    if os.environ.get("FAKE_PASTE_FAIL"): print("boom: khong luu duoc", file=sys.stderr); sys.exit(1)
    print("Paste token for " + prov); sys.stdout.flush(); tok = sys.stdin.readline().strip()
    if not tok.startswith("sk-ant-oat01-"): print("Expected token starting with sk-ant-oat01-"); sys.exit(1)
    pid = opt(a, "--profile-id", prov + ":manual"); c = load(); lst = c.setdefault("fake_profiles", [])
    if pid not in lst: lst.append(pid)
    c.setdefault("fake_token_len", {})[pid] = len(tok); save(c); print("Auth profile: " + pid + " (anthropic/token)")
elif a[:4] == ["models", "auth", "order", "get"]:
    need_offline(); o = (load().get("fake_order") or {}).get(opt(a, "--provider")) or []
    print("Agent: main\nProvider: anthropic\n" + ("Auth profile order override: " + ", ".join(o) if o else "No auth profile order override"))
elif a[:4] == ["models", "auth", "order", "set"]:
    need_offline(); rest = a[4:]; ids = []; i = 0
    while i < len(rest):
        if rest[i].startswith("--"): i += 2
        else: ids.append(rest[i]); i += 1
    c = load(); c.setdefault("fake_order", {})[opt(a, "--provider")] = ids; save(c); print("Auth profile order override: " + ", ".join(ids))
elif a[:2] == ["config", "validate"]: print("ok" + ("\n2 warning(s):\n  ! plugins.entries.duckduckgo: plugin not installed: duckduckgo" if os.environ.get("FAKE_OC_WARN") else ""))
elif a[:2] == ["agents", "list"]:
    ents = list(((load().get("agents") or {}).get("entries") or {}))
    dflt = ((load().get("agents") or {}).get("default")) or ("main" if "main" in ents else (ents[0] if ents else None))
    print(json.dumps([{"id": k, "isDefault": k == dflt} for k in ents]))
elif a[:2] == ["agents", "bind"]:
    ag = a[a.index("--agent") + 1] if "--agent" in a else "main"; bd = a[a.index("--bind") + 1]
    c = load(); lst = c.setdefault("bindings", []); ch, _, acc = bd.partition(":")
    ent = {"agentId": ag, "match": {"channel": ch, "accountId": acc or "default"}}
    if ent in lst: print("No bindings added (already bound)")
    else: lst.append(ent); save(c); print("Added bindings")
elif a[:2] == ["agents", "set-identity"]:
    ag = a[a.index("--agent") + 1]; c = load()
    c.setdefault("agents", {}).setdefault("entries", {}).setdefault(ag, {}).setdefault("identity", {})["name"] = a[a.index("--name") + 1]; save(c); print("Updated")
elif a[:2] == ["agents", "add"]:
    ws = a[a.index("--workspace") + 1]; os.makedirs(ws, exist_ok=True)
    open(ws + "/BOOTSTRAP.md", "w").write("x"); c = load(); c.setdefault("agents", {}).setdefault("entries", {})[a[2]] = {"workspace": ws}; save(c); print("{}")
elif a[:2] == ["sandbox", "explain"]:
    e = load()["agents"]["entries"][a[a.index("--agent") + 1]]
    print("runtime: sandboxed" if (e.get("sandbox") or {}).get("mode") == "all" else "runtime: host")
elif a[:2] == ["message", "send"]:
    open(os.environ.get("FAKE_OC_LOG", "/dev/null"), "a").write(json.dumps(a) + "\n"); print("sent")
elif a[:2] == ["gateway", "usage-cost"]:
    import datetime
    ag = a[a.index("--agent") + 1]; n = int(a[a.index("--days") + 1]); k = (sum(map(ord, ag)) % 7) + 1
    today = datetime.date.today()
    print(json.dumps({"days": n, "daily": [{"date": (today - datetime.timedelta(days=i)).isoformat(), "input": 100 * k, "output": 50 * k, "cacheRead": 10, "cacheWrite": 0,
        "totalTokens": 160 * k, "totalCost": 0.01 * k} for i in range(n - 1, -1, -1)]}))
else: print("fake openclaw: lenh chua ho tro:", a, file=sys.stderr); sys.exit(2)
