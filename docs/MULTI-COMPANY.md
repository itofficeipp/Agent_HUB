# Thêm một công ty thứ hai trên CÙNG máy (Gateway riêng)

Dùng khi công ty mới phải tách hẳn: dữ liệu, bot Telegram, dịch vụ, cổng riêng; lỗi hoặc cấu hình bên này không ảnh hưởng công ty đang chạy.
Cơ chế: **profile OpenClaw** (`openclaw --profile <p>`), xem docs OpenClaw `gateway/multiple-gateways.md`.

## Điều cần biết trước
- Tên profile: a-z 0-9 -, KHÔNG phải `default`/`main`. Cổng Gateway cách cổng mọi Gateway khác **≥ 120** (mặc định 18789; ví dụ công ty thứ hai: 19009).
- Bot Telegram **riêng** (@BotFather). Tài khoản Claude: chạy `kit --tenant <t> model-backup` và dán token (dùng chung tài khoản với công ty kia thì lượt dùng tính chung). Kit không tự sao chép đăng nhập giữa hai Gateway.
- Gateway SSH từ xa (`AW_GATEWAY_SSH`) chưa hỗ trợ profile; dùng Gateway local.
- CLI OpenClaw không tôn trọng biến `OPENCLAW_PROFILE` (đã kiểm), nên kit sinh wrapper `tenants/<t>/bin/openclaw`. Muốn gõ tay lệnh cho Gateway riêng: `openclaw --profile <p> ...` hoặc dùng wrapper đó.

## Các bước (ví dụ công ty ipp)
1. `kit init ipp --oc-profile ipp --oc-port 19009`
2. `kit --tenant ipp gateway-install` (hỏi xác nhận; tạo dịch vụ `openclaw-gateway-ipp`; không đụng Gateway mặc định)
3. `kit --tenant ipp setup ipp` (hoặc `enable base`, `enable agent-web`, `apply` với `--tenant ipp`): cổng receiver mặc định tự là 8787 + (19009 - 18789) = 9007; thư mục Gateway `~/openclaw-kit-agentweb-ipp`; khoá/bí mật `~/.config/agentweb-ipp`; unit `openclaw-kit-agentweb-ipp-*`.
4. `kit --tenant ipp model-backup` (tài khoản Claude cho Gateway này), `kit --tenant ipp alert-bot` (bot Telegram).
5. `kit --tenant ipp run agent-web keygen`, `add-caller <web>`, rồi `kit --tenant ipp doctor`.
- Tên miền/tunnel (`AW_PUBLIC_URL`) riêng cho công ty này, trỏ về cổng receiver 9007.
- Luôn thêm `--tenant ipp` (hoặc `kit use ipp`) để khỏi nhầm sang công ty kia.

## Kiểm
- `systemctl --user status openclaw-gateway-ipp`; `openclaw --profile ipp gateway status`
- Gateway cũ không đổi: `systemctl --user status openclaw-gateway`
