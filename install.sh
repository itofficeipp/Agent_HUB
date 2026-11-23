#!/usr/bin/env bash
# Cài openclaw-kit trên máy mới: Node + OpenClaw (nếu thiếu), rồi lấy kit và khởi tạo tenant.
# Dùng:  bash install.sh [tenant]        (chạy bằng user thường, không root)
set -euo pipefail
TENANT="${1:-}"
KIT_DIR="${KIT_DIR:-$HOME/openclaw-kit}"
REPO="${KIT_REPO:-git@github.com:itofficeipp/Agent_HUB.git}"   # repo private: cần khoá deploy/SSH; đổi bằng KIT_REPO=... nếu dùng bản fork
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
  say "Lấy kit từ $REPO"; git clone "$REPO" "$KIT_DIR" || { echo "Không clone được (repo private?). Cần khoá SSH có quyền đọc, hoặc tự clone vào $KIT_DIR rồi chạy lại."; exit 1; }
fi
mkdir -p "$HOME/.local/bin"; ln -sf "$KIT_DIR/bin/kit" "$HOME/.local/bin/kit"
say "Khởi tạo"
if [ -n "$TENANT" ]; then "$KIT_DIR/bin/kit" init "$TENANT"; fi
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) echo "LƯU Ý: thêm vào PATH: export PATH=\"\$HOME/.local/bin:\$PATH\" (và đưa vào ~/.bashrc)";; esac
cat <<EOF

Xong phần cài. Bước tiếp (OpenClaw cần được onboarding/đăng nhập model trước):
  openclaw onboard --install-daemon     # model, kênh Telegram, service Gateway
  kit setup <ten-cong-ty>               # hỏi từng thông số có gợi ý, xem trước, dựng, kiểm tra, nói bước tiếp
  (nhiều công ty/không hỏi: kit setup <ten> --yes --params-file file.json ;  chỉ kiểm máy: kit preflight)
EOF
