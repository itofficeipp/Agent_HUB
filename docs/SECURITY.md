# Bảo mật

- Không commit: `*.env`, `secrets.env`, `users.json`, `*.pem` (trừ `.pub.pem`), `*.token` — đã nằm trong `.gitignore`.
- `.gitleaks.toml` + hook pre-commit (`gitleaks protect --staged --redact`). Bị chặn thì gỡ bí mật, không dùng `--no-verify`. Đã lỡ đẩy bí mật lên git: **đổi (rotate) bí mật ngay**, xoá khỏi lịch sử không đủ.
- `kit export-config` che bí mật + từ chối ghi nếu còn chuỗi giống token. Vẫn nên xem lại tay trước khi đưa vào repo.
- Repo nên để **private** vì có tên tool MCP, cấu trúc nội bộ của công ty.
- Webhook: Basic auth + HMAC-SHA256 trên `timestamp + "." + body`, timestamp lệch tối đa 5 phút, **chống gửi lại** (chữ ký dùng một lần trong 10 phút, receiver tích hợp), 60 yêu cầu/phút/IP, khoá IP 5 phút sau 10 lần sai xác thực, body tối đa 64KB. Bên gọi dùng HMAC `tuy_chon` và không ký thì **không** có chống gửi lại: nên để `bat_buoc`. Receiver chỉ nghe 127.0.0.1; ra Internet qua Cloudflare Tunnel hoặc Caddy, chỉ cho `/healthz` và `/webhook/<đường dẫn bí mật>` (docs/EXPOSE.md). Bản n8n: chưa có chống gửi lại.
- Mật khẩu bên gọi chỉ in một lần lúc `add-caller`; workflow n8n chỉ chứa băm + secret HMAC.
- Token bot/MCP mã hoá RSA-OAEP; khóa bí mật chỉ ở Gateway.
- Agent người dùng: sandbox `all`, deny nhóm tool runtime/sessions/ui/nodes/automation/agents/messaging, `fs.workspaceOnly`.
- Kho SQLite của receiver (`agent-web/data/agent-web.db`) chỉ chứa `bi_mat` đã mã hoá bằng khoá công khai; không chứa token rõ, mật khẩu hay khoá HMAC. Log receiver không ghi body/header xác thực.
- File `expose/*` chứa đường dẫn webhook bí mật nên đặt chmod 600 và không commit.

- Mở thêm công cụ cho agent (`AW_TOOLS_WEB=yes`, mặc định TẮT): chỉ áp cho agent có sandbox `all`; `AW_TOOLS_RUNTIME=yes` chỉ cho exec/file TRONG sandbox của agent; `AW_TOOLS_BROWSER=yes` bật trình duyệt sandbox và vẫn chặn gateway/nodes/kênh nhắn tin trong sandbox. Agent trong `AW_FULL_AGENTS` không bị ghi đè `sandbox.deny`: chỉ liệt kê agent anh/chị đã quyết định cấp quyền rộng.
