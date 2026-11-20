// Đã có user_id: giữ agent cũ (không tạo lại), nhưng vẫn ghi/cập nhật kênh Telegram + MCP nếu có. Chưa có: tạo mới.
const req = $('Xác thực').first().json;
const rows = $input.all().map(i => i.json).filter(r => r && r.user_id === req.user_id);
if (rows.length) {
  const r = rows[0];
  return [{ json: { ...req, _new: false, agent_id: r.agent_id, trang_thai: r.trang_thai } }];
}
return [{ json: { ...req, _new: true, trang_thai: 'cho_tao' } }];
