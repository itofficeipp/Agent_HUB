"""Đọc tham số tenant (params.json + secrets.env) cho các script agent-web. Chỉ stdlib."""
import json, os, subprocess, sys, urllib.request, urllib.parse
HOME = os.path.expanduser("~")
KIT_HOME = os.environ.get("KIT_HOME", HOME + "/.config/openclaw-kit")
TENANT = os.environ.get("KIT_TENANT", "")
if not TENANT:
    try: TENANT = open(KIT_HOME + "/current").read().strip()
    except OSError: sys.exit("LOI thieu KIT_TENANT")
TDIR = f"{KIT_HOME}/tenants/{TENANT}"
AWDIR = TDIR + "/agent-web"
DB = AWDIR + "/data/agent-web.db"   # kho cục bộ khi AW_BACKEND=local

def _load():
    c = json.load(open(TDIR + "/params.json"))
    try:
        for l in open(TDIR + "/secrets.env"):
            if "=" in l and not l.lstrip().startswith("#"):
                k, v = l.rstrip("\n").split("=", 1); c[k.strip()] = v.strip()
    except OSError: pass
    return c
C = _load()
# Nơi lưu hàng đợi: 'local' (SQLite cục bộ, receiver tích hợp) hoặc 'n8n' (Data table). Tenant cũ có AW_N8N_URL mà chưa có AW_BACKEND -> n8n.
BACKEND = C.get("AW_BACKEND") or ("n8n" if C.get("AW_N8N_URL") else "local")
def need(k):
    if not C.get(k): sys.exit(f"LOI thieu tham so {k} (kit enable agent-web)")
    return C[k]

# ---- n8n API (cần User-Agent kiểu curl: một số Cloudflare chặn urllib mặc định) ----
def n8n(method, path, body=None, timeout=60):
    req = urllib.request.Request(need("AW_N8N_URL").rstrip("/") + "/api/v1" + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"X-N8N-API-KEY": need("AW_N8N_API_KEY"), "Content-Type": "application/json", "User-Agent": "curl/8.5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        t = r.read().decode(); return json.loads(t) if t else {}
def table(which):
    """which: 'registry' | 'kenh' -> id bảng n8n hoặc tên bảng SQLite."""
    if BACKEND == "local": return {"registry": "agent_registry", "kenh": "agent_kenh"}[which]
    return need({"registry": "AW_REGISTRY_TABLE_ID", "kenh": "AW_CHANNEL_TABLE_ID"}[which])
_conn = None
def _local():
    global _conn
    if _conn is None:
        import store; _conn = store.connect(DB)
    return _conn
def flt(col, val): return {"type": "and", "filters": [{"columnName": col, "condition": "eq", "value": val}]}
def rows(table, col=None, val=None, limit=250):
    if BACKEND == "local":
        import store; return store.rows(_local(), table, col, val, limit)
    q = f"/data-tables/{table}/rows?limit={limit}"
    if col: q += "&filter=" + urllib.parse.quote(json.dumps(flt(col, val)))
    return n8n("GET", q)["data"]
def update(table, f, data):
    if BACKEND == "local":
        import store; return store.update(_local(), table, f, data)
    return n8n("PATCH", f"/data-tables/{table}/rows/update", {"filter": f, "data": data})

# ---- chạy lệnh trên máy Gateway: "local" hoặc user@host qua ssh ----
def gw(cmd, input=None, timeout=300):
    host = C.get("AW_GATEWAY_SSH", "local")
    if host == "local": argv = ["bash", "-c", cmd]
    else:
        argv = ["ssh", "-o", "BatchMode=yes"] + (["-i", os.path.expanduser(C["AW_GATEWAY_SSH_KEY"])] if C.get("AW_GATEWAY_SSH_KEY") else []) + [host, cmd]
    return subprocess.run(argv, input=input, capture_output=True, text=True, timeout=timeout)
