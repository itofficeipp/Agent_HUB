# Thêm một công ty mới (checklist)

0. **Khoá đọc repo (mỗi công ty một khoá, CHỈ ĐỌC).** Chạy `bash install.sh <cty>` trên máy khách: nếu chưa clone được, installer tự tạo khoá riêng `~/.ssh/agent_hub_deploy` và in **khoá công khai** (một dòng `ssh-ed25519 ...`). Quản trị viên thêm dòng đó vào GitHub → repo Agent_HUB → Settings → Deploy keys, đặt tên theo công ty (vd `cty-a`), **KHÔNG tích "Allow write access"**; rồi chạy lại `bash install.sh <cty>`. Khoá riêng không rời máy khách. Công ty ngừng dùng: xoá đúng khoá đó trên GitHub, các công ty khác không bị ảnh hưởng. Chỉ có file install.sh (gửi cho khách) là đủ để bắt đầu.
1. Máy mới: `install.sh` (từ 0.3.7 tự cài OpenClaw và thiết lập mặc định không hỏi; không treo ở needrestart). Đăng nhập model bằng token ở bước sau; Telegram cấu hình riêng nếu cần.
2. `kit init <cty>`; `kit enable base`.
3. **Mặc định không cần n8n.** Chỉ khi công ty đã có/muốn dùng n8n: `kit enable n8n` sinh docker-compose mẫu (hoặc dùng n8n có sẵn), rồi dùng `AW_BACKEND=n8n` (tạo 2 Data table, xem docs/ARCHITECTURE.md).
4. `kit enable agent-web`: nơi nhận (`AW_BACKEND`), cổng, **`AW_EXPOSE` (tunnel | port | none) + `AW_PUBLIC_URL`**, Gateway local/SSH, hồ sơ MCP, thống kê token (`AW_STATS`).
4b. Công cụ cho agent (tuỳ chọn): `AW_TOOLS_WEB=yes` (+ `AW_TOOLS_BROWSER`, `AW_TOOLS_RUNTIME`, `AW_SANDBOX_IMAGE`, `AW_SEARCH_PROVIDER`, `AW_FULL_AGENTS`) để agent tìm web/mở trình duyệt; sau `kit apply` chạy `kit run agent-web open-tools --dry-run` xem trước rồi bỏ `--dry-run`. Provision tự áp cho agent mới.
5. MCP của công ty: sao `modules/agent-web/profiles/example.json` thành `<ten>.json`, điền tool; đặt `AW_MCP_PROFILE=<ten>`. Không dùng MCP: `none`.
6. `kit apply`; `kit run agent-web keygen` (tạo khóa trên Gateway); `kit run agent-web add-caller <web>` (ghi mật khẩu + HMAC key vào file 600, không in ra màn hình → đưa cho dev web rồi `shred -u` file); (chỉ khi dùng n8n) `kit run agent-web deploy-workflow`. Làm theo `expose/HUONG_DAN.md` để đưa ra Internet (docs/EXPOSE.md); web bên ngoài gọi `<AW_PUBLIC_URL>/webhook/<AW_WEBHOOK_PATH>`.
6b. **Báo lỗi về Telegram** (nên làm, nếu không lỗi chỉ ghi file log): tạo bot riêng ở @BotFather (/newbot), mở bot bấm Start, lấy ID của bạn ở @userinfobot, rồi `kit alert-bot` (nhập ID + token ẩn, kit gửi thử 1 tin). Thử lại bất cứ lúc nào: `kit alert-test`. `kit setup` cũng hỏi đúng các câu này.
7. Thử: `kit run agent-web test-webhook --user ... --password ... --secret ...` → kỳ vọng 201/200/409 (chỉ receiver tích hợp)/401/401/422/422/401.
8. Khi ổn: `kit apply` với `AW_AUTOSTART=yes` (bật timer provision) — hoặc `systemctl --user enable --now openclaw-kit-agentweb-provision.timer`.
9. `kit doctor`.

Ví dụ tham số không bí mật: `examples/congty.params.json` (`kit enable agent-web --params-file examples/congty.params.json`).
