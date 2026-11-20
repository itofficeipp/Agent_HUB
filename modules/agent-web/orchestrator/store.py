#!/usr/bin/env python3
"""Kho dữ liệu cục bộ (SQLite) thay cho n8n Data table khi AW_BACKEND=local. Chỉ stdlib.
Hai bảng cùng cột với bản n8n: agent_registry, agent_kenh (+ replay: chống gửi lại cùng một yêu cầu đã ký).
Giao diện rows()/update() giống awconf để provision.py chạy y nguyên với cả hai nơi lưu."""
import os, sqlite3, time

COLS = {
    "agent_registry": ["user_id", "agent_id", "ho_ten", "email", "phong_ban", "gateway_id", "trang_thai", "ghi_chu"],
    "agent_kenh": ["user_id", "agent_id", "telegram_bot_username", "telegram_user_id", "mcp_url", "mcp_pham_vi",
                   "mcp_het_han", "bi_mat", "trang_thai", "cap_nhat_luc", "ghi_chu"],
}

def connect(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    new = not os.path.exists(path)
    c = sqlite3.connect(path, timeout=15, isolation_level=None)  # tự quản lý transaction
    if new: os.chmod(path, 0o600)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL"); c.execute("PRAGMA busy_timeout=15000")
    for t, cols in COLS.items():
        defs = ", ".join(f'"{k}" TEXT NOT NULL DEFAULT \'\'' + (" PRIMARY KEY" if k == "user_id" else "") for k in cols)
        c.execute(f'CREATE TABLE IF NOT EXISTS {t} ({defs})')
    c.execute("CREATE TABLE IF NOT EXISTS replay (khoa TEXT PRIMARY KEY, het_han INTEGER NOT NULL)")
    return c

def _where(flt):
    """flt kiểu n8n: {"type":"and","filters":[{"columnName":..,"condition":"eq","value":..}]}"""
    parts, args = [], []
    for f in (flt or {}).get("filters", []):
        if f.get("condition") != "eq": raise ValueError("chi ho tro dieu kien eq")
        col = f["columnName"]
        if not col.replace("_", "").isalnum(): raise ValueError("ten cot khong hop le")
        parts.append(f'"{col}" IS ?'); args.append("" if f.get("value") is None else str(f["value"]))
    return (" WHERE " + " AND ".join(parts)) if parts else "", args

def rows(c, table, col=None, val=None, limit=250):
    assert table in COLS
    w, a = _where({"filters": [{"columnName": col, "condition": "eq", "value": val}]}) if col else ("", [])
    return [dict(r) for r in c.execute(f"SELECT * FROM {table}{w} LIMIT ?", a + [int(limit)])]

def update(c, table, flt, data):
    assert table in COLS
    for k in data:
        if k not in COLS[table]: raise ValueError("cot khong ton tai: " + k)
    w, a = _where(flt)
    sets = ", ".join(f'"{k}" = ?' for k in data)
    cur = c.execute(f"UPDATE {table} SET {sets}{w}", [("" if v is None else str(v)) for v in data.values()] + a)
    return {"updatedCount": cur.rowcount}

def upsert(c, table, key_col, data):
    """Chèn mới hoặc cập nhật theo khoá user_id; trả True nếu là dòng mới."""
    assert table in COLS
    exists = c.execute(f"SELECT 1 FROM {table} WHERE {key_col} = ?", (data[key_col],)).fetchone()
    if exists:
        rest = {k: v for k, v in data.items() if k != key_col}
        if rest: update(c, table, {"filters": [{"columnName": key_col, "condition": "eq", "value": data[key_col]}]}, rest)
        return False
    ks = list(data)
    c.execute(f'INSERT INTO {table} ({", ".join(chr(34)+k+chr(34) for k in ks)}) VALUES ({", ".join("?" for _ in ks)})',
              [str(data[k]) for k in ks])
    return True

def claim_replay(c, key, ttl=600):
    """True nếu khoá chưa dùng (và ghi nhận); False nếu đã thấy trong cửa sổ ttl giây."""
    now = int(time.time())
    c.execute("DELETE FROM replay WHERE het_han < ?", (now,))
    cur = c.execute("INSERT OR IGNORE INTO replay (khoa, het_han) VALUES (?, ?)", (key, now + ttl))
    return cur.rowcount == 1
