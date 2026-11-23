#!/usr/bin/env bash
# post_apply của module agent-web. Dùng: post_apply.sh <AW_AUTOSTART yes|no> <AW_BACKEND local|n8n> <AW_STATS yes|no>
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
export KIT_HOME KIT_TENANT
AUTOSTART="${1:-no}"; BACKEND="${2:-local}"; STATS="${3:-no}"
U=openclaw-kit-agentweb
python3 "$here/deploy_gateway.py"
# agent mới cần dùng chung credential (authInheritance); lỗi ở đây không chặn apply, chỉ báo
python3 "$here/auth_owner.py" || echo "CANH BAO: chưa đặt được authInheritance (xem dòng LOI ở trên; kit doctor sẽ báo tiếp)"
if [ -z "${KIT_NO_SYSTEMD:-}" ] && command -v systemctl >/dev/null && [ -d /run/systemd/system ]; then
  systemctl --user daemon-reload
  if [ "$AUTOSTART" = "yes" ]; then
    systemctl --user enable --now $U-provision.timer; echo "timer provision BẬT"
    if [ "$BACKEND" = "local" ]; then systemctl --user enable $U-receiver.service; systemctl --user restart $U-receiver.service; echo "receiver BẬT"; fi
  else
    echo "dịch vụ CHƯA bật (AW_AUTOSTART=no). Khi đã có khoá + bên gọi:"
    echo "  systemctl --user enable --now $U-provision.timer"
    [ "$BACKEND" = "local" ] && echo "  systemctl --user enable --now $U-receiver.service"
  fi
  if [ "$STATS" = "yes" ]; then systemctl --user enable --now $U-stats.timer; echo "thống kê token BẬT"
  else systemctl --user disable --now $U-stats.timer >/dev/null 2>&1 || true; fi
  if command -v loginctl >/dev/null && ! loginctl show-user "$(id -un)" -p Linger 2>/dev/null | grep -q yes; then
    echo "GỢI Ý: dịch vụ user chỉ chạy khi còn đăng nhập. Để chạy nền khi khởi động lại: sudo loginctl enable-linger $(id -un)"
  fi
fi
if [ -f "$KIT_HOME/tenants/$KIT_TENANT/agent-web/expose/HUONG_DAN.md" ]; then
  echo "HƯỚNG DẪN đưa ra Internet: $KIT_HOME/tenants/$KIT_TENANT/agent-web/expose/HUONG_DAN.md"
fi
