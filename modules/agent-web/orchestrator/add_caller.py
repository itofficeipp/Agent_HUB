#!/usr/bin/env python3
"""Tạo/đổi thông tin 'bên gọi' webhook (hệ thống web/HRM được phép gọi). Lưu băm mật khẩu + secret HMAC vào
<tenant>/agent-web/users.json (chmod 600). GHI mật khẩu và secret HMAC vào file riêng (chmod 600, thư mục 700) để đưa cho bên gọi, KHÔNG in ra màn hình (tránh lộ khi chụp màn hình/ghi log). kit không giữ bản rõ của mật khẩu trong users.json.
Dùng: add_caller.py <ten> [--hmac bat_buoc|tuy_chon] [--print]   (--print: in ra màn hình như cũ, không ghi file)"""
import argparse, hashlib, json, os, secrets
import awconf as A
ap = argparse.ArgumentParser(); ap.add_argument("name"); ap.add_argument("--hmac", default="bat_buoc", choices=["bat_buoc", "tuy_chon"]); ap.add_argument("--print", dest="show", action="store_true"); o = ap.parse_args()
assert o.name.replace("_", "").replace("-", "").isalnum(), "ten chi gom chu/so/_/-"
os.makedirs(A.AWDIR, exist_ok=True); p = A.AWDIR + "/users.json"
U = json.load(open(p)) if os.path.exists(p) else {"salt": secrets.token_hex(16), "users": {}}
pw, sec = secrets.token_urlsafe(24), secrets.token_hex(32)
U["users"][o.name] = {"h": hashlib.sha256((U["salt"] + ":" + pw).encode()).hexdigest(), "hmac": o.hmac, "secret": sec}
fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w") as f: json.dump(U, f, indent=1)
body = f"user      = {o.name}\npassword  = {pw}\nhmac_key  = {sec}\n"
if o.show:
    print(f"Bên gọi '{o.name}' (HMAC {o.hmac}). LƯU NGAY, sẽ không in lại:\n  " + body.replace("\n", "\n  ").rstrip())
else:
    sd = A.AWDIR + "/secrets"; os.makedirs(sd, mode=0o700, exist_ok=True); os.chmod(sd, 0o700)
    sp = f"{sd}/caller-{o.name}.txt"
    fd = os.open(sp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f: f.write(body)
    print(f"Bên gọi '{o.name}' (HMAC {o.hmac}) đã tạo. Mật khẩu và HMAC key KHÔNG in ra màn hình, đã ghi vào file (chỉ chủ máy đọc được):\n  {sp}\n"
          f"Đưa cho bên gọi qua kênh an toàn (không chat/email), rồi xoá file: shred -u {sp}")
print("Rồi chạy: kit run agent-web deploy-workflow   (để n8n nhận bên gọi mới)" if A.BACKEND == "n8n" else
      "Receiver tự đọc lại users.json, không cần khởi động lại.")
