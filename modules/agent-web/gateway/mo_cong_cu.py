#!/usr/bin/env python3
"""Mo them cong cu cho agent nguoi dung tren Gateway agent-web (idempotent). Chay tren may Gateway.
Doc tuy chon tu ~/.config/agentweb/mo_cong_cu.json (do deploy_gateway ghi tu tham so AW_TOOLS_*):
  web (bool)       agent duoc dung web_search + web_fetch
  browser (bool)   them trinh duyet (browser) cho agent; bat sandbox.browser; chan nhom UI khac; sandbox.deny cac kenh/nen tang
  runtime (bool)   bo nhom group:runtime khoi deny (agent duoc exec/process/read/write trong SANDBOX cua no)
  sandbox_image    image docker sandbox (bo trong = khong doi)
  search_provider  nha cung cap web search toan cuc (bo trong = khong doi)
  full_agents      danh sach agent_id duoc cap quyen rong: KHONG ghi de sandbox.deny
Dung: mo_cong_cu.py [--dry-run]    In 'OK ...' / 'LOI ...' tung thay doi, cuoi cung 'XONG' (exit 1 neu co LOI).
Chi dong vao agent co sandbox.mode=all. Khong tu bat gi khi tuy chon deu tat."""
import json, os, subprocess, sys
HOME = os.path.expanduser("~")
CFG = os.environ.get("AW_OPENCLAW_CFG", HOME + "/.openclaw/openclaw.json")
OPT = os.environ.get("AW_MO_CONG_CU_FILE", HOME + "/.config/agentweb/mo_cong_cu.json")
DRY = "--dry-run" in sys.argv
try: O = json.load(open(OPT))
except OSError: O = {}
WEB = bool(O.get("web")); BROWSER = bool(O.get("browser")); RUNTIME = bool(O.get("runtime"))
IMAGE = O.get("sandbox_image") or ""; SEARCH = O.get("search_provider") or ""
FULL = {x for x in (O.get("full_agents") or []) if x}
UI_KHAC = ["screen", "terminal", "canvas", "progress_card", "show_widget"]
SB_DENY = ["canvas", "computer", "mobile_ui", "nodes", "automations", "gateway", "feishu", "googlechat", "nostr", "buzz", "msteams", "mattermost", "nextcloud-talk", "matrix", "raft", "a2a", "line", "zalo", "clickclack", "x", "zalouser", "sms", "synology-chat", "tlon", "discord", "imessage", "irc", "reef", "signal", "slack", "telegram", "twitch", "whatsapp"]
loi = 0
def oset(k, v):
    global loi
    if DRY: print("SE " + k, json.dumps(v)[:120]); return
    r = subprocess.run(["openclaw", "config", "set", k, json.dumps(v), "--strict-json"], capture_output=True, text=True, timeout=120)
    if r.returncode != 0: loi += 1
    print(("OK " if r.returncode == 0 else "LOI ") + k, "" if r.returncode == 0 else r.stderr.strip()[-300:])
def cfg(): return json.load(open(CFG))
c = cfg()
if not (WEB or BROWSER or RUNTIME or IMAGE or SEARCH): print("XONG (tat ca tuy chon deu tat, khong lam gi)"); sys.exit(0)
if SEARCH and (((c.get("tools") or {}).get("web") or {}).get("search") or {}).get("provider") != SEARCH: oset("tools.web.search.provider", SEARCH)
sb = (c.get("agents", {}).get("defaults") or {}).get("sandbox") or {}
if IMAGE and (sb.get("docker") or {}).get("image") != IMAGE: oset("agents.defaults.sandbox.docker.image", IMAGE)
if BROWSER and not (sb.get("browser") or {}).get("enabled"): oset("agents.defaults.sandbox.browser.enabled", True)
for a, e in cfg().get("agents", {}).get("entries", {}).items():
    if ((e.get("sandbox") or {}).get("mode")) != "all": continue
    t = e.get("tools") or {}; deny = t.get("deny") or []
    nd = list(deny)
    if RUNTIME: nd = [x for x in nd if x != "group:runtime"]
    if BROWSER and "group:ui" in nd: nd = [x for x in nd if x != "group:ui"] + [x for x in UI_KHAC if x not in nd]
    if nd != deny: oset(f"agents.entries.{a}.tools.deny", nd)
    st = (t.get("sandbox") or {}).get("tools") or {}
    aa = st.get("alsoAllow") or []
    na = [x for x in (["web_search", "web_fetch"] if WEB else []) + (["browser"] if BROWSER else []) if x not in aa]
    if na: oset(f"agents.entries.{a}.tools.sandbox.tools.alsoAllow", na + aa)
    if a in FULL: continue  # agent duoc cap quyen rong: khong ghi de sandbox.deny
    if BROWSER and st.get("deny") != SB_DENY: oset(f"agents.entries.{a}.tools.sandbox.tools.deny", SB_DENY)
print("XONG" if not loi else f"XONG co {loi} LOI"); sys.exit(1 if loi else 0)
