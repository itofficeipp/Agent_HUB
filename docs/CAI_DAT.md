# Hướng dẫn cài đặt openclaw-kit (từ máy trống đến chạy được)

Tài liệu này gom các bước theo đúng thứ tự đã chạy thật. Mỗi mục ghi rõ ĐÃ THỬ THẬT ở đâu hoặc CHƯA THỬ. Chi tiết từng phần nằm ở các tài liệu khác (có liên kết).

## 0. Cần gì trước khi bắt đầu
- Máy Linux (đã thử Ubuntu), chạy bằng **user thường, KHÔNG root**, có `sudo`, `git` (thiếu: `sudo apt install -y git`), `python3`, systemd user.
- **Docker Engine** (kit KHÔNG tự cài): cần cho sandbox của agent-web. Cài theo docs.docker.com/engine/install/ubuntu rồi `sudo usermod -aG docker $USER` và đăng nhập lại.
- **Dịch vụ chạy nền khi không đăng nhập (linger):** `sudo loginctl enable-linger $USER` (kit không tự bật; `kit doctor` nhắc nếu thiếu). Không có thì Gateway và receiver chỉ chạy khi còn phiên đăng nhập.
- `kit preflight` kiểm các mục trên và báo cách sửa.
- OpenClaw từ **2026.10.9** trở lên. Đã chạy thật với 2026.10.9 (máy dev), 2026.11.7 (Lab sạch), 2026.11.8 (Ubuntu thật của anh Dũng: setup, model-backup, alert-bind). Khác biệt giữa các bản: mục 9.
- Tài khoản Claude của công ty (lấy token ở mục 4).
- Bot Telegram riêng cho công ty: nhắn @BotFather, `/newbot`, giữ token; mở bot bấm Start; lấy ID của bạn ở @userinfobot.
- Phiên bản kit: bản đã chốt cho **một công ty/máy** là tag **v0.3.17**. Từ bản **0.4.0** có thêm Gateway riêng cho công ty thứ hai trên cùng máy (mục 8); đã chạy đủ test với OpenClaw giả, CHƯA cài Gateway riêng thật.

## 1. Quyền đọc repo (một lần cho mỗi máy)
Repo là private; mỗi máy dùng **khoá deploy chỉ đọc** riêng.
1. Chạy `bash install.sh <ten-cong-ty>` (mục 2). Nếu chưa clone được, installer tự tạo khoá `~/.ssh/agent_hub_deploy` và in dòng `ssh-ed25519 ...`.
2. Quản trị viên thêm dòng đó vào GitHub → repo Agent_HUB → Settings → Deploy keys, tên theo công ty, **KHÔNG tích "Allow write access"**.
3. Chạy lại `bash install.sh <ten-cong-ty>`. Công ty ngừng dùng: xoá đúng khoá đó trên GitHub, các công ty khác không ảnh hưởng.

## 2. Cài kit và OpenClaw
```bash
bash install.sh congty-abc        # tên: a-z 0-9 _ - (2-31 ký tự); chữ hoa tự đổi sang thường
```
- Tự cài OpenClaw (nếu thiếu, kể cả Node), Claude Code (chỉ để lấy token), lệnh `kit`, và thiết lập OpenClaw mặc định không hỏi. Có cấu hình needrestart (cần sudo) để cài gói không bị treo ở hộp thoại "Pending kernel upgrade"; bị treo thì `sudo pkill whiptail`.
- Tuỳ chọn môi trường: `KIT_DIR` (mặc định ~/openclaw-kit), `KIT_REPO`, `KIT_ONBOARD=manual` (tự chạy wizard OpenClaw), `KIT_CLAUDE_CODE=no`, `KIT_CLAUDE_LOGIN=no`.
- Cuối cùng installer có thể mời đăng nhập Claude (mục 4). Bỏ qua thì làm sau.
- **Công ty thứ hai trên cùng máy: KHÔNG chạy lại `install.sh <tên>`** (nó tạo tenant dùng Gateway mặc định). Dùng mục 8.

## 3. Cài từng bước có gợi ý
```bash
kit setup congty-abc
```
Năm bước: kiểm máy → tên công ty → chọn chức năng (`base`, `agent-web`; `n8n` tuỳ chọn) → thông số (mỗi câu có gợi ý, bí mật nhập ẩn, lưu chmod 600 trong `~/.config/openclaw-kit/tenants/<ten>/secrets.env`) → xem trước `apply --dry-run`, dựng thật, `doctor`. Chạy lại lúc nào cũng an toàn (giá trị đã nhập được giữ). Muốn đổi một giá trị: `kit enable agent-web --set KEY=giá_trị` rồi `kit apply`.
- Không hỏi (điền sẵn): `kit setup congty-abc --yes --modules base,agent-web --params-file congty.json` (mẫu `examples/congty.params.json`). Chỉ lưu và xem trước: thêm `--no-apply`.
- Thủ công từng lệnh (cùng kết quả): `kit init`, `kit enable base`, `kit enable agent-web`, `kit apply --dry-run`, `kit apply`, `kit doctor`.
- Mọi lần apply tự sao lưu `openclaw.json` vào `~/.config/openclaw-kit/backups/`.

## 4. Tài khoản Claude (token ủy quyền, không API key)
Nguyên tắc: mỗi công ty một token từ chính tài khoản Claude của công ty đó; dùng runtime nhúng, **không** dùng runner `claude-cli` (`kit doctor` báo LỖI). Chi tiết: docs/MODEL-AUTH.md.
- **Công ty đầu tiên (Gateway mặc định):** `bash ~/openclaw-kit/scripts/claude-login.sh` (hoặc để installer làm). Mở đường dẫn in ra bằng trình duyệt, đăng nhập đúng tài khoản, bấm cho phép, dán mã về; token 1 năm được lưu vào OpenClaw, không nằm trên dòng lệnh. Script tự tạm dừng và bật lại dịch vụ `openclaw-gateway` khi ghi token. Lưu ý (suy từ mã, CHƯA chạy trên 2026.11.8): bước "đã có đăng nhập thì bỏ qua" dùng `models auth list`, bản 2026.11.8 chỉ cho đọc khi Gateway tắt, nên script có thể không nhận ra đã có đăng nhập và đăng nhập lại (ghi đè `anthropic:manual`). Đã có đăng nhập rồi thì đừng chạy lại script này.
- **Công ty có Gateway riêng (mục 8):** KHÔNG dùng `claude-login.sh` (nó ghi vào Gateway mặc định). Dùng `kit --tenant <ten> model-backup`: Gateway mới còn trống nên token đầu tiên thành tài khoản chính `anthropic:manual`.
- Agent nhân viên (tạo qua webhook) thừa hưởng credential của agent chủ (`AW_AUTH_OWNER`, mặc định `main`); kit tự đặt `authInheritance`, `kit doctor` báo LỖI nếu agent chủ chưa có token. Dùng chung nghĩa là mọi nhân viên chung hạn mức tài khoản đó.
- Sandbox: `kit sandbox-image` (OpenClaw không tự dựng image; thiếu image thì agent dừng hẳn, an toàn nhưng không trả lời).

## 5. Bot Telegram: báo lỗi và chat với agent tổng
```bash
kit alert-bot
```
Hỏi ID Telegram của bạn rồi token bot (nhập ẩn), gửi thử 1 tin, và **gắn luôn bot này làm bot chat của agent tổng** (tên trợ lý là `ASSISTANT_NAME` lúc cài). Chỉ ID của bạn được nhắn và là chủ sở hữu (`commands.ownerAllowFrom`). Không muốn gắn chat: `kit alert-bot --no-chat`. Gắn lại: `kit alert-bind` (tự sao lưu `openclaw.json`). Gửi thử lại: `kit alert-test`.
- Đã chạy thật trên Ubuntu 2026.11.8: bot chat của agent tổng trả lời bình thường sau `alert-bind`.
- Không dùng chung một bot cho hai công ty; không gửi token qua chat, chỉ nhập ẩn khi kit hỏi.

## 6. Tài khoản Claude dự phòng (tuỳ chọn, khuyên dùng)
```bash
kit model-backup
```
Hỏi token tài khoản 2 (nhập ẩn). Lấy token: đăng nhập ĐÚNG tài khoản Claude số 2 trên trình duyệt, chạy `claude setup-token`, dán mã về, copy chuỗi bắt đầu bằng `sk-ant-oat` (chỉ hiện một lần).
- Kit tự dừng Gateway, lưu profile `anthropic:tk2` (không đụng profile cũ), đặt thứ tự `manual → tk2`, đọc lại kiểm, bật lại Gateway. Chạy lại để thêm `tk3`.
- Đã có từ 2 tài khoản: kit hỏi "CHỈ đặt thứ tự dự phòng, KHÔNG thêm token mới?" (Enter = đồng ý).
- Dán nhầm: kit báo độ dài và 4 ký tự đầu để anh tự đối chiếu, lọc ký tự điều khiển của terminal, và nhận token nằm lẫn trong chuỗi dài.
- ĐÃ THỬ THẬT (Ubuntu 2026.11.8): đặt thứ tự `manual → tk2`, đọc lại khớp, Gateway bật lại. **CHƯA chứng minh:** hệ thống tự chuyển sang `tk2` khi `manual` hết lượt; agent nhân viên có theo thứ tự dự phòng hay không.
- Hai tài khoản nên cùng một chủ/công ty.

## 7. Phần web nhân viên (agent-web)
Sau `kit setup` (đã chọn `agent-web`):
1. `kit run agent-web keygen` (tạo khoá mã hoá trên Gateway; khoá bí mật chỉ ở Gateway).
2. `kit run agent-web add-caller <ten-web>`: tạo bên gọi webhook; mật khẩu và HMAC key ghi vào file chmod 600, **không in ra màn hình**; đưa cho dev web rồi `shred -u` file.
3. Đưa ra Internet: làm theo `~/.config/openclaw-kit/tenants/<ten>/agent-web/expose/HUONG_DAN.md` (Cloudflare Tunnel hoặc mở port; docs/EXPOSE.md). Web bên ngoài gọi `<AW_PUBLIC_URL>/webhook/<AW_WEBHOOK_PATH>`. Cloudflare named tunnel + DNS và mở port/router thật: CHƯA THỬ.
4. Thử: `kit run agent-web test-webhook --user <ten> --password <mk> --secret <hmac>` (receiver tích hợp kỳ vọng 201/200/409/401/401/422/422/401). Đừng gõ nguyên dấu `<...>` trong bash (bash coi là chuyển hướng); thay bằng giá trị thật.
5. Khi ổn: bật dịch vụ nền tự chạy: `kit enable agent-web --set AW_AUTOSTART=yes` rồi `kit apply` (mặc định `AW_AUTOSTART=no`; hoặc `systemctl --user enable --now openclaw-kit-agentweb-provision.timer`). Công ty có Gateway riêng: thêm `--tenant <ten>` và tên unit có hậu tố, ví dụ `openclaw-kit-agentweb-ipp-provision.timer`.
6. Công cụ cho agent (tuỳ chọn): `AW_TOOLS_WEB=yes` (+ `AW_TOOLS_BROWSER`, `AW_TOOLS_RUNTIME`), sau `apply` chạy `kit run agent-web open-tools --dry-run` xem trước rồi bỏ `--dry-run`.
7. Kiểm: `kit doctor` phải "Tất cả OK". Telegram thật cho từng nhân viên và n8n thật: CHƯA THỬ (docs/TESTING.md).

## 8. Công ty thứ hai trên CÙNG máy (kit 0.4.0): Gateway riêng
Mỗi công ty = một tenant có **Gateway OpenClaw riêng** (`openclaw --profile <p>`): dữ liệu `~/.openclaw-<p>`, dịch vụ `openclaw-gateway-<p>`, cổng riêng, bot Telegram riêng. Lỗi bên này không ảnh hưởng công ty kia. Ví dụ công ty ipp:
```bash
kit init ipp --oc-profile ipp --oc-port 19009
kit --tenant ipp gateway-install       # hỏi xác nhận; chạy openclaw --profile ipp gateway install --port 19009 (thêm dịch vụ systemd user MỚI openclaw-gateway-ipp)
kit setup ipp                          # luôn kèm tên; chọn base + agent-web
kit --tenant ipp alert-bot             # bot Telegram RIÊNG của ipp
kit --tenant ipp model-backup          # token Claude đầu tiên của Gateway ipp
kit --tenant ipp run agent-web keygen
kit --tenant ipp run agent-web add-caller web
kit --tenant ipp doctor
```
- Luật: profile a-z 0-9 - (không phải `default`/`main`); cổng Gateway cách cổng mọi Gateway khác **≥ 120** (mặc định 18789, ví dụ 19009); không trùng profile/cổng tenant khác. Kit chặn các lỗi này.
- Tự tách tên: cổng receiver mặc định = 8787 + (cổng Gateway − 18789), tức 9007 cho 19009; thư mục Gateway `~/openclaw-kit-agentweb-ipp`; khoá `~/.config/agentweb-ipp`; unit `openclaw-kit-agentweb-ipp-*`. Công ty cũ giữ nguyên tên/cổng/đường dẫn.
- Cần tên miền/tunnel (`AW_PUBLIC_URL`) riêng, trỏ về cổng receiver của công ty đó.
- **Luôn kèm `--tenant <ten>`** (hoặc `kit use <ten>`) để khỏi nhầm sang công ty kia. `kit setup` tự dừng nếu tên gõ vào dùng Gateway khác tenant đang chọn.
- Không dùng `scripts/claude-login.sh` cho Gateway riêng. Kit không tự sao chép đăng nhập giữa hai Gateway; dùng chung tài khoản Claude thì dán cùng một token và lượt dùng tính chung.
- Gõ tay lệnh OpenClaw cho Gateway riêng: `openclaw --profile ipp ...` hoặc `~/.config/openclaw-kit/tenants/ipp/bin/openclaw ...`. CLI KHÔNG tôn trọng biến `OPENCLAW_PROFILE` (đã kiểm thật 2026.10.9), chỉ cờ `--profile`.
- Gateway ở máy khác qua SSH (`AW_GATEWAY_SSH`) chưa hỗ trợ profile; kit từ chối rõ.
- `gateway-install` đặt `gateway.mode=local` cho profile mới (nếu chưa có cấu hình) rồi mới cài dịch vụ; cờ `--port` và `--force` của `openclaw gateway install` đã xem trong `--help` (2026.10.9). Chạy lại có `--force` nếu dịch vụ đã tồn tại.
- Kiểm: `systemctl --user status openclaw-gateway-ipp`; Gateway cũ `systemctl --user status openclaw-gateway` phải vẫn chạy. CHƯA THỬ thật cờ `--profile` trên OpenClaw 2026.11.8. Chi tiết: docs/MULTI-COMPANY.md.

## 9. Khác biệt theo bản OpenClaw (đã gặp thật)
- **2026.11.8:** `models auth list` và `paste-token` đòi Gateway TẮT ("exclusive offline state owner"); `kit model-backup` tự xử lý (tạm dừng vài giây, rồi bật lại, hỏi trước). Thêm tài khoản thứ hai phải có `--profile-id`, nếu không OpenClaw lưu đè vào `anthropic:manual` (mặc định của `paste-token`); kit luôn tự đặt `anthropic:tk2`. Máy dev 2026.10.9 không đòi, nên test cục bộ không bắt được lỗi này: luôn thử bản OpenClaw của máy khách.
- **2026.11.7:** provider web search `duckduckgo` là plugin ngoài; `kit doctor` báo CANH BAO. Cài: `openclaw plugins install npm:@openclaw/duckduckgo-plugin` hoặc chọn provider khác (`AW_SEARCH_PROVIDER`).

## 10. Cập nhật và khôi phục
`kit update` (kit mới + migrations + apply + doctor), `kit update --with-openclaw` (thêm `openclaw update --yes`). Máy production: chạy `kit apply --dry-run` trước, cập nhật OpenClaw ngoài giờ làm việc. Hoàn tác: copy lại `openclaw.json.<giờ>` trong `~/.config/openclaw-kit/backups/` rồi `openclaw gateway restart` (Gateway riêng: `openclaw --profile ipp gateway restart`). Chi tiết: docs/UPDATING.md.

## 11. Gặp lỗi thì xem
| Hiện tượng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| Cài bị treo, máy trông như đứng | hộp thoại needrestart bị ẩn | `sudo pkill whiptail`; chạy lại `install.sh` |
| `kit model-backup` báo "không đọc được danh sách tài khoản" | OpenClaw 2026.11.x đòi Gateway tắt; hoặc Gateway chưa bật | để kit tạm dừng (trả lời Enter); xem dòng lý do kit in; chạy tay `openclaw models auth list --agent main` |
| Dán token báo sai | dán nhầm chuỗi khác hoặc thiếu | đối chiếu độ dài và 4 ký tự đầu kit in; token bắt đầu `sk-ant-oat` |
| Bot báo "AI service needs a short break" | tài khoản hết lượt, đang chờ (cooldown) | thêm tài khoản dự phòng (mục 6); đợi hết cooldown |
| Agent nhân viên lỗi "No API key found for provider anthropic" | agent chủ chưa có token hoặc chưa `authInheritance` | dán token vào agent chủ; `kit run agent-web auth-owner` |
| Agent dừng "Sandbox image not found" | chưa dựng image | `kit sandbox-image` |
| Lệnh trên công ty thứ hai lại ghi vào công ty đầu | thiếu `--tenant` | luôn `kit --tenant <ten> ...` ; `kit use <ten>` |
| `kit doctor` cảnh báo docker hoặc linger | Docker chưa cài/chưa vào nhóm docker; dịch vụ user dừng khi đăng xuất | mục 0: cài Docker, `sudo usermod -aG docker $USER`, `sudo loginctl enable-linger $USER` |
| Bot Telegram không trả lời | chưa Start bot; ID sai; Gateway tắt | `kit alert-test`; `kit doctor`; `timeout 50 openclaw channels status --probe --json` |

## 12. Bảo mật tóm tắt
Repo không chứa bí mật; token và mật khẩu chỉ ở `secrets.env` chmod 600 của từng máy, nhập ẩn, không đặt trên dòng lệnh, không gửi qua chat. Đã lỡ lộ: đổi (rotate) ngay. Chi tiết: docs/SECURITY.md.
