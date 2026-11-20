#!/usr/bin/env python3
"""Tạo cặp khóa RSA trên máy Gateway (khóa bí mật không rời máy đó). Khóa công khai về orchestrator để n8n mã hóa token bot/MCP.
Dùng: keygen.py   (idempotent: đã có khóa thì chỉ lấy lại khóa công khai)"""
import os, sys
import awconf as A
c = A.gw('set -e; umask 077; mkdir -p ~/.config/agentweb; K=~/.config/agentweb/bi_mat.pem; '
         '[ -f "$K" ] || openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 -out "$K"; openssl pkey -in "$K" -pubout')
if c.returncode != 0 or "BEGIN PUBLIC KEY" not in c.stdout: sys.exit("LOI keygen: " + c.stderr[-300:])
os.makedirs(A.AWDIR, exist_ok=True)
open(A.AWDIR + "/gateway_pub.pem", "w").write(c.stdout.strip() + "\n")
print("OK khoa cong khai:", A.AWDIR + "/gateway_pub.pem  (khoa bi mat o ~/.config/agentweb/bi_mat.pem tren may Gateway)")
