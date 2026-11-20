# Cập nhật

```bash
kit update                    # kit mới nhất + migrations + apply + doctor
kit update --with-openclaw    # thêm: openclaw update --yes (chạy TRƯỚC khi apply)
```
Quy trình `kit update`: (1) `git pull --ff-only` (2) tuỳ chọn `openclaw update --yes` (3) chạy migration chưa chạy (`migrations/NNNN_*.py`, ghi vào state) (4) `kit apply` các module đã bật (5) `kit doctor`.

- **Chức năng mới**: module mới xuất hiện trong `kit modules`; muốn dùng thì `kit enable <module>` rồi `kit apply`. Module đã bật có bản mới: `kit modules` hiện "có bản mới", `kit apply` cập nhật.
- **OpenClaw đổi schema**: apply luôn chạy `openclaw config patch --dry-run` trước; nếu OpenClaw từ chối, kit dừng và **không ghi gì**. Sửa file `config.patch.json.in` của module theo schema mới (xem `openclaw config validate`, docs OpenClaw), thêm migration nếu cần chuyển dữ liệu cũ.
- **Hoàn tác**: mọi lần apply sao lưu vào `~/.config/openclaw-kit/backups/` (`openclaw.json.<giờ>`, `files.<giờ>/`). Khôi phục: copy lại file rồi `openclaw gateway restart`.
- **Máy chạy production**: chạy `kit apply --dry-run` trước; cập nhật OpenClaw ngoài giờ làm việc.
- Không sửa tay file trong thư mục kit (git pull sẽ xung đột); tuỳ biến theo công ty đặt ở tham số, hồ sơ MCP riêng, hoặc sidecar `.kit-new`.

## Viết migration
`migrations/0001_ten.py`: script Python độc lập, nhận `KIT_TENANT`, `KIT_HOME`, `KIT_ROOT` trong môi trường; exit 0 = xong (kit ghi nhớ, không chạy lại). Phải idempotent.
