# Changelog

## 0.2.0
- agent-web: **receiver tích hợp** (Python stdlib + SQLite, `AW_BACKEND=local`, mặc định) thay cho n8n; giao thức webhook giữ nguyên. Tenant cũ có `AW_N8N_URL` tự giữ `AW_BACKEND=n8n`.
- Chống gửi lại (mỗi chữ ký dùng một lần trong 10 phút → 409), giới hạn tần suất theo IP, khoá IP sau nhiều lần sai xác thực, giới hạn body 64KB.
- `AW_EXPOSE` = `tunnel` | `port` | `none`: sinh `cloudflared-config.yml` hoặc `Caddyfile` + hướng dẫn; `kit doctor` kiểm receiver chỉ nghe loopback và chẩn đoán địa chỉ công khai theo tầng.
- Thống kê token theo người (`AW_STATS=yes`): CSV + báo cáo Telegram hằng ngày qua systemd timer.
- Module `n8n` (tuỳ chọn): chỉ sinh `docker-compose.yml` mẫu.
- `kit`: tham số/file/kiểm tra có điều kiện (`when`), `default_if_set`, `probe` (hỏi `N8N_URL` thì thử `/healthz`), hint của `doctor` được render.

- Sửa lỗi receiver (phát hiện khi thử qua Cloudflare Tunnel thật): yêu cầu POST bị từ chối trước khi đọc body làm hỏng yêu cầu kế tiếp trên cùng kết nối keep-alive; nay đóng kết nối và có test hồi quy.

## 0.1.0
- Khung `kit` (init/modules/enable/apply/update/doctor/run/export-config), module `base`, module `agent-web` (webhook tạo nhân viên + bot Telegram + MCP), công cụ xuất cấu hình đã che bí mật, bộ test cục bộ.
