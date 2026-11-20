#!/usr/bin/env python3
"""Thử webhook (ký HMAC đúng như hệ thống gọi thật). Dùng: test_webhook.py --user U --password P --secret S [--ts-offset N]
Chạy các ca: tạo mới, gọi lại, sai chữ ký, timestamp cũ, thiếu ho_ten, user_id sai, không chữ ký. User thử TEST-kit-01 (xoá khỏi bảng sau khi thử)."""
import argparse, base64, hashlib, hmac, json, time, urllib.request, urllib.error
import awconf as A
ap = argparse.ArgumentParser(); ap.add_argument("--user", required=True); ap.add_argument("--password", required=True); ap.add_argument("--secret", required=True)
ap.add_argument("--base", help="địa chỉ gốc để thử (mặc định: receiver 127.0.0.1:cổng, hoặc AW_N8N_URL); đặt = AW_PUBLIC_URL để thử đường công khai")
o = ap.parse_args()
BASE = o.base or (A.need("AW_N8N_URL") if A.BACKEND == "n8n" else f"http://127.0.0.1:{A.C.get('AW_LISTEN_PORT') or 8787}")
URL = BASE.rstrip("/") + "/webhook/" + A.need("AW_WEBHOOK_PATH")
def call(label, body, ts=None, secret=None, sign=True):
    raw = json.dumps(body, ensure_ascii=False).encode(); ts = str(ts or int(time.time()))
    h = {"Content-Type": "application/json", "User-Agent": "curl/8.5.0",
         "Authorization": "Basic " + base64.b64encode(f"{o.user}:{o.password}".encode()).decode()}
    if sign:
        h["X-Timestamp"] = ts; h["X-Signature"] = "sha256=" + hmac.new((secret or o.secret).encode(), ts.encode() + b"." + raw, hashlib.sha256).hexdigest()
    try: r = urllib.request.urlopen(urllib.request.Request(URL, raw, h, method="POST"), timeout=60); code, txt = r.status, r.read().decode()
    except urllib.error.HTTPError as e: code, txt = e.code, e.read().decode()
    print(f"[{label}] HTTP {code} {txt[:160]}")
B = {"user_id": "TEST-kit-01", "ho_ten": "Nguoi Thu Mot", "email": "test01@example.com", "phong_ban": "IT"}
call("tao moi (ky vong 201)", B, ts=int(time.time()) - 1); call("goi lai (ky vong 200)", B)
if A.BACKEND == "local": call("gui lai y het yeu cau da ky (ky vong 409 - chong replay)", B, ts=int(time.time()) - 1)
call("sai secret (401)", B, secret="sai"); call("timestamp cu (401)", B, ts=int(time.time()) - 600)
call("thieu ho_ten (422)", {"user_id": "TEST-kit-02"}); call("user_id sai (422)", {"user_id": "a b c", "ho_ten": "X"})
call("khong chu ky (401 neu HMAC bat buoc)", B, sign=False)
