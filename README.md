# openclaw-kit

Bộ triển khai **OpenClaw** cho nhiều công ty/máy từ một repo. Mỗi máy chỉ cần điền thông số của công ty đó, chọn chức năng (module) cần dùng, rồi `kit apply`. Khi OpenClaw hoặc kit có bản mới: `kit update`.

> **Repo này không chứa bí mật.** Mật khẩu/token/API key chỉ nằm ở `~/.config/openclaw-kit/tenants/<tenant>/secrets.env` (chmod 600) trên từng máy, không bao giờ vào git. Xem [docs/SECURITY.md](docs/SECURITY.md).

## Cài trên máy mới (Linux, user thường)

```bash
# 1. Cài OpenClaw + kit
KIT_REPO=git@github.com:<tai-khoan>/openclaw-kit.git bash <(curl -fsSL https://raw.githubusercontent.com/<tai-khoan>/openclaw-kit/main/install.sh) <ten-cong-ty>
# (repo private: git clone trước rồi chạy bash openclaw-kit/install.sh <ten-cong-ty>)

# 2. Onboarding OpenClaw (model, Telegram, service Gateway)
openclaw onboard --install-daemon

# 3. Chọn chức năng và điền thông số công ty
kit modules                      # xem danh sách chức năng
kit enable base                  # tên công ty, chủ, múi giờ, model chính
kit enable agent-web             # webhook tạo nhân viên + MCP (receiver tích hợp; cách ra Internet; Gateway...)
kit apply --dry-run              # xem trước, KHÔNG ghi gì
kit apply                        # dựng thật (tự sao lưu openclaw.json trước)
kit doctor                       # kiểm tra
```

## Chức năng (module)

| Module | Làm gì | Trạng thái |
|---|---|---|
| `base` | Cấu hình mặc định OpenClaw (model, compaction, memory-flush, web search) + AGENTS/SOUL/USER/IDENTITY mẫu cho workspace | ĐÃ THỬ cục bộ (schema OpenClaw 2026.10.9: `config patch --dry-run` OK) |
| `agent-web` | Web/HRM gọi **webhook** (Basic + HMAC + chống gửi lại) → tạo **agent riêng** (sandbox) + **bot Telegram riêng** + **MCP riêng** theo token từng người; cô lập giữa các agent. **Mặc định receiver tích hợp (Python + SQLite, không cần n8n)**, tuỳ chọn workflow n8n. Tuỳ chọn: Cloudflare Tunnel hoặc mở port (`AW_EXPOSE`), thống kê token theo người (`AW_STATS`) | ĐÃ THỬ cục bộ + **ĐÃ THỬ THẬT trên Lab** (systemd, Cloudflare quick tunnel, Caddy, cloudflared validate); **CHƯA THỬ** Telegram thật, named tunnel + DNS, mở port/router thật, n8n thật (xem docs/TESTING.md) |
| `n8n` | **Tuỳ chọn.** Chỉ sinh `docker-compose.yml` mẫu (+ mẫu tunnel/Caddy) để chạy n8n riêng khi chọn `AW_BACKEND=n8n`. Kit không chạy docker | ĐÃ THỬ cục bộ + `docker compose config` + `caddy validate` trên Lab; **CHƯA THỬ** `docker compose up` thật |

Chưa đưa vào (kế hoạch): tạo VM Proxmox cho Gateway.

## Quy trình agent-web (tóm tắt)

```
Hệ thống web ──POST (Basic + HMAC)──▶ [tunnel/Caddy] ──▶ receiver (127.0.0.1) ──ghi──▶ SQLite (agent_registry / agent_kenh)
   (AW_BACKEND=n8n: ──▶ n8n webhook ──▶ Data table)                                          ▲
         (timer 60s) provision.py ──đọc/cập nhật─────────────────────────────────────────────┘
              │ SSH hoặc local
              ▼
        Máy Gateway: create_agent.sh (agent + sandbox) → gan_kenh.sh (bot Telegram, giải mã token) → gan_mcp.py (MCP riêng + cô lập)
```

Ra Internet: [docs/EXPOSE.md](docs/EXPOSE.md) (Cloudflare Tunnel hoặc mở port). Thống kê token: `kit run agent-web stats --in`.

Chi tiết: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Thêm công ty mới: [docs/NEW_COMPANY.md](docs/NEW_COMPANY.md). Cập nhật: [docs/UPDATING.md](docs/UPDATING.md).

## Lệnh

| Lệnh | Việc |
|---|---|
| `kit init <tenant>` | tạo tenant (mỗi công ty một tenant, có thể nhiều tenant trên một máy) |
| `kit modules` | chức năng, bật/tắt, có bản mới không |
| `kit enable <module> [--set K=V] [--params-file f.json] [--yes]` | hỏi/nhận tham số, lưu |
| `kit apply [module] [--dry-run]` | dựng file, systemd, `openclaw config patch` (idempotent) |
| `kit update [--with-openclaw]` | git pull kit → (tuỳ chọn) `openclaw update` → migrations → apply → doctor |
| `kit doctor` | kiểm môi trường + từng module |
| `kit run agent-web <keygen\|add-caller\|test-webhook\|provision\|receiver\|stats>` (+ `deploy-workflow\|tables` khi dùng n8n) | lệnh riêng của module |
| `kit run agent-web open-tools [--dry-run]` | mở web/trình duyệt cho agent theo `AW_TOOLS_*` (trên Gateway) |
| `kit export-config` | xuất cấu hình OpenClaw đã che bí mật (để đưa vào mẫu) |

## Chạy test

```bash
python3 tests/test_all.py     # backend n8n (n8n giả); cần python3, node, openssl
python3 tests/test_local.py   # receiver tích hợp, expose, thống kê token, module n8n; không chạm OpenClaw/n8n/Telegram/Cloudflare thật
```
