# Hợp đồng tích hợp (Contract v1.2 — Phase 3)

> Cập nhật từ v1.1 lên v1.2 theo TICKET-03 (*Mùa Nước Nổi*: thay thế kho đếm theo loại bằng kho cá thể `{id, kind, fresh}`, thêm độ tươi, sự kiện `spoiled`, giữ chỗ theo ID tươi nhất và giá món theo độ tươi).

## 1. [THAY THẾ] Schema file kho (`gather` → `quan`)
- Khóa gốc duy nhất `"items"`, giá trị là **mảng cá thể**:
  ```json
  {"items": [{"id": "I1", "kind": "ca_linh", "fresh": 100}, {"id": "I2", "kind": "ca_loc", "fresh": 97.5}]}
  ```
- Kho rỗng là `{"items": []}`. File kho đếm theo loại cũ bị trả mã thoát `2`.
- Mỗi cá thể có `id` chuỗi duy nhất khác rỗng (`I1, I2, ...` cấp liên tục xuyên pha và Ngày), `kind` thuộc 6 loại nguyên liệu v1.1, `fresh` hữu hạn trong `[0, 100]`.
- Xuất file `--inventory-out` chỉ ghi một lần khi có `gather_end` (ngất ghi `{"items": []}`), sắp theo `id_key`, ghi nguyên tử qua file tạm cùng thư mục rồi `os.replace`.
- Trong `--mode day`, bàn giao từ `gather` sang `quan` diễn ra trong bộ nhớ ở cùng tick chuyển pha và không hao tươi thêm; `Shop` hiển thị `stock` thô theo cùng schema cá thể và không hao tươi.

## 2. Giao diện giữa `sim/*` và `client/ui` (`chonoi/live.py` ↔ `chonoi/web/index.html`)
- `GET /state`: thêm `tuning.freshness`; trong snapshot, `hold` (`gather`), `stock` (`quan`, `shop`) và `customers[].reserved` dùng mảng cá thể/ID theo Contract v1.2; HUD web đọc được độ tươi từng cá thể và đánh dấu hàng `ƯƠN` (`< 30`).
- `POST /input` & `POST /mode`: giữ nguyên v1.1 (`move`, `interact`, `catch`, `pause`, `shop_done`, `buy`).

## 3. Sự kiện & payload mới / thay đổi ở v1.2 (TICKET-03)
- **`spoiled` (mới):** phát đúng 1 lần theo thứ tự `id_key` khi cá thể đi từ `fresh >= 30` xuống `< 30` ở đầu tick (`{"item_id", "kind", "location": "hold" | "stock"}`).
- **`cook_started.data.items`:** mảng cá thể `{id, kind, fresh}` sắp theo `(kind, id_key)`; `base_price = floor(giá_niêm_yết × trung_bình_fresh / 100)`.
- **`paid` & `served`:** dùng `base_price` đã chốt theo độ tươi; boa `floor(base_price × 0.2)`.
- **`monster_hit.data.lost` & `faint.data.lost`:** mảng cá thể `{id, kind, fresh}` theo thứ tự bỏ LIFO.
- **`gather_end.data.inventory`:** theo schema `{"items": [...]}` (với `fresh` được bảo toàn chính xác ở ngưỡng `30`).
