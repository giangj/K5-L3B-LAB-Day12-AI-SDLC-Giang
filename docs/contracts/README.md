# Hợp đồng tích hợp (Contract v1.1 — Phase 2)

> Cập nhật từ v1.0 sang v1.1 theo TICKET-02 (thêm 2 nguyên liệu, 3 món mới, cá bơi/sinh, Cá Sấu Năm Chèo, chế độ `day`, `Shop` nâng cấp và `pause`).

## 1. Schema file kho (`gather` → `quan`, vẫn dùng đếm theo loại ở v1.1)
- Khóa gốc duy nhất `"items"`:
  ```json
  {"items": {"bong_sung": 2, "ca_keo": 2, "keo_neo": 1}}
  ```
- Danh mục v1.1 gồm 6 loại: `ca_loc`, `ca_linh`, `ca_keo`, `bong_dien_dien`, `bong_sung`, `keo_neo`.
- Trong `--mode day`, bàn giao từ `gather` sang `quan` diễn ra trong bộ nhớ cùng tick phát `gather_end` (kể cả khi `fainted` → kho rỗng `{}`), và kho dư bị xóa sau khi đóng `Shop`. Hai tiến trình rời vẫn bàn giao qua `--inventory-out` / `--inventory` như v1.0.

## 2. Giao diện giữa `sim/*` và `client/ui` (`chonoi/live.py` ↔ `chonoi/web/index.html`)
- `GET /state`: bổ sung `meta.tuning` (`gather`, `quan`, `menu`, `shop`, `day_plan`), trường `monsters[]`, `fish[].age_ticks` ở `gather`; thêm `day`, `day_plan`, `upgrades`, `active_upgrades`, `stock` (ở `shop`), `state: "paused"` khi tạm dừng trong chế độ `day`.
- `POST /input`: nhận `{"move": [dx, dy], "interact": bool, "catch": bool, "pause": bool, "shop_done": bool, "buy": str|null}`.
- `POST /mode`: đổi chế độ chơi (`day`, `gather`, `quan`) từ menu chính trên UI live.

## 3. Sự kiện bổ sung v1.1 (mục 4.4 TICKET-02)
- **Gather:** `monster_hit` (`monster_id`, `hp`, `lost`, `pos`), `fish_spawned` (`id`, `kind`, `pos`), `faint` (thêm `cause: "monster"` nếu do Cá Sấu chạm).
- **Pause:** `paused` (`{}`), `resumed` (`{}`).
- **Day & Shop:** `day_start` (`{}`), `day_plan` (`dishes`, `ingredients`), `phase_start` (`{}`), `bought` (`upgrade`, `level`, `price`, `money`), `buy_failed` (`action`, `reason`: `funds` / `max_level` / `out_of_stock` / `unknown`), `shop_end` (`reason`: `done` / `time`).
- Khi chạy `--mode day`, vỏ mọi dòng event có thêm trường `"day"`, và dòng `end` có thêm `"days_completed"`.
