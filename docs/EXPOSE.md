# Đưa dịch vụ nhận webhook ra Internet

Hệ thống web **ở ngoài** gọi vào máy của bạn thì phải có đường đi vào. Máy sau router/NAT không tự nhận được kết nối từ Internet. Kit chỉ có **một lựa chọn** (`AW_EXPOSE`) với 3 giá trị:

| Giá trị | Làm gì | Mở port router? | Khi nào dùng |
|---|---|---|---|
| `tunnel` (mặc định) | Cloudflare Tunnel: máy tự kết nối **ra** Cloudflare, Cloudflare chuyển yêu cầu về máy | Không | Web ở Internet; máy ở nhà/văn phòng; nhà mạng có thể dùng CGNAT |
| `port` | Mở TCP 80/443 trên router → máy; Caddy làm HTTPS (Let's Encrypt) | Có | Có IP công cộng thật (không CGNAT), muốn tự chủ, không dùng Cloudflare |
| `none` | Không đưa ra Internet | Không | Web và máy cùng LAN/VPN |

Bất kể chọn gì, **receiver chỉ nghe 127.0.0.1**; chỉ tunnel hoặc Caddy mới nhìn thấy nó, và cả hai đều chỉ cho đúng 2 đường dẫn đi qua: `/healthz` và `/webhook/<AW_WEBHOOK_PATH>`. Mọi thứ khác trả 404.

## Địa chỉ công khai (`AW_PUBLIC_URL`)
Bạn **tự đặt** tên miền (ví dụ `https://agents.congty.vn`) rồi điền khi `kit enable agent-web`. Web bên ngoài gọi: `<AW_PUBLIC_URL>/webhook/<AW_WEBHOOK_PATH>` (AW_WEBHOOK_PATH nằm trong `params.json`, là chuỗi ngẫu nhiên, coi như một phần bí mật).
- `tunnel`: tên miền phải thuộc zone đã thêm vào tài khoản Cloudflare.
- `port`: bản ghi A của tên miền trỏ về IP công cộng của router (hoặc DDNS).

## Kit sinh gì (trong `~/.config/openclaw-kit/tenants/<tenant>/agent-web/expose/`)
- `tunnel`: `cloudflared-config.yml` + `HUONG_DAN.md`
- `port`: `Caddyfile` + `HUONG_DAN.md`
Kit **không** đăng nhập Cloudflare, không đụng router, không cài Caddy/cloudflared: các bước đó do người quản trị làm theo `HUONG_DAN.md`.

## Kiểm tra
`kit doctor` kiểm: (1) receiver chỉ nghe loopback, không lộ `0.0.0.0`; (2) `/healthz` trong máy; (3) `<AW_PUBLIC_URL>/healthz` và chẩn đoán lỗi theo tầng (DNS / TLS / kết nối bị từ chối / hết thời gian / 502 / 530).
**Giới hạn:** (3) chạy từ chính máy này nên chứng minh được DNS và đường tunnel/proxy, nhưng với `port` thì từ trong LAN có thể không phản ánh đúng đường từ ngoài vào (NAT hairpin). Hãy thử thêm bằng điện thoại dùng 4G.

## Lớp bảo vệ có sẵn ở receiver (không phụ thuộc cách đưa ra Internet)
Basic auth + HMAC-SHA256 trên `timestamp.body` (lệch tối đa 5 phút) + **chống gửi lại** (mỗi chữ ký dùng một lần trong 10 phút → 409) + giới hạn 60 yêu cầu/phút/IP + khoá IP 5 phút sau 10 lần sai xác thực + body tối đa 64KB. Nên thêm Cloudflare Access (tunnel) hoặc firewall theo IP của web (port) nếu IP đó cố định.

## Module n8n (`N8N_EXPOSE`)
Module `n8n` chỉ sinh `docker-compose.yml` mẫu và dùng cùng ý tưởng: `tunnel` | `port` | `none`. Mẫu của n8n chỉ cho `/healthz` và `/webhook/*` đi qua; giao diện quản trị n8n **không** lộ ra Internet.
