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

# Ubuntu 22.04+: hook needrestart có thể mở hộp thoại whiptail ("Pending kernel upgrade") chờ phím, bị ẩn khi
# cài qua script => apt giữ khoá, máy trông như treo. Đặt cấu hình KHÔNG tương tác (chỉ cần chạy 1 lần, cần sudo).
fix_needrestart(){
  [ -d /etc/needrestart ] || return 0
  local f=/etc/needrestart/conf.d/99-openclaw-kit.conf
  [ -f "$f" ] && return 0
  command -v sudo >/dev/null || { echo "LƯU Ý: không có sudo, bỏ qua cấu hình needrestart (nếu cài bị treo: sudo pkill whiptail)"; return 0; }
  say "Cấu hình needrestart không hỏi khi cài gói (tránh treo ở hộp thoại 'Pending kernel upgrade'; có thể nhập mật khẩu sudo)"
  { sudo mkdir -p /etc/needrestart/conf.d && sudo tee "$f" >/dev/null <<'NRC'
# openclaw-kit: cài gói không bị treo ở hộp thoại needrestart. Xoá file này nếu muốn trở lại mặc định.
$nrconf{restart} = 'a';
$nrconf{ui} = 'NeedRestart::UI::stdio';
$nrconf{kernelhints} = -1;
$nrconf{ucodehints} = 0;
NRC
  } || echo "LƯU Ý: không ghi được $f; nếu cài bị treo: sudo pkill whiptail"
}
fix_needrestart
export DEBIAN_FRONTEND="${DEBIAN_FRONTEND:-noninteractive}" NEEDRESTART_MODE="${NEEDRESTART_MODE:-a}"
if ! command -v openclaw >/dev/null; then
  say "Cài OpenClaw (trình cài chính thức, tự cài Node nếu thiếu)"
  curl -fsSL https://openclaw.ai/install.sh | bash -s -- --no-onboard
fi
export PATH="$HOME/.npm-global/bin:$HOME/.local/bin:$PATH"
openclaw --version
# giữ PATH cho các lần đăng nhập sau (chỉ thêm 1 lần)
case "$(cat "$HOME/.bashrc" 2>/dev/null)" in *".npm-global/bin"*) ;; *)
  printf '\n# openclaw-kit\nexport PATH="$HOME/.local/bin:$HOME/.npm-global/bin:$PATH"\n' >> "$HOME/.bashrc"; echo "Đã thêm PATH vào ~/.bashrc (mở lại terminal để có hiệu lực)";; esac
# Thiết lập OpenClaw mặc định, KHÔNG hỏi: chế độ local, Gateway chỉ nghe loopback + token, bỏ qua đăng nhập model/kênh/skills
# (token Claude dán ở bước sau). KIT_ONBOARD=manual để tự chạy "openclaw onboard"; KIT_ONBOARD_DAEMON=no để không cài service.
if [ "${KIT_ONBOARD:-auto}" = auto ] && [ ! -f "$HOME/.openclaw/openclaw.json" ]; then
  say "Thiết lập OpenClaw mặc định (không hỏi)"
  ONB=(openclaw onboard --non-interactive --accept-risk --mode local --flow quickstart --auth-choice skip --skip-channels --skip-skills --skip-search --skip-ui --skip-health)
  if [ "${KIT_ONBOARD_DAEMON:-yes}" = yes ]; then ONB+=(--install-daemon); else ONB+=(--skip-daemon); fi
  "${ONB[@]}" </dev/null || echo "LƯU Ý: thiết lập tự động lỗi; chạy tay: openclaw onboard --install-daemon"
fi
# Khoá deploy CHỈ ĐỌC, riêng cho máy này (mỗi công ty một khoá): sinh tại chỗ, khoá riêng không rời máy.
DEPLOY_KEY="${KIT_DEPLOY_KEY:-$HOME/.ssh/agent_hub_deploy}"
SSH_CMD="ssh -i $DEPLOY_KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
if [ ! -d "$KIT_DIR/.git" ]; then
  say "Lấy kit từ $REPO"
  if [ -f "$DEPLOY_KEY" ]; then GIT_SSH_COMMAND="$SSH_CMD" git clone "$REPO" "$KIT_DIR"; else git clone "$REPO" "$KIT_DIR"; fi || {
    echo "Không clone được (repo private: máy này cần khoá deploy CHỈ ĐỌC)."
    if [ ! -f "$DEPLOY_KEY" ] && command -v ssh-keygen >/dev/null; then
      mkdir -p "$(dirname "$DEPLOY_KEY")"; chmod 700 "$(dirname "$DEPLOY_KEY")"
      ssh-keygen -q -t ed25519 -N "" -C "kit-$(hostname)-$(date +%F)" -f "$DEPLOY_KEY"
      echo "Đã tạo khoá riêng cho máy này: $DEPLOY_KEY (khoá riêng KHÔNG gửi đi đâu)."
    fi
    if [ -f "$DEPLOY_KEY.pub" ]; then
      echo; echo "Gửi DÒNG DƯỚI (khoá công khai) cho người quản trị repo để thêm vào GitHub -> Agent_HUB -> Settings -> Deploy keys (KHÔNG tích 'Allow write access'):"
      echo; cat "$DEPLOY_KEY.pub"; echo
      echo "Sau khi được thêm, chạy lại: bash install.sh $TENANT"
    else
      echo "Hoặc tự clone vào $KIT_DIR rồi chạy lại."
    fi
    exit 1; }
  # nhớ khoá cho các lần 'kit update' (git pull) sau này
  if [ -f "$DEPLOY_KEY" ]; then git -C "$KIT_DIR" config core.sshCommand "$SSH_CMD"; fi
fi
mkdir -p "$HOME/.local/bin"; ln -sf "$KIT_DIR/bin/kit" "$HOME/.local/bin/kit"
say "Khởi tạo"
if [ -n "$TENANT" ]; then "$KIT_DIR/bin/kit" init "$TENANT"; fi
cat <<EOF

Xong phần cài. OpenClaw đã được thiết lập mặc định (chưa có đăng nhập model). Bước tiếp:
  1) token Claude của công ty:  systemctl --user stop openclaw-gateway; openclaw models auth paste-token --provider anthropic --agent main --expires-in 365d; systemctl --user start openclaw-gateway
  2) kit setup <ten-cong-ty>            # hỏi từng thông số có gợi ý, xem trước, dựng, kiểm tra, nói bước tiếp
  (nhiều công ty/không hỏi: kit setup <ten> --yes --params-file file.json ;  chỉ kiểm máy: kit preflight)
EOF
