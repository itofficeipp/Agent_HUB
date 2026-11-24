#!/usr/bin/env bash
# Cài openclaw-kit trên máy mới: Node + OpenClaw (nếu thiếu), rồi lấy kit và khởi tạo tenant.
# Dùng:  bash install.sh [tenant]        (chạy bằng user thường, không root)
set -euo pipefail
TENANT="${1:-}"
# Tên công ty: tự đổi sang chữ thường và kiểm tra NGAY (trước khi cài gì), để khỏi cài xong mới báo lỗi.
if [ -n "$TENANT" ]; then
  T_LOWER="$(printf '%s' "$TENANT" | tr '[:upper:]' '[:lower:]')"
  if [ "$T_LOWER" != "$TENANT" ]; then echo "Tên công ty đổi sang chữ thường: $TENANT -> $T_LOWER"; TENANT="$T_LOWER"; fi
  printf '%s' "$TENANT" | grep -Eq '^[a-z0-9][a-z0-9_-]{1,30}$' || { echo "Tên công ty không hợp lệ: chỉ a-z 0-9 _ - (2-31 ký tự), ví dụ: d2d, congty-abc"; exit 1; }
fi
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
# Cổng Gateway: mặc định 18789. Nếu đã có dịch vụ khác giữ cổng đó (vd. container Docker OpenClaw cũ) thì chọn cổng trống khác ngay
# từ đầu, thay vì cài xong mới thấy Gateway chết với mã 78. Gateway còn dùng cổng gốc+1 (sandbox) và gốc+2 (điều khiển trình duyệt).
port_busy(){ ss -ltn 2>/dev/null | awk '{print $4}' | grep -Eq "[:.]$1\$"; }
GW_PORT_ARGS=()
if [ -z "${OPENCLAW_GATEWAY_PORT:-}" ]; then
  GW_BASE=""
  for b in 18789 18795 18805 18815 18825; do
    if ! port_busy "$b" && ! port_busy $((b+2)); then GW_BASE="$b"; break; fi
  done
  [ -n "$GW_BASE" ] || { echo "LỖI: không tìm được cổng trống cho Gateway (đã thử 18789, 18795, 18805, 18815, 18825). Xem: ss -ltnp"; exit 1; }
  if [ "$GW_BASE" != 18789 ]; then
    echo "Cổng 18789 (hoặc 18791) đang có dịch vụ khác giữ, dùng cổng Gateway $GW_BASE"; GW_PORT_ARGS=(--gateway-port "$GW_BASE")
  elif port_busy 18790; then
    echo "LƯU Ý: cổng 18790 đang có dịch vụ khác giữ (Gateway dùng cổng này cho sandbox); nếu sandbox lỗi, cài lại với OPENCLAW_GATEWAY_PORT=18795"
  fi
fi
# Dịch vụ systemd còn nhãn 'failed' từ lần chạy trước làm 'gateway install' báo SERVICE_DEFINITION_UNKNOWN [inspection-failed]
# (đã tái hiện + sửa trên VM114): xoá nhãn này trước khi cài. Chỉ xoá nhãn, không đụng dữ liệu.
clear_failed_unit(){ systemctl --user reset-failed openclaw-gateway.service >/dev/null 2>&1 || true; systemctl --user daemon-reload >/dev/null 2>&1 || true; }
gw_wait_healthy(){ local i; for i in $(seq 1 ${1:-12}); do timeout 10 openclaw gateway health >/dev/null 2>&1 && return 0; sleep 4; done; return 1; }
GW_FAIL=0
# Thiết lập OpenClaw mặc định, KHÔNG hỏi: chế độ local, Gateway chỉ nghe loopback + token, bỏ qua đăng nhập model/kênh/skills
# (token Claude dán ở bước sau). KIT_ONBOARD=prompt: chạy wizard "openclaw onboard" có hỏi (cần chạy trong terminal; vẫn cài service + kiểm tra Gateway); KIT_ONBOARD=manual: bỏ qua, tự chạy onboard sau; KIT_ONBOARD_DAEMON=no để không cài service.
KIT_ONBOARD="${KIT_ONBOARD:-auto}"
if [ "$KIT_ONBOARD" = prompt ] && [ ! -t 0 ]; then echo "LƯU Ý: KIT_ONBOARD=prompt cần terminal có bàn phím (stdin không phải terminal), chuyển sang thiết lập mặc định."; KIT_ONBOARD=auto; fi
if [ "$KIT_ONBOARD" = prompt ] && [ ! -f "$HOME/.openclaw/openclaw.json" ]; then
  say "Chạy wizard OpenClaw (có hỏi)"
  clear_failed_unit
  ONB=(openclaw onboard "${GW_PORT_ARGS[@]}")
  if [ "${KIT_ONBOARD_DAEMON:-yes}" = yes ]; then ONB+=(--install-daemon); else ONB+=(--no-install-daemon); fi
  "${ONB[@]}" || echo "LƯU Ý: wizard lỗi/bị huỷ (sẽ thử sửa ở bước kiểm tra Gateway bên dưới)"
fi
if [ "$KIT_ONBOARD" = auto ] && [ ! -f "$HOME/.openclaw/openclaw.json" ]; then
  say "Thiết lập OpenClaw mặc định (không hỏi)"
  clear_failed_unit
  ONB=(openclaw onboard --non-interactive --accept-risk --mode local --flow quickstart --auth-choice skip --skip-channels --skip-skills --skip-search --skip-ui --skip-health "${GW_PORT_ARGS[@]}")
  if [ "${KIT_ONBOARD_DAEMON:-yes}" = yes ]; then ONB+=(--install-daemon); else ONB+=(--skip-daemon); fi
  "${ONB[@]}" </dev/null || echo "LƯU Ý: thiết lập tự động lỗi (sẽ thử sửa ở bước kiểm tra Gateway bên dưới)"
fi
# Kiểm tra Gateway THẬT SỰ chạy (trước đây script in 'Xong phần cài' kể cả khi dịch vụ chết).
if [ "$KIT_ONBOARD" != manual ] && [ "${KIT_ONBOARD_DAEMON:-yes}" = yes ]; then
  say "Kiểm tra Gateway"
  if ! gw_wait_healthy 12; then
    echo "Gateway chưa lên, thử sửa dịch vụ một lần (xoá nhãn failed rồi cài lại)..."
    clear_failed_unit
    openclaw gateway install 2>&1 | tail -5 || true
    openclaw gateway start 2>&1 | tail -3 || true
    gw_wait_healthy 8 || GW_FAIL=1
  fi
  if [ "$GW_FAIL" = 0 ]; then echo "Gateway đang chạy (health OK)."; fi
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
if [ "$GW_FAIL" = 1 ]; then
  cat <<EOF

LỖI: kit đã lấy về và tenant đã khởi tạo, nhưng Gateway OpenClaw KHÔNG chạy. CHƯA xong phần cài.
Xem nguyên nhân (chỉ đọc):
  systemctl --user show openclaw-gateway.service -p ActiveState,Result,ExecMainStatus
  journalctl --user -u openclaw-gateway.service -n 25 --no-pager | cut -c1-220
  ss -ltnp | grep -E ':1878|:1879'
Gỡ lỗi chính thức:  openclaw gateway uninstall; systemctl --user reset-failed openclaw-gateway.service; openclaw gateway install; openclaw gateway health
(đừng dùng --force hay sudo để lách; gửi kết quả cho người quản trị kit)
EOF
  exit 1
fi
cat <<EOF

Xong phần cài. OpenClaw đã được thiết lập mặc định (chưa có đăng nhập model). Bước tiếp:
  1) token Claude của công ty:  systemctl --user stop openclaw-gateway; openclaw models auth paste-token --provider anthropic --agent main --expires-in 365d; systemctl --user start openclaw-gateway
  2) kit setup <ten-cong-ty>            # hỏi từng thông số có gợi ý, xem trước, dựng, kiểm tra, nói bước tiếp
  (nhiều công ty/không hỏi: kit setup <ten> --yes --params-file file.json ;  chỉ kiểm máy: kit preflight)
EOF
