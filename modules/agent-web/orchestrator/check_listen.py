#!/usr/bin/env python3
"""Kiểm cổng receiver chỉ nghe loopback (127.0.0.1/::1), không lộ ra 0.0.0.0. Đọc /proc/net/tcp{,6}, không cần ss/netstat.
Dùng: check_listen.py <cổng>.  Thoát 0 nếu chỉ nghe loopback; 1 nếu nghe ra ngoài hoặc không nghe."""
import sys
port = int(sys.argv[1]); LOOP4 = "0100007F"; LOOP6 = "00000000000000000000000001000000"
seen = []
for f, loop in (("/proc/net/tcp", LOOP4), ("/proc/net/tcp6", LOOP6)):
    try: lines = open(f).read().splitlines()[1:]
    except OSError: continue
    for l in lines:
        p = l.split()
        addr, prt = p[1].split(":")
        if p[3] == "0A" and int(prt, 16) == port: seen.append((addr, addr == loop))
if not seen: sys.exit(f"không có tiến trình nghe cổng {port} (receiver chưa chạy?)")
bad = [a for a, ok in seen if not ok]
if bad: sys.exit(f"cổng {port} đang nghe ra ngoài ({bad[0]}); phải là 127.0.0.1 (AW_LISTEN_HOST)")
print(f"cổng {port} chỉ nghe loopback")
