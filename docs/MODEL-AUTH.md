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
Từ kit 0.3.6 việc này TỰ ĐỘNG: tham số `AW_AUTH_OWNER` (mặc định `main`) + `kit apply agent-web` hoặc `provision` tự đặt `authInheritance`; `kit doctor` báo LỖI nếu agent chủ chưa có token. Chỉ cần: (1) dán token vào agent chủ, (2) nếu chủ không phải `main`: `kit enable agent-web --set AW_AUTH_OWNER=<id agent>` rồi `kit apply agent-web` (hoặc `kit run agent-web auth-owner`). Phần dưới là cách làm tay / giải thích.
Mỗi agent nhân viên do kit tạo (webhook -> provision) có kho credential riêng, ban đầu TRỐNG: lượt đầu lỗi `No API key found for provider "anthropic"`.
Chọn MỘT agent làm "chủ credential" (nơi đã `paste-token`, thường là `main`) rồi cho mọi agent khác thừa hưởng:
```
openclaw config set agents.defaults.authInheritance '{"agentId":"main"}' --strict-json
```
Áp dụng không cần khởi động lại Gateway. Kiểm: gửi một lượt tới agent mới, phải trả lời được và `sandboxed: true`. Hủy: `openclaw config unset agents.defaults.authInheritance`.
Lưu ý: token dùng chung nghĩa là mọi nhân viên của công ty dùng chung hạn mức tài khoản đó. Muốn tách hạn mức thì `paste-token` riêng cho từng agent.



## Tài khoản dự phòng (tài khoản 1 hết lượt thì chuyển tài khoản 2)
Chạy một lệnh (trong terminal, trên máy có OpenClaw):
```
kit model-backup            # agent tổng (mặc định); đổi: --agent <id>
```
Kit hỏi token tài khoản 2 (nhập ẩn). Lấy token: đăng nhập ĐÚNG tài khoản Claude số 2 trên trình duyệt, chạy `claude setup-token`, dán mã về, copy chuỗi `sk-ant-oat01-...`. Kit tự dừng Gateway, lưu profile `anthropic:tk2` (không đụng profile cũ), đặt thứ tự tài khoản cũ trước rồi dự phòng, đọc lại kiểm, bật lại Gateway. Chạy lại để thêm tài khoản 3 (`tk3`).
- Cách OpenClaw chạy: dùng tài khoản đầu trước; bị rate_limit/hết hạn mức thì tạm bỏ nó theo thời gian nhà cung cấp báo (cooldown) và dùng tài khoản kế; hết cooldown quay lại. Mỗi phiên chat giữ một tài khoản (giữ bộ nhớ đệm); `/new` chọn lại. Xem: `openclaw models auth list --agent main`.
- Không có thứ tự thì OpenClaw xoay vòng theo lần dùng, hai tài khoản bị dùng xen kẽ: nên luôn đặt thứ tự (lệnh trên làm sẵn).
- Làm tay: dừng Gateway; `openclaw models auth paste-token --provider anthropic --agent main --profile-id anthropic:tk2 --expires-in 365d`; `openclaw models auth order set --provider anthropic --agent main anthropic:manual anthropic:tk2`; bật Gateway. Đừng gõ nguyên dấu ngoặc nhọn kiểu <ten-profile> trong lệnh (bash coi là chuyển hướng).
- Agent nhân viên thừa hưởng credential từ agent chủ qua `authInheritance`: hai token để cùng ở agent chủ. CHƯA kiểm agent nhân viên có theo thứ tự dự phòng.
- Hai tài khoản nên cùng một chủ/công ty (xem Nguyên tắc 1 ở trên).
