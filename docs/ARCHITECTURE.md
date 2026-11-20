# Kiến trúc

## Tenant
Một **tenant** = một công ty/môi trường. Trạng thái nằm ngoài repo:
```
~/.config/openclaw-kit/
  current                       tenant đang chọn
  backups/                      bản sao openclaw.json + file bị thay trước mỗi apply
  tenants/<tenant>/
    params.json                 tham số KHÔNG bí mật
    secrets.env                 tham số bí mật (chmod 600)
    state.json                  module đã bật, bản đã apply, migrations đã chạy
    agent-web/                  file sinh ra cho module (script, users.json, khóa công khai...)
```

## Module
Mỗi module là một thư mục trong `modules/` với `module.json`:
- `params`: tham số cần hỏi (`secret:true` → vào secrets.env; `pattern` kiểm định dạng; `default` có thể là `random:hex12`).
- `files`: mẫu → đích. `if_exists`: `replace` (mặc định, có sao lưu) | `skip` | `sidecar` (ghi `.kit-new`, không đè file người dùng đã sửa — dùng cho AGENTS.md/SOUL.md).
- `config_patch`: JSON gộp vào openclaw.json bằng `openclaw config patch` (kit luôn `--dry-run` kiểm schema trước, rồi sao lưu, rồi ghi).
- `post_apply`, `commands`, `checks`: lệnh sau apply, lệnh `kit run`, kiểm tra cho `kit doctor`.
Mẫu dùng `{{TEN_THAM_SO}}`; thiếu tham số thì apply báo lỗi (không im lặng).

## agent-web
Hai vai trò máy (có thể là **một máy**, đặt `AW_GATEWAY_SSH=local`):
- **Orchestrator**: có quyền gọi n8n API; chạy `provision_tick.py` (systemd timer, flock).
- **Gateway**: chạy OpenClaw và các agent người dùng; giữ **khóa RSA bí mật** (`~/.config/agentweb/bi_mat.pem`). Token bot Telegram/MCP do hệ thống ngoài gửi lên đã được n8n mã hoá bằng khóa công khai (RSA-OAEP-SHA256) → n8n và orchestrator không thấy token rõ.

Cô lập MCP giữa các agent (gan_mcp.py): agent sandbox chỉ mở đúng tool của server mình; agent khác bị `deny` server đó; agent không sandbox (main) `deny` mọi server tiền tố của module. `gan_mcp.py --kiem` báo vi phạm.

Hồ sơ MCP (`modules/agent-web/profiles/*.json`): `server_prefix`, `scopes` (phạm vi → tên tool chính xác), `combined` (tool cần đủ nhiều phạm vi). Công ty mới: sao `example.json`, điền tool của MCP server công ty đó. Tool mới trên server **không tự mở**: thêm vào hồ sơ rồi `kit apply` + cấp lại.

## Nơi nhận webhook (`AW_BACKEND`)
- `local` (mặc định): `receiver.py` (stdlib) nghe 127.0.0.1:`AW_LISTEN_PORT`, ghi SQLite `agent-web/data/agent-web.db` (chmod 600) với đúng hai bảng dưới đây; mã hoá `bi_mat` bằng `openssl pkeyutl` (RSA-OAEP-SHA256) nên không cần thư viện ngoài. `provision.py` đọc/ghi cùng kho qua `awconf.rows/update`.
- `n8n`: workflow n8n (Basic + HMAC) ghi Data table; dùng khi công ty đã có n8n.
Ra Internet: xem docs/EXPOSE.md. Thống kê token: `token_stats.py` (tuỳ chọn `AW_STATS`).

## Bảng (n8n Data table hoặc SQLite)
- `agent_registry`: user_id, agent_id, ho_ten, email, phong_ban, gateway_id, trang_thai (cho_tao→da_tao), ghi_chu
- `agent_kenh`: user_id, agent_id, telegram_bot_username, telegram_user_id, mcp_url, mcp_pham_vi, mcp_het_han, bi_mat, trang_thai (cho_gan→da_gan|loi_gan|khong_co_telegram), cap_nhat_luc, ghi_chu
