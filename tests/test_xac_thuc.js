// Test logic webhook (xac_thuc.js) bằng node: Basic auth, HMAC, timestamp, validate, mã hoá RSA-OAEP (giải mã bằng openssl ở test_all.py).
const fs = require('fs'), crypto = require('crypto');
const [,, codeFile, pubFile, outFile] = process.argv;
const pub = fs.readFileSync(pubFile, 'utf8').trim();
const SALT = 'saltx', PASS = 'pw-test', SECRET = 'hmac-secret-test';
const users = { cty: { h: crypto.createHash('sha256').update(SALT + ':' + PASS).digest('hex'), hmac: 'bat_buoc', secret: SECRET } };
const code = fs.readFileSync(codeFile, 'utf8').replace('__USERS__', JSON.stringify(users)).replace('__SALT__', SALT)
  .replace('__PUBKEY__', pub).replaceAll('__SCOPES__', JSON.stringify(['doc', 'viet']));
const run = new (Object.getPrototypeOf(async function () {}).constructor)('$input', 'require', code);
async function call(body, o = {}) {
  const raw = JSON.stringify(body), ts = String(o.ts || Math.floor(Date.now() / 1000));
  const h = { authorization: 'Basic ' + Buffer.from('cty:' + (o.pass || PASS)).toString('base64') };
  if (o.sign !== false) { h['x-timestamp'] = ts; h['x-signature'] = 'sha256=' + crypto.createHmac('sha256', o.secret || SECRET).update(ts + '.' + raw).digest('hex'); }
  const ctx = { helpers: { getBinaryDataBuffer: async () => { throw new Error('no binary in test'); } } };
  const res = await run.call(ctx, { first: () => ({ json: { headers: h, body } }) }, require);
  return res[0].json;
}
const fut = new Date(Date.now() + 86400000 * 30).toISOString();
const tests = [];
const t = (name, got, want) => tests.push([name, JSON.stringify(got).includes(want), want, got]);
(async () => {
  let r = await call({ user_id: 'NV-1', ho_ten: 'A', email: 'a@x.vn' }); t('hop le', r.ok, 'true'); fs.writeFileSync(outFile, JSON.stringify(r));
  r = await call({ user_id: 'NV-1', ho_ten: 'A' }, { secret: 'sai' }); t('sai chu ky', r, 'sai_chu_ky');
  r = await call({ user_id: 'NV-1', ho_ten: 'A' }, { ts: Math.floor(Date.now() / 1000) - 600 }); t('timestamp cu', r, 'lech_qua_5_phut');
  r = await call({ user_id: 'NV-1', ho_ten: 'A' }, { pass: 'sai' }); t('sai mat khau', r, 'sai_user_hoac_mat_khau');
  r = await call({ user_id: 'NV-1', ho_ten: 'A' }, { sign: false }); t('khong ky (HMAC bat buoc)', r, 'thieu_x-signature');
  r = await call({ user_id: 'a b', ho_ten: 'A' }); t('user_id sai', r, 'user_id_bat_buoc');
  r = await call({ user_id: 'NV-2' }); t('thieu ho_ten', r, 'ho_ten_bat_buoc');
  r = await call({ user_id: 'NV-3', ho_ten: 'C', can_mcp: true }); t('can_mcp thieu truong', r, 'thieu_mcp');
  r = await call({ user_id: 'NV-4', ho_ten: 'D', mcp_url: 'https://mcp.example.com/x', mcp_token: 'abcdefgh12345678', mcp_pham_vi: 'xoa', mcp_het_han: fut }); t('pham vi la', r, 'mcp_pham_vi_chi_gom_doc,viet');
  r = await call({ user_id: 'NV-5', ho_ten: 'E', mcp_url: 'https://mcp.example.com/x', mcp_token: 'tokenmcp-secret-12345', mcp_pham_vi: 'doc,viet', mcp_het_han: fut }); t('mcp hop le + ma hoa', [r.ok, r.mcp_pham_vi, r.bi_mat.length > 100], 'true,"doc,viet",true');
  fs.writeFileSync(outFile + '.mcp', JSON.stringify(r));
  r = await call({ user_id: 'NV-6', ho_ten: 'F', mcp_url: 'http://mcp.example.com/x', mcp_token: 'tokenmcp-secret-12345', mcp_pham_vi: 'doc', mcp_het_han: fut }); t('mcp http bi tu choi', r, 'mcp_url_phai_la_https');
  let bad = 0; for (const [n, ok, want, got] of tests) { console.log((ok ? 'PASS ' : 'FAIL ') + n); if (!ok) { bad++; console.log('   want ~', want, 'got', JSON.stringify(got).slice(0, 200)); } }
  process.exit(bad ? 1 : 0);
})();
