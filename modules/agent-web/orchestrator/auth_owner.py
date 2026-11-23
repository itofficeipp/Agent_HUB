#!/usr/bin/env python3
"""Đặt agents.defaults.authInheritance trên Gateway để MỌI agent nhân viên (tạo qua webhook) dùng chung credential model của
agent chủ (AW_AUTH_OWNER, mặc định main). Nếu không, agent mới có kho credential TRỐNG và lượt chat đầu báo
'No API key found for provider ...' (đã gặp khi thử thật trên VM114, 24/11).
- AW_AUTH_OWNER = main hoặc none: không đổi gì (main là mặc định của OpenClaw; none = tự quản).
- Chỉ ghi khi chưa đặt; nếu Gateway đã đặt giá trị KHÁC thì giữ nguyên và chỉ cảnh báo (không ghi đè lựa chọn của quản trị).
- Chạy lại nhiều lần an toàn. Thoát 0 = OK/bỏ qua; 1 = LỖI (agent chủ chưa tồn tại, đặt không thành)."""
import json, re, shlex, sys
import awconf as A

KEY = "agents.defaults.authInheritance"

def _val(out):
    s = (out or "").strip().strip('"')
    return s if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", s) else ""

def ensure():
    owner = (A.C.get("AW_AUTH_OWNER") or "main").strip()
    if owner in ("", "main", "none"):
        print("auth-owner: bỏ qua (AW_AUTH_OWNER=%s: không đổi cấu hình thừa hưởng credential)" % (owner or "main")); return 0
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", owner):
        print("LOI auth-owner: AW_AUTH_OWNER không hợp lệ: %r" % owner); return 1
    c = A.gw("openclaw config get %s.agentId" % KEY)
    cur = _val(c.stdout) if c.returncode == 0 else ""
    if cur == owner:
        print("OK auth-owner: Gateway đã thừa hưởng credential của '%s'" % owner); return 0
    if cur:
        print("CANH BAO auth-owner: Gateway đang đặt authInheritance='%s' (khác AW_AUTH_OWNER='%s'); giữ nguyên, không ghi đè. Đổi thủ công nếu muốn." % (cur, owner)); return 0
    ls = A.gw("openclaw agents list --json")
    if ls.returncode != 0 or ('"%s"' % owner) not in ls.stdout:
        print("LOI auth-owner: agent chủ credential '%s' chưa có trên Gateway. Tạo agent và dán token trước (docs/MODEL-AUTH.md), hoặc đặt AW_AUTH_OWNER=main/none." % owner); return 1
    s = A.gw("openclaw config set %s %s --strict-json" % (KEY, shlex.quote(json.dumps({"agentId": owner}))))
    chk = A.gw("openclaw config get %s.agentId" % KEY)
    if s.returncode != 0 or _val(chk.stdout) != owner:
        print("LOI auth-owner: đặt %s không thành: %s" % (KEY, (s.stdout + s.stderr).strip()[-200:])); return 1
    print("OK auth-owner: đã đặt %s.agentId='%s' (áp dụng không cần khởi động lại Gateway)" % (KEY, owner)); return 0

if __name__ == "__main__":
    sys.exit(ensure())
