#!/usr/bin/env bash
# Đăng nhập Claude bằng TRÌNH DUYỆT của người dùng (ủy quyền OAuth) rồi lưu token vào OpenClaw. Chạy lại được bất cứ lúc nào.
# Dùng:  bash scripts/claude-login.sh [--force]      (bằng user thường, trong terminal có bàn phím; không root)
#   1) `claude setup-token` in một đường dẫn đăng nhập -> mở đường dẫn đó trên trình duyệt của BẠN, đăng nhập tài khoản Claude của công ty,
#      bấm cho phép, copy mã hiện ra rồi dán lại vào terminal này.
#   2) Token dài hạn (1 năm) được bắt lại tự động và đưa vào OpenClaw (paste-token), không nằm trên dòng lệnh, file tạm bị xoá.
# KIT_AGENT (mặc định main), KIT_TOKEN_EXPIRES (mặc định 365d). Không dùng runner claude-cli; Claude Code chỉ dùng để lấy token.
set -uo pipefail
export PATH="$PATH:$HOME/.local/bin:$HOME/.npm-global/bin"
AGENT="${KIT_AGENT:-main}"; EXP="${KIT_TOKEN_EXPIRES:-365d}"; FORCE=0; [ "${1:-}" = --force ] && FORCE=1
say(){ printf '\n== %s\n' "$*"; }
die(){ echo "LỖI: $*" >&2; exit 1; }
[ "$(id -u)" -ne 0 ] || die "không chạy bằng root."
command -v openclaw >/dev/null || die "chưa có openclaw."
command -v claude >/dev/null || die "chưa có Claude Code. Cài: curl -fsSL https://claude.ai/install.sh | bash"
command -v script >/dev/null || die "thiếu lệnh script (gói util-linux)."
command -v python3 >/dev/null || die "thiếu python3."
{ [ -t 0 ] && [ -t 1 ]; } || die "cần chạy trong terminal có bàn phím (PuTTY/SSH), không chạy ngầm."
have_profile(){ openclaw models auth list --agent "$AGENT" 2>/dev/null | grep -qi 'anthropic'; }
if [ "$FORCE" = 0 ] && have_profile; then echo "Đã có đăng nhập Anthropic cho agent $AGENT (dùng --force để đăng nhập lại)."; exit 0; fi
umask 077; TMP="$(mktemp -d)"
cleanup(){ [ -d "$TMP" ] && { find "$TMP" -type f -exec shred -u {} + 2>/dev/null; rm -rf "$TMP"; }; }
trap cleanup EXIT
say "Đăng nhập Claude bằng trình duyệt"
cat <<'EOF'
Làm theo các bước hiện ra:
  - Copy đường dẫn https://claude.ai/oauth/authorize?... mở trên trình duyệt của bạn (máy này không có trình duyệt).
  - Đăng nhập tài khoản Claude CỦA CÔNG TY (không dùng tài khoản khác), bấm cho phép.
  - Trang web hiện một mã: copy rồi dán vào terminal này, nhấn Enter.
  - Cuối cùng Claude in ra token dài. KHÔNG chụp màn hình, KHÔNG gửi token cho ai. Script tự lấy token, bạn không cần copy.
EOF
script -qe -c "stty cols 500 2>/dev/null; claude setup-token" "$TMP/out"; RC=$?
printf '\033[2J\033[3J\033[H'   # xoá màn hình (và cuộn lại) để token không nằm lại trên màn hình
[ "$RC" -eq 0 ] || echo "LƯU Ý: claude setup-token thoát mã $RC."
TOKEN="$(sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g' "$TMP/out" 2>/dev/null | tr -d '\r' | grep -o 'sk-ant-[A-Za-z0-9_-]\{40,\}' | tail -1)"
if [ -z "$TOKEN" ]; then
  echo "Không tự bắt được token từ kết quả của Claude. Dán token vào đây (không hiện ký tự), rồi Enter; để trống để bỏ qua:"
  IFS= read -rs TOKEN; echo
  [ -n "$TOKEN" ] || die "chưa có token. Làm lại: bash $0 --force"
fi
case "$TOKEN" in sk-ant-*) ;; *) die "chuỗi nhập vào không giống token Claude (phải bắt đầu bằng sk-ant-).";; esac
echo "Đã lấy được token (độ dài ${#TOKEN} ký tự, không in ra)."
GW_WAS=0; systemctl --user is-active --quiet openclaw-gateway.service 2>/dev/null && GW_WAS=1
[ "$GW_WAS" = 1 ] && { say "Tạm dừng Gateway để ghi token"; systemctl --user stop openclaw-gateway.service; }
# paste-token hỏi token ở dấu nhắc (cần TTY): pty_feed.py đợi dấu nhắc hiện rồi mới đưa token vào qua pty, không đặt trên dòng lệnh (thử 2 lần).
PRC=1; OK=0
for TRY in 1 2; do
  printf '%s' "$TOKEN" | python3 "$(dirname "$(readlink -f "$0")")/pty_feed.py" "token" -- openclaw models auth paste-token --provider anthropic --agent "$AGENT" --expires-in "$EXP" >"$TMP/paste.log" 2>&1; PRC=$?
  if have_profile; then OK=1; break; fi
  [ "$TRY" = 1 ] && { echo "Lần 1 chưa lưu được, thử lại..."; sleep 3; }
done
unset TOKEN
if [ "$GW_WAS" = 1 ]; then systemctl --user start openclaw-gateway.service; for i in $(seq 1 10); do timeout 10 openclaw gateway health >/dev/null 2>&1 && break; sleep 4; done; fi
if [ "$OK" = 1 ]; then
  say "Xong: đã lưu đăng nhập Anthropic (hết hạn sau $EXP; nhớ gia hạn bằng: bash $0 --force)"
  openclaw models status 2>&1 | grep -iE 'anthropic|auth' | head -6 | cut -c1-160
  exit 0
fi
echo "Chưa lưu được token (paste-token mã $PRC). Phần cuối nhật ký (đã lọc mã token):" >&2
sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g' "$TMP/paste.log" | tr -d '\r' | sed -E 's/sk-ant-[A-Za-z0-9_-]+/sk-ant-***/g' | tail -8 | cut -c1-200 >&2
die "làm lại: bash $0 --force   (hoặc dán tay: openclaw models auth paste-token --provider anthropic --agent $AGENT --expires-in $EXP)"
