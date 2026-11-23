# Cấp quyền model cho agent (token ủy quyền, không API key)

Áp dụng cho máy dùng module `agent-web`: agent của người dùng/khách chạy trong **sandbox Docker**. Hướng dẫn này đã **thử thật** trên VM Lab (OpenClaw 2026.11.7; xem docs/TESTING.md, mục "Sandbox Docker chạy thật").

## Nguyên tắc
1. **Mỗi công ty một token riêng**, tạo từ chính tài khoản Claude của công ty đó. Dùng chung một token thì thu hồi là mất hết, và mức dùng tính vào hạn mức/quản trị của chủ tài khoản.
2. **Không dùng runner `claude-cli`** cho agent khách. Lệnh `openclaw models auth login --method cli` gán `agentRuntime.id = claude-cli`; runner này chạy ngoài sandbox, `kit doctor` sẽ báo LỖI.
3. Dùng **runtime nhúng** (`agentRuntime.id = openclaw`) với **token setup-token** (hạn 1 năm).

## Các bước (trên máy khách, user của OpenClaw)
1. Cài Claude Code (chỉ để lấy token): `npm i -g @anthropic-ai/claude-code --prefix ~/.local`.
2. Chạy `claude setup-token`. Mở link in ra bằng trình duyệt đã đăng nhập **đúng tài khoản của công ty**, bấm cho phép, dán mã vào. Lệnh in token dạng `sk-ant-oat...` (chỉ hiện một lần; đừng gửi qua chat/email).
3. **Dừng Gateway** (lệnh nhập token đòi "exclusive offline state owner"): `systemctl --user stop openclaw-gateway`.
4. `openclaw models auth paste-token --provider anthropic --agent <id-agent> --expires-in 365d`, dán token.
5. Bật lại: `systemctl --user start openclaw-gateway`.
6. Đặt runtime nhúng cho model (áp dụng ngay, không cần khởi động lại):
   `openclaw config set 'agents.defaults.models["anthropic/*"].agentRuntime.id' openclaw`
   và cho từng model đã có mục riêng (xem `kit doctor` báo chỗ nào còn `claude-cli`).
7. `claude auth logout` (token setup-token độc lập với phiên đăng nhập CLI; đã thử: agent vẫn chạy sau khi đăng xuất).
8. `kit sandbox-image` rồi `kit doctor` phải "Tất cả OK".

Thu hồi token: claude.ai/settings/claude-code.

## Kiểm tra agent có thật sự trong sandbox
`openclaw agent --agent <id> --session-id thu-1 --json --message "xin chào"` rồi xem kết quả: `executionTrace.runner = embedded` và `sandbox: {mode: all, sandboxed: true}`; `docker ps` thấy container `openclaw-sbx-...`.

## Lưu ý
- Thiếu image thì agent **dừng hẳn** ("Sandbox image not found"), không chạy ngoài sandbox: an toàn nhưng cần `kit sandbox-image`.
- Mỗi lượt tốn khoảng 16k token (phần nền cố định ~8k: prompt hệ thống + schema công cụ). Xem số đo trong docs/TESTING.md khi chọn gói.

## Agent tạo qua webhook cần dùng chung credential (ĐÃ THỬ THẬT trên VM114, 24/11)
Mỗi agent nhân viên do kit tạo (webhook -> provision) có kho credential riêng, ban đầu TRỐNG: lượt đầu lỗi `No API key found for provider "anthropic"`.
Chọn MỘT agent làm "chủ credential" (nơi đã `paste-token`, thường là `main`) rồi cho mọi agent khác thừa hưởng:
```
openclaw config set agents.defaults.authInheritance '{"agentId":"main"}' --strict-json
```
Áp dụng không cần khởi động lại Gateway. Kiểm: gửi một lượt tới agent mới, phải trả lời được và `sandboxed: true`. Hủy: `openclaw config unset agents.defaults.authInheritance`.
Lưu ý: token dùng chung nghĩa là mọi nhân viên của công ty dùng chung hạn mức tài khoản đó. Muốn tách hạn mức thì `paste-token` riêng cho từng agent.

