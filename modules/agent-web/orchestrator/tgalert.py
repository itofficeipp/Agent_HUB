"""Gửi tin báo lỗi qua bot Telegram TRỰC TIẾP bằng Bot API (không qua OpenClaw Gateway), chỉ stdlib.

Vì sao trực tiếp: cảnh báo phải tới được ngay cả khi Gateway/OpenClaw đang hỏng. Phần GỬI của kit không nhận tin. Từ 0.3.13 kit còn dùng cùng token làm bot chat của agent tổng
(channels.telegram, chỉ ID người nhận được nhắn - allowlist), nhưng việc nhận tin do Gateway lo, không phải file này.
Token không bao giờ được in ra hay đưa vào thông báo lỗi. AW_TG_API đổi địa chỉ API (dùng cho thử nghiệm).
"""
import json, os, re, urllib.error, urllib.request

TOKEN_RE = r"[0-9]{6,12}:[A-Za-z0-9_-]{30,60}"
CHAT_RE = r"-?[0-9]{5,15}"
API = lambda: os.environ.get("AW_TG_API", "https://api.telegram.org").rstrip("/")

def _call(token, method, body=None, timeout=20):
    """Trả (đã_gọi_được_API, dict_json hoặc {}, mô_tả_lỗi_mạng)."""
    req = urllib.request.Request(f"{API()}/bot{token}/{method}", method="POST",
        data=json.dumps(body or {}).encode(), headers={"Content-Type": "application/json", "User-Agent": "curl/8.5.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: return True, json.loads(r.read().decode() or "{}"), ""
    except urllib.error.HTTPError as e:   # Telegram trả mã lỗi kèm JSON mô tả
        try: return True, json.loads(e.read().decode() or "{}"), ""
        except Exception: return True, {"ok": False, "error_code": e.code, "description": "HTTP %s" % e.code}, ""
    except Exception as e:                # mạng/DNS/timeout. str(e) của urllib không chứa URL (có token) nên an toàn; cắt ngắn cho chắc
        return False, {}, re.sub(TOKEN_RE, "***", str(e))[:120]

def explain(res, net_err=""):
    """Giải thích lỗi bằng tiếng Việt, nói rõ cách sửa."""
    if net_err: return "không nối được tới Telegram (%s). Kiểm Internet/DNS/firewall của máy này." % net_err
    code, desc = res.get("error_code"), (res.get("description") or "").lower()
    if code == 401: return "Telegram từ chối token (sai hoặc đã bị thu hồi). Lấy token mới ở @BotFather (/token) rồi nhập lại."
    if code == 403: return "bot không nhắn được cho ID này: người nhận chưa bấm Start với bot. Mở bot trong Telegram, bấm Start hoặc gửi 1 tin bất kỳ, rồi thử lại."
    if code == 400 and "chat not found" in desc: return "không thấy ID nhận tin (sai ID, hoặc người đó chưa nhắn bot lần nào). Lấy ID thật từ @userinfobot, rồi bấm Start với bot."
    if code == 429: return "Telegram báo gửi quá nhanh, thử lại sau ít phút."
    return "Telegram trả lỗi %s: %s" % (code, (res.get("description") or "?")[:120])

def get_me(token):
    """(ok, username hoặc thông báo lỗi tiếng Việt)."""
    if not re.fullmatch(TOKEN_RE, token or ""): return False, "token sai định dạng (dạng 123456789:AA... do @BotFather cấp)"
    reached, res, ne = _call(token, "getMe")
    if reached and res.get("ok"): return True, (res.get("result") or {}).get("username", "")
    return False, explain(res, ne)

def send(token, chat, text):
    """(ok, thông báo). Cắt text còn 3500 ký tự (giới hạn Telegram 4096)."""
    if not re.fullmatch(TOKEN_RE, token or ""): return False, "token sai định dạng"
    if not re.fullmatch(CHAT_RE, str(chat or "")): return False, "ID người nhận phải là số (ví dụ 123456789)"
    reached, res, ne = _call(token, "sendMessage", {"chat_id": str(chat), "text": text[:3500], "disable_web_page_preview": True})
    if reached and res.get("ok"): return True, "đã gửi"
    return False, explain(res, ne)
