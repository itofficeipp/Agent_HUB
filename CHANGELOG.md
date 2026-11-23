# Changelog

## 0.3.5
- **kit doctor --strict**: thoát mã 1 khi có mục LỖI (để CI/script/tự động hoá dùng được). Không có `--strict` vẫn thoát mã 0 như cũ (đã rà: setup/update gọi doctor nội bộ, không dựa vào mã thoát; test cũ không đọc mã thoát của doctor). `kit setup` và `kit update` không đổi.

## 0.3.4
- **kit doctor** (khi bật agent-web): báo **LỖI** nếu bất kỳ model nào gán `agentRuntime.id = claude-cli`. Runner này chạy NGOÀI sandbox Docker (docs OpenClaw), nên agent khách sẽ chạy lệnh trên máy thật; thử thật trên VM114 báo `sandbox: {mode: off}` (docs/TESTING.md). Cho phép có chủ đích bằng `KIT_ALLOW_CLAUDE_CLI=1`.
- **kit doctor** kiểm có image sandbox (mặc định `openclaw-sandbox:trixie-slim`; đổi bằng `agents.defaults.sandbox.docker.image` hoặc `KIT_SANDBOX_IMAGE`); thiếu thì LỖI + gợi ý.
- **kit sandbox-image [--force]**: dựng image sandbox (debian + bash curl git jq python3 ripgrep, user `sandbox`); OpenClaw không tự dựng, docs còn ghi bookworm-slim nhưng bản 2026.11.7 đòi trixie-slim. Idempotent.
- **docs/MODEL-AUTH.md**: cách cấp quyền model bằng token ủy quyền (`claude setup-token`, mỗi công ty một token riêng) cho runtime nhúng, không dùng API key; lệnh nhập token cần tắt Gateway.
- test: tests/test_local.py (docker giả) cho cả ba điểm trên.

## 0.3.3
- **install.sh**: mỗi máy/công ty tự sinh khoá deploy riêng (`~/.ssh/agent_hub_deploy`, ed25519, không mật khẩu, chmod 600) khi chưa clone được; in khoá công khai để quản trị viên thêm vào GitHub (Deploy keys, CHỈ ĐỌC). Khoá riêng không rời máy. Sau khi clone, ghi `core.sshCommand` vào repo để `kit update` (git pull) dùng đúng khoá. Đổi đường dẫn khoá bằng `KIT_DEPLOY_KEY`.

## 0.3.2
- **Sửa**: `kit init`/`kit setup` tenant thứ hai không còn tự đổi tenant mặc định (phát hiện khi thử trên VM Lab trắng: `kit doctor` trơn kiểm nhầm tenant mới). Tenant đầu tiên vẫn thành mặc định; muốn đổi: `kit use <tenant>` hoặc `--tenant`.
- Thêm lệnh `kit use <tenant>`; test trong tests/test_local.py.

## 0.3.1
- **kit setup**: cài từng bước có gợi ý (kiểm tra máy -> chọn chức năng -> hỏi thông số -> tóm tắt -> apply --dry-run -> apply -> keygen/bên gọi -> doctor -> bước tiếp). Chạy lại an toàn; hỗ trợ --yes/--modules/--params-file/--no-apply cho nhiều công ty.
- **kit preflight**: kiểm tra máy (không root, python, git, openclaw, node, systemd, linger, docker, dung lượng) với gợi ý sửa.
- Mọi tham số của base/agent-web/n8n có **hint** (gợi ý) và **example** (ví dụ); nhập sai thì báo lỗi và hỏi lại (tối đa 5 lần) thay vì thoát.
- install.sh/README: trỏ đúng repo itofficeipp/Agent_HUB, bỏ chỗ giữ chỗ.
- sửa lỗi thật (thử trên Lab): umask 002 làm ~/.config nhóm-ghi được nên OpenClaw không cài được service; kit đặt umask 022, preflight kiểm quyền thư mục.
- doctor in cảnh báo của openclaw config validate (vd plugin duckduckgo ở 2026.11); docs/UPDATING.md có bảng lưu ý theo phiên bản.
- thử thật với OpenClaw 2026.11.7 trên user mới (docs/TESTING.md).
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
