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
a = sys.argv[1:]
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
elif a[:2] == ["config", "validate"]: print("ok" + ("\n2 warning(s):\n  ! plugins.entries.duckduckgo: plugin not installed: duckduckgo" if os.environ.get("FAKE_OC_WARN") else ""))
elif a[:2] == ["agents", "list"]: print(json.dumps([{"id": k} for k in (load().get("agents") or {}).get("entries", {})]))
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
