# Ma trận kiểm chứng — Phase 3 (TICKET-03 & Test Contract v1.2)

- **Ngày kiểm chứng:** 2026-11-21
- **Người thực hiện:** Lê Danh Giang (`@giangj`)
- **ADR & Kế hoạch:** [`docs/adr/0001-freshness-inventory-v12.md`](../adr/0001-freshness-inventory-v12.md), [`docs/plan/phase-3.md`](../plan/phase-3.md)

## 1. Bảng truy vết Yêu cầu ↔ Mã nguồn ↔ Kiểm thử ↔ Bằng chứng

| ID | Yêu cầu (TICKET-03 & Test Contract v1.2) | Mã nguồn | Kiểm thử (`tests/test_phase3_rules.py`) | Kết quả / Proof |
|---|---|---|---|---|
| AC-P3-01 | `contract_version: "1.2"`, `tuning.freshness` (`100`, `0.5`, `0.25`, `30`); file kho đếm theo loại hoặc sai schema trả mã thoát `2`. | [`game.contract.json`](../../game.contract.json), [`chonoi/contract.py`](../../chonoi/contract.py), [`chonoi/inventory.py`](../../chonoi/inventory.py) | `test_p3_01_contract_v12_spoil_threshold_and_count_map_exit_2`, `test_smoke_p1.Integration.test_inv_bad_schema_exit_2` | PASS |
| AC-P3-02 | Ngưỡng `fresh < 30` phát `spoiled` đúng 1 lần theo `id_key` khi đi từ `>= 30` xuống `< 30` (khớp mẫu `fresh: 30` → tick 1 `spoiled`). | [`chonoi/sim/gather.py`](../../chonoi/sim/gather.py), [`chonoi/sim/quan.py`](../../chonoi/sim/quan.py) | `test_p3_01_contract_v12_spoil_threshold_and_count_map_exit_2` | PASS (`spoil_threshold.jsonl`) |
| AC-P3-03 | Hàng mới `fresh = 100` bắt đầu hao từ bước sau; `pause` đóng băng tươi; ID `I1, I2, ...` tăng liên tục xuyên pha/Ngày; `gather` rơi LIFO dạng `{id, kind, fresh}`. | [`chonoi/sim/gather.py`](../../chonoi/sim/gather.py), [`chonoi/runner.py`](../../chonoi/runner.py) | `test_p3_02_freshness_pause_lifo_and_monotonic_ids`, `test_phase1_rules`, `test_phase2_rules` | PASS |
| AC-P3-04 | Ghi `--inventory-out` một lần khi `gather_end` qua file tạm cùng thư mục rồi `os.replace`, sắp theo `id_key`, giữ chính xác `1/240` qua bàn giao 2 tiến trình (`--ticks 0`). | [`chonoi/inventory.py`](../../chonoi/inventory.py), [`chonoi/runner.py`](../../chonoi/runner.py) | `test_p3_04_cook_items_sorted_base_price_floor_tip_and_handoff` | PASS (`handoff_catch.json`, `handoff_quan.jsonl`) |
| AC-P3-05 | Quán hao `0.25/s` kho thô; nhả toàn bộ giữ chỗ đơn có cá thể vừa ươn & thử giữ lại 1 lần theo `(order_tick, id_key(table_id))` chọn tươi nhất (`id_key` hòa); thiếu chuyển `unfulfillable`. | [`chonoi/sim/quan.py`](../../chonoi/sim/quan.py) | `test_p3_03_quan_spoil_rereserve_and_unfulfillable` | PASS |
| AC-P3-06 | `cook_started` tiêu đúng ID giữ, xuất `items` sắp `(kind, id_key)`, chốt `base_price = floor(giá × avg_fresh / 100)`, boa `floor(base_price × 0.2)`. | [`chonoi/sim/quan.py`](../../chonoi/sim/quan.py) | `test_p3_04_cook_items_sorted_base_price_floor_tip_and_handoff` | PASS |
| AC-P3-07 | Chế độ `day`: Ngày 1 giữ ID mẫu `gather.hold`, Ngày 2+ cấp ID mới tiếp nối; kho `ShopSim` theo schema v1.2 và không hao tươi; lỗi `reserved` thoát mã `2`. | [`chonoi/sim/day.py`](../../chonoi/sim/day.py), [`chonoi/sim/shop.py`](../../chonoi/sim/shop.py), [`chonoi/scenario.py`](../../chonoi/scenario.py) | `test_p3_05_day_v12_ids_shop_no_decay_and_contradictions` | PASS (`day_v12.jsonl`) |
| AC-P3-08 | HUD web hiển thị thanh/số độ tươi từng ô giỏ, `Kho khả dụng` không tính hàng ươn/đã giữ và cảnh báo `ƯƠN (< 30)`. | [`chonoi/web/index.html`](../../chonoi/web/index.html) | `test_live.LiveServerTest`, `test_ac_p2_14_live_server_day_mode` | PASS |

## 2. Lý do cập nhật test cũ P1/P2 khi chuyển sang Contract v1.2

- `[THAY THẾ]` trong Contract v1.2 loại bỏ kho đếm `{kind: count}` và định giá cố định, nên toàn bộ fixture `hold`/`stock`/`reserved` trong `tests/test_smoke_p1.py`, `tests/test_python_starter_units.py`, `tests/test_phase1_rules.py`, và `tests/test_phase2_rules.py` đã được chuyển sang mảng `{id, kind, fresh}` (với bài test từ chối kho đếm cũ tại `test_inv_bad_schema_exit_2`).
- Tại `test_full_cook_serve_tip_boundary_and_reputation_precision` (`120 -> 119`, boa `24 -> 23`), `test_end_to_end_gather_to_quan_and_contract_meta`, và `test_ac_p2_13` (`200 -> 199`, boa `40 -> 39`, thu `238`), giá món giảm đúng theo độ tươi còn lại khi đưa vào bếp ở Contract v1.2.

## 3. Lệnh & Bằng chứng chạy thật

```bash
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
```
- Kết quả lưu tại [`docs/proof/phase-3/test_results.txt`](../proof/phase-3/test_results.txt) (**58/58 test pass**).
- Bằng chứng mẫu Contract v1.2: [`spoil_threshold.jsonl`](../proof/phase-3/spoil_threshold.jsonl), [`handoff_catch.json`](../proof/phase-3/handoff_catch.json), [`handoff_quan.jsonl`](../proof/phase-3/handoff_quan.jsonl), [`day_v12.jsonl`](../proof/phase-3/day_v12.jsonl).
