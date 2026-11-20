// Không bao giờ trả token. bi_mat cũng không trả.
const r = $('Quyết định').first().json;
const out = { ok: true, created: r._new, user_id: r.user_id, agent_id: r.agent_id, trang_thai: r.trang_thai };
if (r.telegram_bot_username) out.telegram = { bot: '@' + r.telegram_bot_username, telegram_user_id: r.telegram_user_id, trang_thai: 'cho_gan' };
if (r.mcp_url) out.mcp = { url: r.mcp_url, pham_vi: r.mcp_pham_vi, het_han: r.mcp_het_han, trang_thai: 'da_luu_chua_bat' };
return [{ json: { http_status: r._new ? 201 : 200, out } }];
