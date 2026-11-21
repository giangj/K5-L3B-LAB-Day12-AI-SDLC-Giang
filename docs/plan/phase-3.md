# Kế hoạch thực hiện Phase 3 — TICKET-03 “Mùa Nước Nổi” (Test Contract v1.2)

- **Phạm vi:** 100% Lõi (*Độ tươi nguyên liệu, kho cá thể, giữ chỗ theo ID & giá theo tươi*)
- **Thành viên:** Lê Danh Giang (`@giangj`, `team_size: 1`)
- **Tham chiếu thiết kế:** [`docs/adr/0001-freshness-inventory-v12.md`](../adr/0001-freshness-inventory-v12.md)

## Các bước thực hiện

1. **Bước 1 — Hợp đồng & Adapter Kho (`docs`, `contract v1.2`, `inventory.py`):**
   - Khai báo `contract_version: "1.2"` và khối `tuning.freshness` (`initial: 100`, `gather_decay_per_s: 0.5`, `quan_decay_per_s: 0.25`, `spoiled_below: 30`).
   - Hoàn thiện [`chonoi/inventory.py`](../../chonoi/inventory.py): kiểm tra nghiêm ngặt mảng `{id, kind, fresh}`, từ chối kho đếm cũ (exit `2`), tính `Fraction` bội số `1/240`, xuất file nguyên tử (`os.replace`) sắp theo `id_key`.
   - Cập nhật [`docs/contracts/inventory.sample.json`](../contracts/inventory.sample.json), [`docs/contracts/README.md`](../contracts/README.md), [`AGENTS.md`](../../AGENTS.md).

2. **Bước 2 — Lõi mô phỏng (`gather.py`, `quan.py`, `shop.py`, `day.py`, `scenario.py`):**
   - **`gather.py`:** `hold` giữ list cá thể theo thứ tự vào giỏ; cấp ID `I1, I2, ...` liên tục qua `IdAllocator`; hao tươi `0.5/s` đầu mỗi tick (không hao trong tick vừa bắt/hái và khi `paused`); phát `spoiled` 1 lần theo `id_key`; rơi hàng `monster_hit` / `faint` theo LIFO trả mảng dict `{id, kind, fresh}`; ngất ghi kho rỗng.
   - **`quan.py`:** `stock` là list cá thể; hao tươi `0.25/s` kho thô kể cả hàng đang giữ chỗ; phát hết `spoiled` theo `id_key` rồi xử lý đơn bị ảnh hưởng theo `(order_tick, id_key(table_id))` (nhả toàn bộ phần giữ và thử giữ lại đúng 1 lần theo tươi nhất, hòa theo `id_key`; không đủ thì chuyển `unfulfillable`); lúc `cook_started` tiêu đúng ID đã giữ, phát `items` sắp theo `(kind, id_key)` và chốt `base_price = floor(list_price * avg_fresh / 100)`; boa `floor(base_price * 0.2)`.
   - **`day.py` & `shop.py`:** đồng bộ trạng thái ra `DaySim` ngay mỗi tick (bài học Phase 2); giữ `IdAllocator` xuyên pha & xuyên Ngày; bàn giao `hold -> stock` trong cùng tick không hao thêm; kho thô trong `ShopSim` giữ nguyên schema v1.2 và không hao.
   - **`scenario.py`:** kiểm tra mâu thuẫn v1.2 (`gather.hold`, `quan.stock`, `customers[].reserved`, ID duy nhất toàn cục, tự động giữ chỗ nếu thiếu `reserved`, Ngày 2+ cấp ID mới).

3. **Bước 3 — HUD Web & Cập nhật Fixture P1/P2:**
   - Cập nhật [`chonoi/web/index.html`](../../chonoi/web/index.html) hiển thị độ tươi từng cá thể (thanh tươi + số %) và đánh dấu `ƯƠN` (`< 30`).
   - Chuyển đổi các fixture trong `tests/` sang schema v1.2 (giữ test từ chối kho đếm cũ), chạy toàn bộ bộ test xanh 100% và đẩy `origin/main`.

4. **Bước 4 — Bộ test mới, Bằng chứng & Đóng Phase 3:**
   - Tạo `tests/test_phase3_rules.py` (`AC-P3-01`..`AC-P3-12`).
   - Lưu proof thật tại `docs/proof/phase-3/`: kịch bản ngưỡng `30 -> <30`, bàn giao 2 tiến trình kiểm tra độ tươi & giá chốt, chạy `day` v1.2 nhiều ngày, kết quả test.
   - Cập nhật [`docs/verification/phase-3.md`](../verification/phase-3.md), [`CHANGELOG.md`](../../CHANGELOG.md) (Breaking Changes & hướng dẫn nâng cấp fixture), `docs/clarify.md`, `docs/standup.md`, `docs/ai-usage-log.md`, `README.md` và gắn thẻ `phase-3`.
