#!/usr/bin/env python3
"""Tạo/đổi thông tin 'bên gọi' webhook (hệ thống web/HRM được phép gọi). Lưu băm mật khẩu + secret HMAC vào
<tenant>/agent-web/users.json (chmod 600). IN 1 LẦN mật khẩu và secret HMAC để đưa cho bên gọi — kit không giữ bản rõ của mật khẩu.
Dùng: add_caller.py <ten> [--hmac bat_buoc|tuy_chon]"""
import argparse, hashlib, json, os, secrets
import awconf as A
ap = argparse.ArgumentParser(); ap.add_argument("name"); ap.add_argument("--hmac", default="bat_buoc", choices=["bat_buoc", "tuy_chon"]); o = ap.parse_args()
assert o.name.replace("_", "").replace("-", "").isalnum(), "ten chi gom chu/so/_/-"
os.makedirs(A.AWDIR, exist_ok=True); p = A.AWDIR + "/users.json"
U = json.load(open(p)) if os.path.exists(p) else {"salt": secrets.token_hex(16), "users": {}}
pw, sec = secrets.token_urlsafe(24), secrets.token_hex(32)
U["users"][o.name] = {"h": hashlib.sha256((U["salt"] + ":" + pw).encode()).hexdigest(), "hmac": o.hmac, "secret": sec}
fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w") as f: json.dump(U, f, indent=1)
print(f"Bên gọi '{o.name}' (HMAC {o.hmac}). LƯU NGAY, sẽ không in lại:\n  user      = {o.name}\n  password  = {pw}\n  hmac_key  = {sec}")
print("Rồi chạy: kit run agent-web deploy-workflow   (để n8n nhận bên gọi mới)" if A.BACKEND == "n8n" else
      "Receiver tự đọc lại users.json, không cần khởi động lại.")
