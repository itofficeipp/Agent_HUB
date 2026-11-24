# Changelog

## 0.3.14
- **Mới `kit model-backup`: thêm tài khoản Claude DỰ PHÒNG cho agent tổng** (tài khoản 1 hết lượt/rate_limit thì OpenClaw tự dùng tài khoản 2; hết cooldown thì quay lại tài khoản 1). Một lệnh thay cho chuỗi lệnh tay anh Dũng đã chạy trên Ubuntu 24/11:
  - Hỏi token (nhập ẩn, bỏ khoảng trắng/xuống dòng thừa, kiểm dạng `sk-ant-oat01-...` trước khi dùng, dán sai thì báo nguyên nhân thường gặp).
  - Tự dừng Gateway nếu đang chạy (OpenClaw đòi tắt để ghi credential), lưu token thành profile mới `anthropic:tk2` (hoặc tk3...; KHÔNG ghi đè profile cũ, đã có thì hỏi, mặc định không), đặt thứ tự `auth order` (tài khoản cũ trước, mới sau, giữ thứ tự đang có), đọc lại kiểm, rồi LUÔN bật lại Gateway (kể cả khi lỗi); Gateway vốn tắt thì không bật hộ.
  - Token đi qua pty (`scripts/pty_feed.py`, đã dùng thật từ 0.3.11), không nằm trên dòng lệnh; nhật ký lỗi che token.
  - `kit doctor`: mới 1 tài khoản thì nhắc `kit model-backup`; từ 2 tài khoản thì báo OK. `kit setup` nhắc ở BƯỚC TIẾP.
  - Test mới trong `tests/test_alert.py` mục 5c (14 ca; openclaw GIẢ biết đòi Gateway tắt như thật + systemctl GIẢ). **CHƯA chạy qua kit với OpenClaw thật.** Các lệnh tương đương anh Dũng đã chạy tay trên Ubuntu 24/11 (paste-token --profile-id anthropic:tk2 OK; order set OK; order get in "Auth profile order override: anthropic:manual, anthropic:tk2"). Định dạng in của auth list/order get lấy theo ảnh chụp thật; nếu bản OpenClaw khác in khác, kit báo "CHƯA đặt được thứ tự" kèm lệnh đặt tay.
  - Chưa chứng minh chuyển tài khoản THẬT khi tài khoản 1 hết lượt (mới biết LyLy trả lời bằng model thật lúc tài khoản 1 đang cooldown).

## 0.3.13
- **Token bot Telegram nhập lúc cài đặt nay dùng luôn cho AGENT TỔNG (agent mặc định).** Trước đây bot chỉ gửi báo lỗi; anh Dũng muốn bot đó cũng là bot chat của trợ lý tổng (tên đặt lúc cài, vd LyLy) và ID nhận báo lỗi là ID quản trị tối cao. Trước đó anh phải gõ tay vài nhóm lệnh (config patch, agents bind, set-identity).
  - `kit alert-bot` và câu hỏi token trong `kit setup`/`kit enable agent-web`: sau khi lưu token, kit tự (1) ghi token vào `tenants/<t>/telegram-main.token` chmod 600 (không vào openclaw.json), (2) `channels.telegram`: tokenFile, `dmPolicy: allowlist`, `allowFrom` gồm ID nhận, `groupPolicy: disabled` (chỉ khi chưa đặt), (3) `commands.ownerAllowFrom` thêm `telegram:<ID>` (chủ sở hữu bot), (4) `openclaw agents bind --agent <agent mặc định> --bind telegram:default`, (5) `openclaw agents set-identity --name <ASSISTANT_NAME>`. Sao lưu openclaw.json trước khi ghi. Chạy lại không nhân đôi.
  - **Gộp, không ghi đè**: owner/allowFrom đang có được giữ. Nếu `channels.telegram` đang dùng MỘT BOT KHÁC, kit hỏi (mặc định không) hoặc giữ nguyên khi không tương tác.
  - ID nhận là ID nhóm (âm): chỉ gửi báo lỗi, không gắn bot chat.
  - Mới: `kit alert-bind` (gắn lại bằng token đang lưu), `kit alert-bot --no-chat` (chỉ gửi báo lỗi), `KIT_NO_BIND=1` (bỏ câu hỏi trong setup). `kit doctor` báo bot đã gắn agent tổng chưa.
  - Gửi báo lỗi vẫn đi thẳng Bot API, không qua Gateway: Gateway hỏng vẫn báo được.
  - Test mới trong `tests/test_alert.py` (mục 5b, openclaw GIẢ, Telegram GIẢ). **CHƯA thử qua kit với OpenClaw thật**; các lệnh tương đương anh Dũng đã chạy tay trên Ubuntu 24/11 (config patch + agents bind + set-identity cho kết quả đúng, bot nhận tin nhắn thật).
  - Lưu ý: chưa chứng minh agent tổng trả lời bằng model thật (token Claude đang rate_limit tới khoảng 00:30 25/11).

## 0.3.12
- **Thêm bước nhập token bot Telegram để BÁO LỖI** (trước đây `kit setup` chỉ hỏi ID nhận, không hỏi token nên không có tin nào gửi đi; chỉ ghi `loi_su_kien.log`). Gặp thật khi anh Dũng cài thử trên Ubuntu: màn hình không có chỗ nhập token bot.
  - `kit setup` / `kit enable agent-web`: sau câu **ID Telegram người nhận báo lỗi** (`AW_ALERT_TARGET`, nay phải là dãy số) kit hỏi **token bot** (`AW_ALERT_BOT_TOKEN`, nhập ẩn, lưu `secrets.env` chmod 600, không vào `params.json`). Bỏ trống ID thì không hỏi token. Hỏi xong kit kiểm token bằng `getMe` rồi gửi thử 1 tin; nếu người nhận chưa bấm Start thì nói rõ cách sửa và cho thử lại.
  - **Mới `kit alert-bot`** (nhập/đổi token + ID bất cứ lúc nào, token chỉ nhận qua terminal ẩn, không qua tham số dòng lệnh) và **`kit alert-test`** (gửi thử, thoát mã 1 nếu không gửi được). `kit doctor` báo rõ: chưa có ID (lỗi chỉ ghi log), có ID nhưng chưa có token, hoặc đã cấu hình đủ.
  - Báo lỗi gửi **thẳng qua Telegram Bot API** (`orchestrator/tgalert.py`, chỉ stdlib), không phụ thuộc Gateway: khi Gateway/OpenClaw hỏng vẫn báo được. Bot chỉ gửi, không nhận tin, không gắn vào agent nào nên không thể bị người lạ nhắn vào để điều khiển. Không có token thì dự phòng `openclaw message send` như cũ. Token không bao giờ in ra hoặc đưa vào thông báo lỗi. Báo cáo token hằng ngày (`AW_STATS_TARGET`) dùng chung đường này.
  - `provision_tick`: gửi báo lỗi thất bại thì **thử lại ở lần tick sau** (trước đây coi như đã báo dù gửi lỗi), ghi 1 dòng `canh_bao_khong_gui_duoc` kèm nguyên nhân (không ghi lặp), lỗi đã báo thành công thì im lặng, lỗi mới hoặc lỗi lại sau khi hết thì báo tiếp.
  - Test mới `tests/test_alert.py` (39 ca, Telegram GIẢ cục bộ): token đúng/sai (401), 403 chưa Start, chat not found, mất mạng, cắt tin dài, token không lộ ra màn hình/params/thông báo lỗi, nhập ẩn qua pty, chmod 600, doctor, ba kịch bản của provision_tick.
  - **CHƯA thử với Telegram thật** (cần token bot thật của anh Dũng): API Telegram chỉ được thử bằng bản giả. Cần thử `kit alert-bot` với bot thật trên máy Ubuntu của anh Dũng.
- Sửa ghi chú 0.3.11: đăng nhập Claude bằng trình duyệt **đã chạy thật** trên máy Ubuntu của anh Dũng với tài khoản thật (24/11, bắt token 108 ký tự, lưu `anthropic:manual`; `gateway health` OK, `kit preflight` sẵn sàng). Token đó chưa được kiểm bằng một lần gọi mô hình thật.

## 0.3.11
- **install.sh cài Claude Code ngay lúc cài đặt** (bộ cài chính thức claude.ai, vào `~/.local/bin`, không cần root). Bỏ qua bằng `KIT_CLAUDE_CODE=no`. Claude Code chỉ dùng để lấy token; KHÔNG dùng runner claude-cli.
- **Đăng nhập Claude bằng trình duyệt của người dùng, ngay trên Linux**: mới `scripts/claude-login.sh` chạy `claude setup-token` (in URL claude.ai để mở trên máy người dùng, dán mã về), tự bắt token, tạm dừng Gateway, lưu bằng `openclaw models auth paste-token` (profile `anthropic:manual`, hết hạn 365 ngày), bật lại Gateway, xóa file tạm (shred). Token không nằm trên dòng lệnh. install.sh tự gọi khi có terminal và chưa có đăng nhập Anthropic (bỏ qua bằng `KIT_CLAUDE_LOGIN=no`); chạy lại/gia hạn: `bash scripts/claude-login.sh --force`.
- `scripts/pty_feed.py`: đưa bí mật vào dấu nhắc qua pty (đặt cỡ cửa sổ, đợi dấu nhắc hiện). Sửa lỗi paste-token không nhận khi pty rộng 0 cột.
- Đã thử thật trên VM114 (user thường `kt`) với `claude` GIẢ: lấy token, lưu profile anthropic, Gateway active lại. CHƯA thử với tài khoản Claude thật (cần trình duyệt của người dùng): định dạng in của `claude` thật có thể làm bước bắt token trượt, khi đó script nhờ dán tay.

## 0.3.10
- **add-caller không in bí mật ra màn hình nữa**: mật khẩu + HMAC key ghi vào `<tenant>/agent-web/secrets/caller-<ten>.txt` (file chmod 600, thư mục 700); màn hình chỉ in đường dẫn và lệnh xoá (`shred -u`). `--print` để in như cũ. Lý do: bí mật từng lộ qua ảnh chụp màn hình. Test: test_all (file 600, stdout không có "password") và test_local (--print) đều PASS.
- **install.sh: KIT_ONBOARD=prompt** chạy wizard `openclaw onboard` có hỏi (vẫn cài dịch vụ, chọn cổng trống, kiểm tra Gateway). Không có terminal (stdin không phải tty) thì tự chuyển về thiết lập mặc định. Đã thử thật trên VM114: nhánh không-tty (RC=0, Gateway OK) và nhánh có tty (wizard mở đúng, nhận --gateway-port). CHƯA đi hết wizard tương tác tới cuối.

## 0.3.9
- **install.sh kiểm tra Gateway thật sự chạy** (trước đây in "Xong phần cài" kể cả khi dịch vụ chết). Nếu Gateway không lên sau một lần tự sửa: in LỖI kèm lệnh chỉ đọc để xem nguyên nhân và thoát mã 1.
- **Sửa lỗi SERVICE_DEFINITION_UNKNOWN [inspection-failed]** khi cài dịch vụ Gateway (gặp thật trên máy Ubuntu của anh Dũng). Nguyên nhân tái hiện được trên VM114: unit systemd còn nhãn `failed` (exit 78, do lần chạy trước bị tranh cổng); `gateway uninstall` xoá file nhưng không xoá nhãn. install.sh chạy `systemctl --user reset-failed` + `daemon-reload` trước khi cài. Chỉ xoá nhãn, không dùng --force/sudo.
- **Tự chọn cổng Gateway trống**: thử 18789, 18795, 18805, 18815, 18825 (cần gốc và gốc+2 trống), dùng `onboard --gateway-port`. Nếu 18789 trống nhưng 18790 (sandbox) bận thì chỉ cảnh báo. Đặt OPENCLAW_GATEWAY_PORT để bỏ qua bước này.
- Đã thử thật trên VM114 (user thường `kt`): máy sạch (cổng 18789 bận -> tự chọn 18795, health OK, RC=0) và Gateway đang dừng (tự sửa, health OK, RC=0).
- CHƯA thử thật: đường báo lỗi (Gateway không thể lên -> LỖI, thoát mã 1); chưa chạy 0.3.9 trên máy Ubuntu của anh Dũng.

## 0.3.8
- install.sh: tên công ty tự đổi sang chữ thường (D2D -> d2d) và được kiểm tra ngay đầu script, trước khi cài gì (trước đây gõ D2D thì cài xong mới báo lỗi tên tenant). Đã thử thật trên VM114: D2D -> d2d, RC 0, tenant d2d được tạo.

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
