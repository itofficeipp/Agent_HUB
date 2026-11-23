# openclaw-kit

Bộ triển khai **OpenClaw** cho nhiều công ty/máy từ một repo. Mỗi máy chỉ cần điền thông số của công ty đó, chọn chức năng (module) cần dùng, rồi `kit apply`. Khi OpenClaw hoặc kit có bản mới: `kit update`.

> **Repo này không chứa bí mật.** Mật khẩu/token/API key chỉ nằm ở `~/.config/openclaw-kit/tenants/<tenant>/secrets.env` (chmod 600) trên từng máy, không bao giờ vào git. Xem [docs/SECURITY.md](docs/SECURITY.md).

## Cài trên máy mới (Linux, user thường, KHÔNG dùng root)

Repo này là **private**; máy mới cần quyền **đọc** (khoá deploy SSH chỉ đọc, riêng cho từng công ty). Cách dễ nhất: chạy `bash install.sh <ten-cong-ty>` — nếu chưa có quyền, installer tự tạo khoá riêng cho máy và in khoá công khai để quản trị viên thêm vào GitHub (Deploy keys, không tích Allow write access), rồi chạy lại (xem docs/NEW_COMPANY.md bước 0). Cách thủ công:

```bash
# 1. Lấy kit và cài OpenClaw (nếu thiếu)
git clone git@github.com:itofficeipp/Agent_HUB.git ~/openclaw-kit
bash ~/openclaw-kit/install.sh                # cài OpenClaw + lệnh 'kit'; không hỏi gì thêm

# 2. Đăng nhập model/Telegram của OpenClaw (một lần)
openclaw onboard --install-daemon

# 3. Cài từng bước CÓ GỢI Ý: kiểm tra máy -> hỏi thông số -> xem trước -> dựng -> kiểm tra
kit setup congty-abc                          # đổi tên theo công ty; chạy lại bất cứ lúc nào cũng an toàn
```

`kit setup` hỏi từng thông số, mỗi câu có **gợi ý + ví dụ**, nhập sai thì báo và hỏi lại, bí mật nhập ẩn (lưu chmod 600, không vào git), có bản **tóm tắt** trước khi dựng, rồi `apply --dry-run` → `apply` → `doctor` và in **bước tiếp**.

Muốn chạy không hỏi (nhiều công ty, điền sẵn): copy `examples/congty.params.json`, sửa, rồi:

```bash
kit setup congty-abc --yes --modules base,agent-web --params-file congty-abc.json
kit setup congty-abc --yes --no-apply ...    # chỉ lưu + xem trước
kit preflight                                 # chỉ kiểm tra máy
```

Chạy thủ công từng lệnh (cùng kết quả): `kit init`, `kit enable base`, `kit enable agent-web`, `kit apply --dry-run`, `kit apply`, `kit doctor`.

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
| `kit init <tenant>` | tạo tenant (mỗi công ty một tenant, có thể nhiều tenant trên một máy); tenant đầu tiên thành mặc định, các tenant sau không đổi mặc định |
| `kit use <tenant>` | đổi tenant mặc định (hoặc thêm `--tenant <tenant>` vào từng lệnh) |
| `kit modules` | chức năng, bật/tắt, có bản mới không |
| `kit enable <module> [--set K=V] [--params-file f.json] [--yes]` | hỏi/nhận tham số, lưu |
| `kit apply [module] [--dry-run]` | dựng file, systemd, `openclaw config patch` (idempotent) |
| `kit update [--with-openclaw]` | git pull kit → (tuỳ chọn) `openclaw update` → migrations → apply → doctor |
| `kit doctor [--strict]` | kiểm môi trường + từng module; `--strict` thoát mã 1 nếu có LỖI (mặc định 0) |
| `kit run agent-web <keygen\|add-caller\|test-webhook\|provision\|receiver\|stats>` (+ `deploy-workflow\|tables` khi dùng n8n) | lệnh riêng của module |
| `kit run agent-web open-tools [--dry-run]` | mở web/trình duyệt cho agent theo `AW_TOOLS_*` (trên Gateway) |
| `kit export-config` | xuất cấu hình OpenClaw đã che bí mật (để đưa vào mẫu) |

## Chạy test

```bash
python3 tests/test_all.py     # backend n8n (n8n giả); cần python3, node, openssl
python3 tests/test_local.py   # receiver tích hợp, expose, thống kê token, module n8n; không chạm OpenClaw/n8n/Telegram/Cloudflare thật
```
