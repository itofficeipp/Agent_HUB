#!/usr/bin/env python3
"""Gan MCP rieng cho 1 agent tren Gateway agent-web. Chay tren VM Gateway, user javis.
Dung: gan_mcp.py <agent_id> <pham_vi: doc,viet,duyet,bao_cao,thu> <url>  |  --kiem (chi kiem tra)  |  --sua (dong bo deny cho moi agent, vd sau khi tao agent moi)
Co lap 2 lop: (1) cong sandbox cua agent CHI mo dung tool cua server minh (alsoAllow tung ten tool theo pham vi);
(2) deny server cua nguoi khac (de khong ket noi bang token nguoi khac); agent khong sandbox (main...) deny "cty_*".
Token doc tu ~/.config/agentweb/secrets/mcp_<agent>.token, khong in ra. In 1 dong ket qua: OK/LOI ..."""
import json, os, re, subprocess, sys
HOME = os.path.expanduser('~'); SFX = os.environ.get('KIT_SFX', ''); CFG = os.environ.get('KIT_OC_CFG', HOME + '/.openclaw/openclaw.json'); SEC = HOME + '/.config/agentweb' + SFX + '/secrets'
PROFILE = os.environ.get('AW_MCP_PROFILE_FILE', HOME + '/.config/agentweb' + SFX + '/mcp_profile.json')
try: _P = json.load(open(PROFILE))
except OSError: print('LOI thieu mcp_profile.json (' + PROFILE + ')'); sys.exit(2)
PFX = _P.get('server_prefix', 'mcp_')
QUYEN = _P['scopes']  # pham vi -> danh sach tool (tool moi tren server KHONG tu mo: them vao profile roi cap lai)
KEP = {tuple(k.split('+')): v for k, v in (_P.get('combined') or {}).items()}  # vd 'thu+viet': [tool can du 2 pham vi]
def cong_cu(pvs):
    out = [x for p in pvs for x in QUYEN[p]]
    for need, ts in KEP.items():
        if all(n in pvs for n in need): out += ts
    return list(dict.fromkeys(out))
def die(msg, rc=1): print('LOI', msg); sys.exit(rc)
def sv(a): return PFX + a
def cfg(): return json.load(open(CFG))
def oset(path, val):
    r = subprocess.run(['openclaw', 'config', 'set', path, json.dumps(val), '--strict-json'], capture_output=True, text=True, timeout=120)
    if r.returncode != 0: die(f'config set {path.split(".headers")[0]} rc={r.returncode}', 3)
def sandboxed(c, a, e):
    m = ((e.get('sandbox') or {}).get('mode') or ((c.get('agents') or {}).get('defaults') or {}).get('sandbox', {}).get('mode') or 'off')
    return m == 'all'
def kiem(c):
    """Tra ve danh sach vi pham. Agent X chi duoc thay tool <prefix>X__*; agent khong sandbox phai deny <prefix>*."""
    ents = (c.get('agents') or {}).get('entries') or {}; servers = set((c.get('mcp') or {}).get('servers') or {})
    bad = []
    g = ((c.get('tools') or {}).get('sandbox') or {}).get('tools') or {}
    for k in ('allow', 'alsoAllow'):
        for t in g.get(k) or []:
            if t.startswith(PFX) or t in ('bundle-mcp', 'group:plugins', '*'): bad.append(f'tools.sandbox.tools.{k} chung co {t}')
    for a, e in ents.items():
        t = e.get('tools') or {}; deny = t.get('deny') or []
        if not sandboxed(c, a, e):
            if PFX + '*' not in deny: bad.append(f'{a} khong sandbox ma chua deny <prefix>*')
            continue
        st = (t.get('sandbox') or {}).get('tools') or {}
        for k in ('allow', 'alsoAllow'):
            for x in st.get(k) or []:
                if x in ('bundle-mcp', 'group:plugins', '*') or (x.startswith(PFX) and not x.startswith(sv(a) + '__')):
                    bad.append(f'{a} sandbox.{k} mo {x}')
    return bad
def dong_bo():
    """Agent khong sandbox: deny <prefix>*. Agent sandbox: deny server <prefix> cua nguoi khac (khong ket noi bang token nguoi khac)."""
    c = cfg(); ents = (c.get('agents') or {}).get('entries') or {}
    servers = [s for s in ((c.get('mcp') or {}).get('servers') or {}) if s.startswith(PFX)]
    for b, e in ents.items():
        d = (e.get('tools') or {}).get('deny') or []
        if not sandboxed(c, b, e): want = [x for x in d if not x.startswith(PFX)] + [PFX + '*']
        else: want = [x for x in d if not (x.startswith(PFX) and x.endswith('__*'))] + [f'{s}__*' for s in servers if s != sv(b)]
        if want != d: oset(f'agents.entries.{b}.tools.deny', want)
def trang_thai():
    c = cfg(); ents = (c.get('agents') or {}).get('entries') or {}; S = (c.get('mcp') or {}).get('servers') or {}
    f = lambda a: SEC + '/mcp_' + a + '.token'
    tk = {a: (PFX + a) in S and os.path.exists(f(a)) and S[PFX + a].get('headers', {}).get('Authorization') == 'Bearer ' + open(f(a)).read().strip() for a in ents}
    ag = {a: len([x for x in ((((v.get('tools') or {}).get('sandbox') or {}).get('tools') or {}).get('alsoAllow') or []) if x.startswith(PFX)]) for a, v in ents.items()}
    sv_ = [x for x in S if x.startswith(PFX)]
    thieu = any(x != PFX + a and x + '__*' not in ((v.get('tools') or {}).get('deny') or []) for a, v in ents.items() if sandboxed(c, a, v) for x in sv_)
    print(json.dumps({'sv': list(S), 'tk': tk, 'ag': ag, 'thieu_deny': thieu}))
def main():
    if sys.argv[1:2] == ['--state']: trang_thai(); sys.exit(0)
    if sys.argv[1:2] == ['--count']: print(len(cong_cu([x.strip() for x in sys.argv[2].split(',') if x.strip()]))); sys.exit(0)
    if sys.argv[1:] == ['--sua']:
        dong_bo(); b = kiem(cfg()); print('OK dong bo' if not b else 'LOI co_lap ' + '; '.join(b)); sys.exit(1 if b else 0)
    if sys.argv[1:] == ['--kiem']:
        b = kiem(cfg()); print('OK kiem co lap' if not b else 'LOI co_lap ' + '; '.join(b)); sys.exit(1 if b else 0)
    if len(sys.argv) != 4: die('cach dung: gan_mcp.py <agent_id> <pham_vi> <url>', 2)
    a, pv, url = sys.argv[1], sys.argv[2], sys.argv[3]
    if not re.fullmatch(r'[a-z0-9_]{3,40}', a): die('agent_id sai', 2)
    if not re.fullmatch(r'https://[A-Za-z0-9.-]+(/[A-Za-z0-9._~/-]*)?|http://127\.0\.0\.1:\d+(/[A-Za-z0-9._~/-]*)?', url): die('url sai', 2)
    pvs = [x.strip() for x in pv.split(',') if x.strip()]
    if not pvs or any(x not in QUYEN for x in pvs): die(f'pham_vi la {pv}', 2)
    c = cfg(); ents = (c.get('agents') or {}).get('entries') or {}
    if a not in ents: die(f'{a} chua co tren gateway', 4)
    if not sandboxed(c, a, ents[a]): die(f'{a} khong chay sandbox, khong gan MCP', 4)
    tf = f'{SEC}/mcp_{a}.token'
    try: tok = open(tf).read().strip()
    except OSError: die(f'thieu token mcp cua {a}', 4)
    if not re.fullmatch(r'[A-Za-z0-9_.-]{20,200}', tok): die('token mcp sai dinh dang', 4)
    me = sv(a)
    dong_bo()  # 0) agent khong sandbox (main...) deny <prefix>* TRUOC khi them server
    # 1) server cua agent
    oset(f'mcp.servers.{me}', {'url': url, 'transport': 'streamable-http', 'headers': {'Authorization': 'Bearer ' + tok},
                               'connectionTimeoutMs': 10000, 'requestTimeoutMs': 30000})
    dong_bo()  # 2) moi agent khac deny server nay; agent nay deny server nguoi khac
    # 3) agent nay: mo dung tool theo pham vi (tool moi tren server khong tu mo)
    c = cfg(); t = c['agents']['entries'][a].get('tools') or {}
    st = (t.get('sandbox') or {}).get('tools') or {}
    keep = [x for x in (st.get('alsoAllow') or []) if not x.startswith(PFX)]
    oset(f'agents.entries.{a}.tools.sandbox.tools.alsoAllow', keep + [f'{me}__{x}' for x in cong_cu(pvs)])
    bad = kiem(cfg())
    if bad: die('co_lap ' + '; '.join(bad), 5)
    print(f'OK {a} {me} pham_vi={",".join(pvs)} tool={len(cong_cu(pvs))}')
main()
