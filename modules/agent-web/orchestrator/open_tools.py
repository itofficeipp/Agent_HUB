#!/usr/bin/env python3
"""Chạy mo_cong_cu.py trên Gateway theo AW_TOOLS_*. Dùng: kit run agent-web open-tools [--dry-run]. (kit apply đã đưa script + tuỳ chọn lên Gateway.)"""
import sys
import awconf as A
GDIR = A.C.get("AW_GATEWAY_DIR", "~/openclaw-kit-agentweb")
if A.C.get("AW_TOOLS_WEB") != "yes": sys.exit("AW_TOOLS_WEB=no: chưa bật mở công cụ (kit enable agent-web --set AW_TOOLS_WEB=yes rồi kit apply)")
c = A.gw(f"python3 {GDIR}/mo_cong_cu.py" + (" --dry-run" if "--dry-run" in sys.argv else ""), timeout=300)
print(c.stdout.strip()); sys.stderr.write(c.stderr[-300:]); sys.exit(c.returncode)
