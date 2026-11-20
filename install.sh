#!/usr/bin/env bash
# Cài openclaw-kit trên máy mới: Node + OpenClaw (nếu thiếu), rồi lấy kit và khởi tạo tenant.
# Dùng:  bash install.sh [tenant]        (chạy bằng user thường, không root)
set -euo pipefail
TENANT="${1:-}"
KIT_DIR="${KIT_DIR:-$HOME/openclaw-kit}"
REPO="${KIT_REPO:-}"      # vd: git@github.com:<tai-khoan>/openclaw-kit.git  (bắt buộc nếu chưa clone)
say(){ printf '\n== %s\n' "$*"; }
[ "$(id -u)" -ne 0 ] || { echo "Không chạy bằng root."; exit 1; }
command -v git >/dev/null || { echo "Thiếu git: sudo apt install -y git"; exit 1; }
command -v python3 >/dev/null || { echo "Thiếu python3"; exit 1; }
if ! command -v openclaw >/dev/null; then
  say "Cài OpenClaw (trình cài chính thức, tự cài Node nếu thiếu)"
  curl -fsSL https://openclaw.ai/install.sh | bash
  export PATH="$HOME/.npm-global/bin:$HOME/.local/bin:$PATH"
fi
openclaw --version
if [ ! -d "$KIT_DIR/.git" ]; then
  [ -n "$REPO" ] || { echo "Đặt KIT_REPO=<url git của openclaw-kit> hoặc tự clone vào $KIT_DIR"; exit 1; }
  say "Lấy kit"; git clone "$REPO" "$KIT_DIR"
fi
mkdir -p "$HOME/.local/bin"; ln -sf "$KIT_DIR/bin/kit" "$HOME/.local/bin/kit"
say "Khởi tạo"
if [ -n "$TENANT" ]; then "$KIT_DIR/bin/kit" init "$TENANT"; fi
cat <<EOF

Xong phần cài. Bước tiếp (OpenClaw cần được onboarding/đăng nhập model trước):
  openclaw onboard --install-daemon     # model, kênh Telegram, service Gateway
  kit init <ten-cong-ty>                # nếu chưa truyền tenant
  kit enable base                       # hỏi tên công ty, múi giờ, model...
  kit enable agent-web                  # hỏi cách ra Internet (tunnel/port), Gateway, hồ sơ MCP...  (n8n là tuỳ chọn: kit enable n8n)
  kit apply --dry-run && kit apply
  kit doctor
EOF
