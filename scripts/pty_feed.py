#!/usr/bin/env python3
"""Chạy một lệnh đòi nhập bí mật ở dấu nhắc (cần TTY), đưa bí mật vào qua pty khi dấu nhắc đã hiện. Bí mật đọc từ stdin, KHÔNG đặt trên dòng lệnh.
Dùng:  printf %s "$SECRET" | pty_feed.py <chuoi-dau-nhac> -- lenh arg...      (thoát với mã của lệnh; nhật ký in ra stdout, đã che bí mật)"""
import fcntl, os, pty, re, select, struct, sys, termios, time
i = sys.argv.index("--")
prompt = sys.argv[1].encode(); cmd = sys.argv[i + 1:]
secret = sys.stdin.read().strip().encode()
pid, fd = pty.fork()
if pid == 0:
    fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack("HHHH", 50, 200, 0, 0))
    os.execvp(cmd[0], cmd)
buf = b""; sent = False; t0 = time.time(); status = None
while True:
    r, _, _ = select.select([fd], [], [], 0.5)
    if r:
        try: d = os.read(fd, 4096)
        except OSError: d = b""
        if not d: break
        buf += d
        if not sent and prompt.lower().replace(b" ", b"") in re.sub(rb"\x1b\[[0-9;?]*[a-zA-Z]|\s", b"", buf).lower():
            time.sleep(0.4); os.write(fd, secret + b"\r"); sent = True
    if not sent and time.time() - t0 > 90:
        os.kill(pid, 15); break
    p, st = os.waitpid(pid, os.WNOHANG)
    if p:
        status = st
        while True:
            try:
                if not select.select([fd], [], [], 0.2)[0]: break
                d = os.read(fd, 4096)
                if not d: break
                buf += d
            except OSError: break
        break
if status is None:
    try: status = os.waitpid(pid, 0)[1]
    except ChildProcessError: status = 1 << 8
sys.stdout.write(buf.replace(secret, b"***").decode("utf-8", "replace")); sys.stdout.write("\n[pty_feed] da_gui_bi_mat=%s\n" % sent)
sys.exit(os.waitstatus_to_exitcode(status) if status is not None else 1)
