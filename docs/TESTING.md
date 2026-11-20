# Kiểm thử — đã làm gì, chưa làm gì

## ĐÃ CHẠY (cục bộ, tất cả PASS; không chạm OpenClaw/n8n/Telegram/Cloudflare thật)
`python3 tests/test_all.py` (backend n8n: openclaw giả + n8n giả + HOME tạm): kit init/enable/apply/idempotent; `config patch` (giả); secrets.env 600; build workflow 11 node; logic webhook bằng node; mã hoá RSA-OAEP rồi giải mã đúng như gan_kenh.sh; provision.py → create_agent.sh tạo agent + sandbox; gan_mcp.py cô lập A/B/main.

`python3 tests/test_local.py` (receiver tích hợp, openclaw giả): enable/apply mặc định (local + tunnel), file expose (tunnel/port/none), receiver thật chạy trên cổng ngẫu nhiên: 201/200/409 (replay)/401/403/422/413/404, token không lọt vào phản hồi/log/DB, `bi_mat` giải mã được bằng khoá bí mật Gateway, khoá IP sau 10 lần sai (qua CF-Connecting-IP), provision.py trên SQLite, thống kê token (CSV 600 + gửi báo cáo qua `message send` giả), `kit doctor` (nghe loopback, healthz, địa chỉ công khai giả → báo LỖI), `check_listen` bắt cổng nghe `0.0.0.0`, tenant cũ giữ `AW_BACKEND=n8n`, module n8n sinh compose/.env/expose đúng.

Ngoài ra `openclaw config patch --dry-run` của module `base` đã chạy với OpenClaw thật 2026.10.9 (chỉ kiểm schema, không ghi). Định dạng `openclaw gateway usage-cost --agent <id> --days N --json` (dùng cho thống kê token) đã xem trên OpenClaw thật: `{daily:[{date,input,output,cacheRead,cacheWrite,totalTokens,totalCost}],totals}`; riêng việc đếm token của agent người dùng thật **chưa** có dữ liệu để kiểm.

## ĐÃ THỬ THẬT trên máy thử (Lab) (20/11/2026; Ubuntu 24.04, systemd user, Internet ra được; không dùng dữ liệu/token thật)
- Receiver chạy bằng **systemd user service** do `kit apply` sinh: bật, nghe đúng `127.0.0.1`, `kill -9` → tự chạy lại sau ~4 giây; `kit doctor` báo đúng (nghe loopback, healthz, địa chỉ công khai giả → LỖI kèm chẩn đoán DNS); `kit apply` lần hai nâng cấp file và khởi động lại dịch vụ.
- `test-webhook` thật trên receiver đó: 201/200/409(replay)/401/401/422/422/401.
- **Cloudflare quick tunnel** (`cloudflared tunnel --url`, không cần tài khoản; bản 2026.11.1): máy này (ngoài Lab) gọi qua Internet → Cloudflare → receiver trên Lab: healthz 200, tạo user 201, replay 409, sai mật khẩu 403, sai đường dẫn 404. **Lỗi thật phát hiện nhờ thử này** (POST sai đường dẫn không đọc body → body lọt vào yêu cầu kế tiếp trên cùng kết nối → 400): đã sửa, thêm test hồi quy (xác nhận test FAIL với bản cũ, PASS với bản mới), thử lại qua tunnel đều đúng.
- `cloudflared tunnel ingress validate` + `ingress rule` với `cloudflared-config.yml` do kit sinh: cấu hình hợp lệ; `/healthz` và `/webhook/<đúng đường dẫn>` khớp rule #0, mọi đường/hostname khác rơi vào rule 404.
- **Caddy v2.11.9**: `caddy validate` Caddyfile do kit sinh (expose=port) và của module n8n: hợp lệ (`request_body max_size` chạy được). Chạy thật bản tương đương (chỉ đổi địa chỉ site thành `http://127.0.0.1:18080`, vì không có tên miền/HTTPS thật): healthz 200, `/` 404, `/webhook/sai` 404, webhook thật không auth → 401 từ receiver, body 70KB → 413 từ Caddy.
- `docker compose config` với `docker-compose.yml` của module n8n: hợp lệ, port chỉ `127.0.0.1:5678` (không `up`, không kéo image).
Đã dọn sạch Lab sau thử (dịch vụ, unit, file, tunnel); không tạo agent nào trong OpenClaw của Lab.

## CHƯA THỬ THẬT (cần thử ở máy công ty hoặc bước sau, theo thứ tự)
1. **Named tunnel** có tên miền riêng + `cloudflared tunnel route dns` + chạy dịch vụ nền; Cloudflare Access. (Quick tunnel và việc kiểm cấu hình đã thử; phần cần tài khoản Cloudflare + zone thì chưa.)
2. **Mở port thật**: router NAT 80/443, Let's Encrypt xin chứng chỉ, thử từ 4G, CGNAT.
3. Receiver tự chạy lại **sau khi khởi động lại máy** (cần `loginctl enable-linger`; Lab đã bật sẵn, chưa reboot thử).
4. `gan_kenh.sh` với Telegram thật (getMe, config patch tài khoản, binding).
5. `openclaw agents add`/`sandbox explain` thật + Docker sandbox có sẵn image.
6. Module `n8n`: `docker compose up -d` thật (kéo image), `N8N_PROXY_HOPS`, tạo API key; `kit run agent-web tables` và `deploy-workflow` lên n8n thật.
7. SSH tới Gateway khác máy (`AW_GATEWAY_SSH=user@host`); `token_stats.py` qua SSH; timer `stats` và `provision` chạy theo lịch.
8. Thống kê token với agent người dùng thật (định dạng `usage-cost` đã xem trên OpenClaw thật nhưng agent thử chưa có dữ liệu; chưa đối chiếu số với Control UI).
9. `install.sh` trên Ubuntu sạch; `kit update --with-openclaw`.
10. Chịu tải: receiver là `ThreadingHTTPServer` (đủ cho vài yêu cầu/phút; chưa đo ở tải cao).
Quy tắc: thử trên máy Lab trước khi đưa vào production.
