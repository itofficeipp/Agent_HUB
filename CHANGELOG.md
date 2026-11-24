# Changelog

## 0.3.7
- **install.sh không còn treo/hỏi trên máy Ubuntu mới** (gặp thật khi cài thử trên Ubuntu mới của anh Dũng: treo 20 phút ở "Configuring NodeSource repository"):
  - Nguyên nhân: hook **needrestart** của apt mở hộp thoại whiptail "Pending kernel upgrade" chờ phím, hộp thoại bị ẩn vì output trình cài bị lọc, apt giữ khoá, các lệnh khác in "Waiting for cache lock". Đã tái hiện đúng hộp thoại trên VM114 (giả lập kernel mới + UI Debconf) và xác nhận **có cấu hình sửa thì apt xong sau 3 giây** (không sửa: treo).
  - install.sh ghi `/etc/needrestart/conf.d/99-openclaw-kit.conf` (cần sudo, chỉ khi có needrestart, chạy lại an toàn): restart=a, UI stdio, kernelhints=-1, ucodehints=0 (không hộp thoại). Xoá file này để trở lại mặc định.
  - Chưa thử trên máy có needrestart mặc định tương tác thật (chỉ giả lập bằng cấu hình, Ubuntu 24.04).
- **install.sh thiết lập OpenClaw mặc định, không hỏi**: gọi trình cài OpenClaw với `--no-onboard`, rồi `openclaw onboard --non-interactive --accept-risk --mode local --flow quickstart --auth-choice skip --skip-channels --skip-skills --skip-search --skip-ui --skip-health --install-daemon` (loopback + token, chưa đăng nhập model; token Claude dán ở bước sau). `KIT_ONBOARD=manual` để tự chạy onboard; `KIT_ONBOARD_DAEMON=no` để không cài service. Bỏ qua nếu đã có `~/.openclaw/openclaw.json`.
  - Đã thử thật trên VM114 (HOME tạm): onboard không tương tác rc 0, config hợp lệ, agent main được tạo; chạy lại không làm gì thêm. Lệnh onboard có `--install-daemon` đã thử thật trước đó (docs/TESTING.md: Gateway systemd user `active`); **chưa chạy lại nguyên install.sh bản mới kèm service trên máy trắng** (sẽ đè service Gateway của Lab).
- install.sh tự thêm PATH (`~/.local/bin`, `~/.npm-global/bin`) vào `~/.bashrc` một lần.

## 0.3.6
- **Sửa lỗi lượt chat đầu của agent mới**: agent nhân viên tạo qua webhook có kho credential TRỐNG nên báo `No API key found for provider "anthropic"` (phát hiện khi thử thật trên VM114). Thêm tham số **AW_AUTH_OWNER** (mặc định `main`; `none` = tự quản; hoặc id agent đang giữ token): kit đặt `agents.defaults.authInheritance` để mọi agent mới dùng chung credential của agent chủ.
  - Tự đặt khi `kit apply agent-web` (post_apply) và trước khi `provision` tạo agent mới; chạy tay: `kit run agent-web auth-owner`. Chỉ ghi khi chưa đặt; Gateway đã đặt giá trị khác thì giữ nguyên và chỉ cảnh báo; agent chủ chưa tồn tại thì báo LỖI, không ghi. Chạy lại an toàn (idempotent). `main`/`none` không đổi gì.
  - **kit doctor** (agent-web, Gateway ở máy này): kiểm `openclaw models status --agent <chủ> --check`, báo **LỖI** nếu agent chủ chưa có token (kèm lệnh `paste-token` và cách đổi chủ), cảnh báo nếu token sắp hết hạn hoặc AW_AUTH_OWNER lệch với Gateway. Gateway ở máy khác: chỉ in cảnh báo cách tự kiểm.
  - test: fake openclaw hỗ trợ `config get` theo đường dẫn, `config unset`, `models status`; thêm 20 ca (auth-owner, doctor, provision tự đặt, chống chèn lệnh).

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
