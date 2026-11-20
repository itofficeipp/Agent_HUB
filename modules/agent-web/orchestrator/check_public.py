#!/usr/bin/env python3
"""Gọi <AW_PUBLIC_URL>/healthz và chẩn đoán lỗi theo tầng. Dùng: check_public.py <url công khai>.
LƯU Ý: chạy từ chính máy này nên chỉ chứng minh DNS + đường tunnel/proxy tới receiver hoạt động.
Mở port ở router (NAT hairpin) có thể chỉ đúng từ bên ngoài: hãy thử thêm từ điện thoại dùng 4G."""
import socket, ssl, sys, urllib.error, urllib.parse, urllib.request
url = sys.argv[1].rstrip("/"); host = urllib.parse.urlparse(url).hostname
try: ips = sorted({i[4][0] for i in socket.getaddrinfo(host, None)})
except socket.gaierror: sys.exit(f"DNS: chưa phân giải được {host} (chưa trỏ bản ghi DNS / chưa 'cloudflared tunnel route dns')")
try:
    r = urllib.request.urlopen(urllib.request.Request(url + "/healthz", headers={"User-Agent": "curl/8.5.0"}), timeout=15)
    body = r.read(200).decode("utf-8", "replace")
    if r.status == 200 and '"ok"' in body: print(f"OK {url}/healthz (DNS {','.join(ips)})"); sys.exit(0)
    sys.exit(f"{url}/healthz trả {r.status} nhưng nội dung lạ: không phải receiver này?")
except urllib.error.HTTPError as e:
    hint = {502: "proxy/tunnel chạy nhưng receiver không trả lời (receiver đã chạy? đúng cổng AW_LISTEN_PORT?)",
            530: "Cloudflare không thấy tunnel (cloudflared chưa chạy hoặc sai hostname)", 1033: "tunnel Cloudflare không kết nối",
            404: "tới được máy chủ nhưng đường /healthz bị chặn/sai (kiểm allowlist đường dẫn trong cloudflared/Caddyfile)"}.get(e.code, "")
    sys.exit(f"HTTP {e.code}: {hint or 'xem log cloudflared/Caddy/receiver'}")
except ssl.SSLError as e: sys.exit(f"TLS: {e} (chứng chỉ chưa cấp? Caddy cần mở cổng 80/443 để xin Let's Encrypt)")
except urllib.error.URLError as e:
    why = str(e.reason)
    if "refused" in why.lower(): sys.exit("kết nối bị từ chối: chưa mở cổng/chưa chạy Caddy-cloudflared, hoặc firewall (ufw allow 80,443)")
    if "timed out" in why.lower(): sys.exit("hết thời gian: router chưa chuyển cổng 80/443, firewall chặn, hoặc nhà mạng dùng CGNAT")
    sys.exit("lỗi mạng: " + why)
