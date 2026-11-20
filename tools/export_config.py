#!/usr/bin/env python3
"""Xuất ~/.openclaw/openclaw.json đã che bí mật để XEM/ĐƯA VÀO MẪU (không bao giờ ghi bí mật).
Dùng: kit export-config [--in FILE] [--out FILE] [--drop agents.entries,bindings,channels] [--mask-ids]
- Giá trị của khoá có chữ token|secret|password|apikey|key|cookie|authorization|bearer -> "<REDACTED>"
- SecretRef ({source,provider,id}) giữ nguyên cấu trúc (id là đường dẫn, không phải giá trị)
- --drop: bỏ hẳn các nhánh riêng của một công ty (đường dẫn chấm)
- --mask-ids: che số nhận dạng dài (chat id Telegram, user id) -> "<ID>"
- Quét lần cuối bằng regex token phổ biến; còn sót thì KHÔNG ghi file, exit 2."""
import argparse, json, os, re, sys
KEY = re.compile(r"(token|secret|passw|api[-_]?key|apikey|cookie|authorization|bearer|credential|private)", re.I)
PATS = [re.compile(p) for p in (r"\d{6,12}:[A-Za-z0-9_-]{30,}", r"sk-[A-Za-z0-9_-]{20,}", r"cf[kut]_[A-Za-z0-9]{20,}", r"AKIA[0-9A-Z]{16}",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----", r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.", r"(?i)bearer\s+[A-Za-z0-9._-]{20,}")]
ap = argparse.ArgumentParser(); ap.add_argument("--in", dest="inp", default=os.path.expanduser("~/.openclaw/openclaw.json"))
ap.add_argument("--out"); ap.add_argument("--drop", default=""); ap.add_argument("--mask-ids", action="store_true"); o = ap.parse_args()
cfg = json.load(open(o.inp)); n = {"redacted": 0, "masked": 0}
def is_ref(v): return isinstance(v, dict) and {"source", "id"} <= set(v)
def walk(v, key=""):
    if is_ref(v): return v
    if isinstance(v, dict): return {k: walk(x, k) for k, x in v.items()}
    if isinstance(v, list): return [walk(x, key) for x in v]
    if isinstance(v, (str, int)) and not isinstance(v, bool):
        if KEY.search(key) and v not in ("", 0): n["redacted"] += 1; return "<REDACTED>"
        if isinstance(v, str):
            for p in PATS:
                if p.search(v): n["redacted"] += 1; return "<REDACTED>"
        if o.mask_ids and re.fullmatch(r"-?\d{7,}", str(v)): n["masked"] += 1; return "<ID>"
    return v
out = walk(cfg)
for path in [x for x in o.drop.split(",") if x]:
    d = out; ks = path.split(".")
    for k in ks[:-1]: d = d.get(k, {}) if isinstance(d, dict) else {}
    if isinstance(d, dict): d.pop(ks[-1], None)
txt = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
left = [p.pattern for p in PATS if p.search(txt)]
if left: sys.exit("TU CHOI ghi: con chuoi giong bi mat (" + left[0] + "). Kiem tra tay.")
if o.out:
    fd = os.open(o.out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f: f.write(txt)
    print(f"da ghi {o.out}: che {n['redacted']} gia tri bi mat, {n['masked']} id")
else: sys.stdout.write(txt)
