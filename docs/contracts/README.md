# Hợp đồng tích hợp (Contract v1.0 — Phase 1)

> Chốt trong kickoff Phase 1. Mọi thay đổi schema hoặc tên sự kiện từ Phase 2+ cần cập nhật tài liệu này và ghi ADR/CHANGELOG.

## 1. Schema file kho (`gather` → `quan`, mục G PRD-0)
- Định dạng UTF-8 JSON object có **duy nhất** khóa `"items"`:
  ```json
  {"items": {"bong_sung": 2, "ca_loc": 1}}
  ```
- Khóa trong `items` thuộc danh mục v1.0 (`ca_loc`, `ca_linh`, `bong_dien_dien`, `bong_sung`); giá trị là số nguyên `> 0` (bên ghi loại bỏ mục bằng `0`; kho rỗng là `{"items":{}}`).
- File kho mẫu hợp lệ: [`inventory.sample.json`](inventory.sample.json).
- Quy tắc bàn giao:
  - `gather --inventory-out <path>` chỉ ghi **một lần** khi có `gather_end` (ghi file tạm cùng thư mục rồi `os.replace` nguyên tử). Ngất (`fainted`) ghi kho rỗng `{"items":{}}`. Chạm `--ticks` trước khi kết thúc không tạo/ghi đè file đích.
  - `quan --inventory <path>` đọc file kho; từ chối sai schema, kind lạ, số âm (mã thoát `2`). Trần `hold_capacity` chỉ áp dụng cho giỏ ở `gather`, không áp lên `quan.stock`.

## 2. Giao diện giữa `sim/*` và `client/ui` (`chonoi/live.py` ↔ `chonoi/web/index.html`)
- **UI đọc trạng thái (`GET /state`)**: trả JSON snapshot theo mode + `meta` (`tuning[mode]`), `events` (40 sự kiện gần nhất), `finished`, `reason`, `error`:
  - Chung: `tick`, `sim_tick`, `mode`, `phase`, `phase_tick`, `state`, `time_left_ticks`, `money`, `earned`, `reputation`, `score`.
  - `gather`: `player` (`pos`, `vel`, `heading_deg`, `oxygen_ticks`, `oxygen_max_ticks`, `hp`, `hp_max`, `zero_oxy_ticks`, `invuln_ticks`, `catch_cd_ticks`, `at_surface`), `hold`, `hold_count`, `hold_capacity`, `nodes[]` (`id`, `pos`, `kind`, `ready`, `regrow_ticks`), `fish[]` (`id`, `pos`, `kind`, `heading_deg`).
  - `quan`: `player` (`pos`), `stock` (tồn vật lý), `hand` (payload `{order_id, dish_id, base_price}` hoặc `null`), `stoves[]` (`id`, `pos`, `state`, `dish`, `cook_ticks_left`, `ready_ticks`), `tables[]` (`id`, `pos`, `customer_id`), `customers[]` (`id`, `table_id`, `dish_id`, `order_tick`, `state`, `patience_ticks_left`, `eat_ticks_left`, `order_status`, `reserved`, `base_price`, `tip`).
- **UI gửi lệnh (`POST /input`, `POST /restart`)**:
  - `POST /input`: `{"move": [dx, dy], "interact": bool, "catch": bool}` (`dy` dương = lặn xuống trong `gather`, đi lên bắc `+z` trong `quan`). Sim xử lý `interact`/`catch` theo cạnh lên (`false -> true`).
  - `POST /restart`: khởi tạo lại lượt chơi với cùng `mode`, `seed`, `scenario`.

## 3. Danh sách sự kiện (Event Catalog v1.0, mục E PRD-0)

### Buổi sáng (`gather`, phát bởi `GatherSim`, nghe bởi `runner` / `JsonlWriter` / `client/ui`)
| Event | `data` | Khi nào phát |
|---|---|---|
| `dive` | `{"pos": [x, d]}` | Chuyển từ mặt nước (`d <= surface_depth`) xuống dưới nước |
| `surface` | `{"pos": [x, d]}` | Chuyển từ dưới nước lên mặt nước |
| `oxygen_empty` | `{"oxygen_ticks": 0}` | Oxy giảm từ dương xuống đúng `0` |
| `choke` | `{"hp": hp}` | Đủ `choke_interval_ticks` (60) dưới nước với `oxygen_ticks == 0` |
| `faint` | `{"cause": "choke", "lost": [...], "hp": 0}` | `hp` chạm `0` (bỏ giỏ theo LIFO) |
| `node_regrown` | `{"node_id": id}` | `regrow_ticks` giảm từ `1` về `0` |
| `gather` | `{"node_id": id, "kind": kind, "amount": n}` | Hái thành công nút ở mặt nước |
| `fish_caught` | `{"fish_id": id, "kind": kind, "yield": n}` | Bắt thành công đàn cá dưới nước |
| `hold_full` | `{"action": "gather"\|"catch", "node_id"\|"fish_id": id, "required": r, "free": f}` | Không đủ chỗ trong giỏ |
| `gather_end` | `{"reason": "docked"\|"time"\|"fainted", "inventory": {"items": {...}}}` | Kết thúc ca sáng |

### Buổi tối (`quan`, phát bởi `QuanSim`, nghe bởi `runner` / `JsonlWriter` / `client/ui`)
| Event | `data` | Khi nào phát |
|---|---|---|
| `customer_arrived` | `{"order_id": id, "table_id": tid, "dish_id": did}` | Khách mới ngồi bàn và giữ nguyên liệu |
| `no_dish` | `{}` | Tới lượt khách và còn bàn trống nhưng không đủ kho khả dụng cho món nào |
| `cook_started` | `{"stove_id": sid, "order_id": oid, "dish_id": did, "items": [...], "base_price": p}` | Bắt đầu nấu đơn `reserved` cũ nhất |
| `dish_ready` | `{"stove_id": sid, "order_id": oid, "dish_id": did}` | Bếp nấu xong |
| `dish_picked` | `{"stove_id": sid, "order_id": oid, "dish_id": did}` | Nhấc món lên tay trống |
| `served` | `{"order_id": oid, "table_id": tid, "dish_id": did, "patience_ticks_left": p, "base_price": bp, "tip": tip}` | Giao đúng món tới bàn |
| `paid` | `{"order_id": oid, "table_id": tid, "base_price": bp, "tip": tip, "amount": amt, "reason": "finished_eating"\|"closing"}` | Khách ăn xong hoặc đóng ca khi đang ăn |
| `customer_left` | `{"order_id": oid, "table_id": tid, "reason": "patience"\|"closing", "reputation": rep}` | Khách waiting bỏ đi hết kiên nhẫn hoặc đóng ca |
| `quan_end` | `{"reason": "time", "money": m, "earned": e, "shift_earned": se, "reputation": rep}` | Kết thúc ca tối |
