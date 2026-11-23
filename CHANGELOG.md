# Changelog

## 0.3.1
- **kit setup**: cài từng bước có gợi ý (kiểm tra máy -> chọn chức năng -> hỏi thông số -> tóm tắt -> apply --dry-run -> apply -> keygen/bên gọi -> doctor -> bước tiếp). Chạy lại an toàn; hỗ trợ --yes/--modules/--params-file/--no-apply cho nhiều công ty.
- **kit preflight**: kiểm tra máy (không root, python, git, openclaw, node, systemd, linger, docker, dung lượng) với gợi ý sửa.
- Mọi tham số của base/agent-web/n8n có **hint** (gợi ý) và **example** (ví dụ); nhập sai thì báo lỗi và hỏi lại (tối đa 5 lần) thay vì thoát.
- install.sh/README: trỏ đúng repo itofficeipp/Agent_HUB, bỏ chỗ giữ chỗ.
- test: tests/test_local.py mục 11 (setup tương tác qua pty + không tương tác, preflight, hint đủ).

## 0.3.0
- agent-web: **mở thêm công cụ cho agent** (đưa `mo_cong_cu.py` của hệ thống đang chạy vào kit, viết lại cho tổng quát, không còn tên agent/đường dẫn riêng). Tham số `AW_TOOLS_WEB` (web_search + web_fetch), `AW_TOOLS_BROWSER`, `AW_TOOLS_RUNTIME` (bỏ group:runtime khỏi deny, chỉ trong sandbox), `AW_SANDBOX_IMAGE`, `AW_SEARCH_PROVIDER`, `AW_FULL_AGENTS` (agent quyền rộng, không bị ghi đè sandbox.deny). Mặc định TẮT: không đổi hành vi bản cũ.
- `provision.py` tự chạy `mo_cong_cu.py` sau khi tạo agent/gắn kênh khi `AW_TOOLS_WEB=yes`; lệnh mới `kit run agent-web open-tools [--dry-run]`.
- Test: bản mới cho kết quả cấu hình giống hệt bản đang chạy trên VM111 (cùng đầu vào); thêm 15 kiểm tra vào tests/test_local.py.
- `.gitleaks.toml`: ghi rõ `tests/test_xac_thuc.js` (token giả `abcdefgh12345678`) là mẫu, không phải bí mật.

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
