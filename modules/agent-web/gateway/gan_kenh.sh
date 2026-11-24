#!/bin/bash
# Gan bot Telegram (va luu MCP token) cho 1 agent tren Gateway agent-web. Chay tren VM Gateway, user javis.
# Dung: echo '<json>' | gan_kenh.sh
#   json: {"agent_id","telegram_user_id","telegram_bot_username","bi_mat":"<base64 RSA-OAEP-SHA256 cua {\"tg\":..,\"mcp\":..}>"}
# Khong bao gio in token. Ket qua dong cuoi: OK <agent_id> @<bot> | LOI <ma> <mo ta>
set -euo pipefail; umask 077
AWD=$HOME/.config/agentweb${KIT_SFX:-}; OCCFG=${KIT_OC_CFG:-$HOME/.openclaw/openclaw.json}
KEY=${AGENTWEB_KEY:-$AWD/bi_mat.pem}
SEC=$AWD/secrets; mkdir -p "$SEC"; chmod 700 "$SEC"
J=$(cat)
g(){ python3 -c 'import json,sys;v=json.loads(sys.argv[1]).get(sys.argv[2]);print("" if v is None else v)' "$J" "$1"; }
ID=$(g agent_id); TUID=$(g telegram_user_id); BOT=$(g telegram_bot_username); BM=$(g bi_mat)
die(){ echo "LOI $1 $2"; exit "${3:-1}"; }
[[ "$ID" =~ ^u_[a-z0-9_]{3,60}$ ]] || die agent_id "khong hop le"
[[ "$TUID" =~ ^[1-9][0-9]{4,14}$ ]] || die telegram_user_id "khong hop le"
[[ "$BOT" =~ ^[A-Za-z][A-Za-z0-9_]{3,30}[Bb][Oo][Tt]$ ]] || die telegram_bot_username "khong hop le"
openclaw agents list --json 2>/dev/null | grep -q "\"$ID\"" || die agent_chua_co "$ID" 3
# 1) Giai ma (chi tren may nay co khoa bi mat)
P=$(mktemp); trap 'shred -u "$P" 2>/dev/null || rm -f "$P"' EXIT
printf '%s' "$BM" | base64 -d 2>/dev/null | openssl pkeyutl -decrypt -inkey "$KEY" -pkeyopt rsa_padding_mode:oaep -pkeyopt rsa_oaep_md:sha256 -pkeyopt rsa_mgf1_md:sha256 > "$P" 2>/dev/null || die giai_ma "khong giai ma duoc bi_mat" 4
TGF=$SEC/tg_$ID.token; MCPF=$SEC/mcp_$ID.token
python3 - "$P" "$TGF" "$MCPF" <<'PY' || die bi_mat "noi dung sai dinh dang" 4
import json,sys,os,re
d=json.load(open(sys.argv[1]))
tg=d.get('tg') or ''; mcp=d.get('mcp') or ''
if not re.fullmatch(r'\d{6,12}:[A-Za-z0-9_-]{30,60}',tg): sys.exit(1)
def w(p,v):
    fd=os.open(p+'.tmp',os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600); os.write(fd,v.encode()); os.close(fd); os.replace(p+'.tmp',p)
w(sys.argv[2],tg)
if mcp: w(sys.argv[3],mcp)
PY
# 2) Kiem bot that bang getMe, username phai khop
R=$(curl -s -m 20 -A curl/8.5.0 "https://api.telegram.org/bot$(cat "$TGF")/getMe" || true)
U=$(python3 -c 'import json,sys
try:
  d=json.loads(sys.argv[1]); print(d["result"]["username"] if d.get("ok") else "")
except Exception: print("")' "$R")
[ -n "$U" ] || { rm -f "$TGF"; die bot_token "Telegram tu choi token (getMe khong ok)" 5; }
[ "${U,,}" = "${BOT,,}" ] || { rm -f "$TGF"; die bot_username "token thuoc @$U, khong phai @$BOT" 5; }
# 3) Sao luu config, gan account + binding
mkdir -p $AWD/bk; cp $OCCFG $AWD/bk/openclaw.json.$(date +%Y%m%d%H%M%S).before-$ID
ACC=$ID
python3 - "$ACC" "$TGF" "$TUID" "$U" > /tmp/patch_$ID.json <<'PY'
import json,sys
acc,tf,uid,u=sys.argv[1:]
print(json.dumps({"channels":{"telegram":{"enabled":True,"dmPolicy":"allowlist","groupPolicy":"disabled","allowFrom":[],
  "accounts":{acc:{"enabled":True,"name":"@"+u,"tokenFile":tf,"dmPolicy":"allowlist","allowFrom":[uid],"groupPolicy":"disabled"}}}}}))
PY
openclaw config patch --stdin < /tmp/patch_$ID.json > /tmp/patch_$ID.out 2>&1 || { tail -3 /tmp/patch_$ID.out; die config_patch "bi tu choi" 6; }
grep -qi declined /tmp/patch_$ID.out && { tail -3 /tmp/patch_$ID.out; die config_patch "declined" 6; }
# bindings chua dat -> CLI tra {"ok":false,...} + rc!=0: coi nhu danh sach rong
B=$(openclaw config get bindings --json 2>/dev/null) || B='[]'
NB=$(python3 -c 'import json,sys
try: b=json.loads(sys.argv[1] or "[]")
except Exception: b=[]
if not isinstance(b,list): b=[]
acc,ag=sys.argv[2],sys.argv[3]
b=[x for x in b if not (x.get("match",{}).get("channel")=="telegram" and x.get("match",{}).get("accountId")==acc)]
b.insert(0,{"agentId":ag,"match":{"channel":"telegram","accountId":acc}})
print(json.dumps(b))' "$B" "$ACC" "$ID") || die bindings "khong doc duoc bindings" 6
openclaw config set bindings "$NB" --strict-json >/dev/null 2>&1 || die bindings "khong ghi duoc" 6
# 4) Doc lai
python3 - "$ACC" "$ID" "$TUID" <<'PY' || die doc_lai "config khong dung" 7
import json,os,sys
c=json.load(open(os.environ.get('KIT_OC_CFG') or os.path.expanduser('~/.openclaw/openclaw.json')))
acc,ag,uid=sys.argv[1:]
a=c["channels"]["telegram"]["accounts"][acc]
assert a["allowFrom"]==[uid] and a["dmPolicy"]=="allowlist" and a["tokenFile"].endswith(".token")
assert any(b["agentId"]==ag and b["match"].get("accountId")==acc for b in c.get("bindings",[]))
PY
rm -f /tmp/patch_$ID.json /tmp/patch_$ID.out
echo "OK $ID @$U"
