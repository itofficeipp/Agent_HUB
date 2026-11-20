// Xác thực Basic Auth (nhiều user) + HMAC + kiểm tham số. USERS do build.py thay vào (chỉ có hash mật khẩu, không có mật khẩu gốc).
const USERS = __USERS__; // { user: { h: sha256(SALT+':'+pass), hmac: 'bat_buoc'|'tuy_chon', secret } }
const SALT = '__SALT__';
const it = $input.first();
const h = it.json.headers || {};
const fail = (code, loi) => [{ json: { http_status: code, out: { ok: false, loi } } }];
const crypto = require('crypto');
const eq = (a, b) => a.length === b.length && crypto.timingSafeEqual(Buffer.from(a), Buffer.from(b));
// 1) Basic Auth
const au = String(h['authorization'] || '');
const m = au.match(/^Basic\s+([A-Za-z0-9+\/=]+)$/i);
if (!m) return fail(401, 'thieu_xac_thuc');
const dec = Buffer.from(m[1], 'base64').toString('utf8');
const i = dec.indexOf(':');
const user = i > 0 ? dec.slice(0, i) : '', pass = i > 0 ? dec.slice(i + 1) : '';
const u = Object.prototype.hasOwnProperty.call(USERS, user) ? USERS[user] : null;
const ph = crypto.createHash('sha256').update(SALT + ':' + pass, 'utf8').digest('hex');
if (!u || !eq(ph, u.h)) return fail(403, 'sai_user_hoac_mat_khau');
// 2) HMAC: bắt buộc hay tùy chọn tùy user
const ts = String(h['x-timestamp'] || '');
const sig = String(h['x-signature'] || '').toLowerCase().replace(/^sha256=/, '');
let raw;
try { raw = (await this.helpers.getBinaryDataBuffer(0, 'data')).toString('utf8'); }
catch (e) { raw = JSON.stringify(it.json.body || {}); }
if (sig || u.hmac === 'bat_buoc') {
  if (!sig) return fail(401, 'thieu_x-signature');
  if (!/^\d{10}$/.test(ts)) return fail(401, 'thieu_hoac_sai_x-timestamp');
  if (Math.abs(Date.now() / 1000 - Number(ts)) > 300) return fail(401, 'x-timestamp_lech_qua_5_phut');
  const exp = crypto.createHmac('sha256', u.secret).update(ts + '.' + raw, 'utf8').digest('hex');
  if (!eq(sig, exp)) return fail(401, 'sai_chu_ky');
}
let b;
try { b = JSON.parse(raw); } catch (e) { return fail(422, 'body_khong_phai_json'); }
const s = (v) => (v === undefined || v === null) ? '' : String(v).trim();
const user_id = s(b.user_id), ho_ten = s(b.ho_ten), email = s(b.email).toLowerCase(), phong_ban = s(b.phong_ban);
if (!/^[A-Za-z0-9_.@-]{1,64}$/.test(user_id)) return fail(422, 'user_id_bat_buoc_1-64_ky_tu_A-Z_0-9_._@-');
if (!ho_ten || ho_ten.length > 200) return fail(422, 'ho_ten_bat_buoc_toi_da_200');
if (email && (email.length > 200 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))) return fail(422, 'email_sai_dinh_dang');
if (phong_ban.length > 200) return fail(422, 'phong_ban_toi_da_200');
const slug = user_id.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 40) || 'x';
const agent_id = 'u_' + slug + '_' + crypto.createHash('sha256').update(user_id).digest('hex').slice(0, 8);
// 3) Telegram (tùy chọn, đủ cả 3 trường) + MCP (tùy chọn). Token được mã hóa bằng khóa công khai của VM Gateway; n8n không lưu token dạng thường.
const tg_bot = s(b.telegram_bot_username).replace(/^@/, ''), tg_uid = s(b.telegram_user_id), tg_tok = s(b.telegram_bot_token);
const mcp_url = s(b.mcp_url), mcp_tok = s(b.mcp_token), mcp_pv = s(b.mcp_pham_vi).toLowerCase(), mcp_hh = s(b.mcp_het_han);
const coTg = !!(tg_bot || tg_uid || tg_tok), coMcp = !!(mcp_url || mcp_tok || mcp_pv || mcp_hh);
// can_mcp=true: he thong goi khang dinh user dung MCP -> bat buoc du 4 truong MCP
const canMcp = b.can_mcp === true || s(b.can_mcp).toLowerCase() === 'true';
if (canMcp && !(mcp_url && mcp_tok && mcp_pv && mcp_hh)) return fail(422, 'thieu_mcp');
if ((canMcp || coMcp) && __SCOPES__.length === 0) return fail(422, 'mcp_khong_duoc_bat_cho_tenant_nay');
if (coTg) {
  if (!/^[A-Za-z][A-Za-z0-9_]{3,30}bot$/i.test(tg_bot)) return fail(422, 'telegram_bot_username_sai_dinh_dang');
  if (!/^[1-9][0-9]{4,14}$/.test(tg_uid)) return fail(422, 'telegram_user_id_phai_la_so');
  if (!/^[0-9]{6,12}:[A-Za-z0-9_-]{30,60}$/.test(tg_tok)) return fail(422, 'telegram_bot_token_sai_dinh_dang');
}
if (coMcp) {
  if (!/^https:\/\/[A-Za-z0-9.-]+(:[0-9]{2,5})?(\/[A-Za-z0-9._~\/-]*)?$/.test(mcp_url) || mcp_url.length > 300) return fail(422, 'mcp_url_phai_la_https');
  if (!/^[A-Za-z0-9_.-]{8,200}$/.test(mcp_tok)) return fail(422, 'mcp_token_sai_dinh_dang');
  const PV = __SCOPES__;  // pham vi MCP hop le: lay tu mcp_profile.json luc build
  if (!PV.length) return fail(422, 'mcp_khong_duoc_bat_cho_tenant_nay');
  const pv = mcp_pv.split(',').map(v => v.trim()).filter(Boolean);
  if (!pv.length || pv.some(v => !PV.includes(v))) return fail(422, 'mcp_pham_vi_chi_gom_' + PV.join(','));
  const t = Date.parse(mcp_hh);
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$/.test(mcp_hh) || isNaN(t)) return fail(422, 'mcp_het_han_phai_la_ISO8601');
  if (t <= Date.now()) return fail(422, 'mcp_het_han_da_qua');
}
let bi_mat = '';
if (coTg || coMcp) {
  const PUB = `__PUBKEY__`;
  const plain = Buffer.from(JSON.stringify({ tg: coTg ? tg_tok : '', mcp: coMcp ? mcp_tok : '' }), 'utf8');
  if (plain.length > 300) return fail(422, 'token_qua_dai');
  bi_mat = crypto.publicEncrypt({ key: PUB, padding: crypto.constants.RSA_PKCS1_OAEP_PADDING, oaepHash: 'sha256' }, plain).toString('base64');
}
return [{ json: { ok: true, user_id, ho_ten, email, phong_ban, agent_id, goi_boi: user,
  co_kenh: coTg || coMcp, telegram_bot_username: coTg ? tg_bot : '', telegram_user_id: coTg ? tg_uid : '',
  mcp_url: coMcp ? mcp_url : '', mcp_pham_vi: coMcp ? mcp_pv : '', mcp_het_han: coMcp ? mcp_hh : '', bi_mat } }];
