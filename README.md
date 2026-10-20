# Sony Bravia TV (IP Control) cho Home Assistant

Custom integration (HACS) điều khiển tivi **Sony Bravia** (Android TV / Google TV, đời 2013 trở lên) qua mạng LAN bằng **REST API + IRCC** của Sony. Không cần thư viện ngoài, chạy tốt trên Home Assistant bản Docker.

Domain: `sony_bravia_ip` — không đụng với integration `braviatv` có sẵn của HA.

## Tính năng

| Entity | Chức năng |
|---|---|
| `media_player` | Bật/tắt, âm lượng (set / tăng / giảm / mute), chọn nguồn (HDMI + ứng dụng), play/pause/stop, next/prev (đổi kênh khi đang xem TV), `play_media`, hiển thị kênh/nguồn đang phát |
| `remote` | Gửi mọi phím IRCC (`Home`, `Return`, `Up`, `Confirm`, `Num1`…), hỗ trợ `num_repeats`, `delay_secs`. Danh sách lệnh nằm trong attribute `commands` |
| `select.*_nguon` | Chọn cổng vào / ứng dụng |
| `select.*_che_do_hinh_anh` | Picture mode (Vivid, Cinema, Custom…) |
| `select.*_dau_ra_am_thanh` | Loa tivi / Audio system (soundbar, AVR) |
| `button` | Home, Back, Input, Options, Netflix, Guide, Khởi động lại tivi |

Service riêng (target là `media_player`):

- `sony_bravia_ip.launch_app` — mở app theo tên (`YouTube`) hoặc URI
- `sony_bravia_ip.play_content` — chuyển cổng/kênh theo URI (`extInput:hdmi?port=3`)
- `sony_bravia_ip.set_picture_setting` — chỉnh `brightness`, `contrast`, `pictureMode`…
- `sony_bravia_ip.set_sound_setting` — chỉnh `outputTerminal`, `soundMode`…

Tùy chọn (Options): chu kỳ cập nhật và **chọn những nguồn/ứng dụng nào hiện trong source list** (để trống = hiện tất cả). Tên cổng HDMI dùng nhãn bạn đặt trên tivi (vd. HDMI 3 đặt nhãn "Zidoo" sẽ hiện là "Zidoo").

## Cài đặt trên tivi

1. **Cài đặt → Mạng & Internet → Mạng gia đình → Điều khiển IP**
   - **Xác thực**: `Bình thường và Khóa chia sẻ trước` (Normal and Pre-Shared Key)
   - **Khóa chia sẻ trước**: đặt một mã, vd. `1234`
   - **Điều khiển từ xa đơn giản / Simple IP control**: Bật (nếu có)
2. **Khởi động từ xa (Remote start)**: Bật — để bật tivi qua mạng khi đang standby.
3. Đặt **IP tĩnh** cho tivi trên router.

> Nếu tivi tắt hẳn mạng khi standby, integration sẽ gửi thêm Wake-on-LAN tới MAC của tivi khi bật.

## Cài integration

### HACS
1. HACS → ⋮ → **Custom repositories** → thêm `https://github.com/lamntevohome-gif/ha-sony-tv`, loại **Integration**.
2. Tải **Sony Bravia TV (IP Control)**, khởi động lại Home Assistant.

### Thủ công
Chép thư mục `custom_components/sony_bravia_ip` vào `config/custom_components/` (với Docker là thư mục được mount làm `/config`), rồi khởi động lại.

### Thêm thiết bị
**Cài đặt → Thiết bị & Dịch vụ → Thêm tích hợp → Sony Bravia TV (IP Control)** → nhập IP và PSK.

## Ví dụ

```yaml
# Chuyển sang HDMI 3
action: media_player.select_source
target: { entity_id: media_player.sony_tv }
data: { source: "HDMI 3" }

# Gửi chuỗi phím
action: remote.send_command
target: { entity_id: remote.sony_tv_dieu_khien }
data:
  command: [Home, Down, Down, Confirm]
  delay_secs: 0.3

# Mở YouTube
action: sony_bravia_ip.launch_app
target: { entity_id: media_player.sony_tv }
data: { app: YouTube }

# Mở kênh/URI trực tiếp
action: media_player.play_media
target: { entity_id: media_player.sony_tv }
data:
  media_content_type: app
  media_content_id: Netflix
```

Lệnh remote nhận tên phím Sony (không phân biệt hoa thường), các tên tắt `back`, `ok`, `enter`, `menu`, `info`, `previous`, `ff`, `rev`, hoặc mã IRCC base64 thô.

## Lưu ý

- Khi đang ở trong ứng dụng, Sony API không cho biết app nào đang chạy → `source` sẽ trống, state là `on`.
- Một số đời tivi không hỗ trợ picture mode / sound output qua API; các select đó sẽ ở trạng thái *unavailable*.
- Bật log debug:
  ```yaml
  logger:
    logs:
      custom_components.sony_bravia_ip: debug
  ```
