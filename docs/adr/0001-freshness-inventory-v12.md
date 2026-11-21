# ADR-0001: Chuyển kho đếm theo loại sang kho cá thể `{id, kind, fresh}` (Test Contract v1.2)

- **Trạng thái:** Đã duyệt & triển khai (Phase 3 — TICKET-03)
- **Ngày:** 2026-11-21
- **Người quyết định:** Lê Danh Giang (`@giangj`, PO / Kỹ sư phụ trách)

## 1. Bối cảnh (Context)

Ở Contract v1.0 và v1.1, kho nguyên liệu (`hold`, `stock`, file `--inventory-out` / `--inventory`, và `reserved` của khách) sử dụng **kho đếm theo loại** (`{"items": {"ca_linh": 2, "ca_loc": 1}}`). Sang Phase 3 (TICKET-03 *Mùa Nước Nổi*), mỗi nguyên liệu từ lúc bắt/hái đều có vòng đời **độ tươi (`fresh`)** giảm theo thời gian thực (`0.5/s` trong giỏ buổi sáng, `0.25/s` trong kho quán buổi tối), có ngưỡng ươn (`< 30`), phát sự kiện `spoiled` đúng 1 lần theo từng cá thể, giữ chỗ theo `id` tươi nhất, và chốt giá món ăn theo độ tươi trung bình (`floor(giá niêm yết × avg_fresh / 100)`).

Kho đếm theo loại không thể phân biệt 2 con `ca_linh` có độ tươi khác nhau hay giữ chỗ đúng cá thể vừa bị ươn, do đó bắt buộc phải thay thế hợp đồng kho.

## 2. Quyết định (Decision)

1. **Thay thế schema kho ở Contract v1.2:**
   - Định dạng file kho & snapshot là danh sách cá thể:
     ```json
     {"items": [{"id": "I1", "kind": "ca_linh", "fresh": 100}, {"id": "I2", "kind": "ca_loc", "fresh": 97.5}]}
     ```
   - File kho đếm dạng dict cũ bị **từ chối với mã thoát `2`** (`BadInput`) trong Contract v1.2.
   - `id` cấp tuần tự `I1, I2, ...` qua `IdAllocator` giữ liên tục xuyên pha (`gather -> quan`) và xuyên Ngày (`day`), không tái sử dụng hay đặt lại sau khi tiêu/rơi/ươn.
   - Thứ tự bỏ hàng LIFO (`monster_hit`, `faint`) giữ đúng thứ tự vào giỏ; xuất file kho sắp xếp theo `id_key` (`sort_by_id`) và ghi nguyên tử qua file tạm cùng thư mục rồi `os.replace`.

2. **Tính chính xác tại ngưỡng `30` và phép `floor`:**
   - Toàn bộ phép tính độ tươi bên trong `chonoi/sim/*` sử dụng **`fractions.Fraction`** chính xác tuyệt đối theo bội số `1/240` điểm tươi/tick (`0.5 / 60 = 2/240` ở `gather`, `0.25 / 60 = 1/240` ở `quan`), tránh hoàn toàn sai số dấu phẩy động nhị phân (ví dụ `30.0 - 60*(0.5/60)` hay `99.99166666666666` qua bàn giao JSON).
   - Khi đọc lại JSON (`snap_fresh`), nếu `val * 240` sai khác số nguyên trong phạm vi `1e-9` thì quy về đúng `Fraction(round(val * 240), 240)`; ngược lại giữ `Fraction(str(val))` để không bẻ sai các fixture gần biên (`29.999`, `30.001`).

3. **Thứ tự xử lý tick & giữ chỗ trong quán:**
   - **Gather:** timer/cooldown/hồi nút và hao tươi `hold` sẵn có ở đầu bước (phát `spoiled` theo `id_key`) → bơi/oxy/ngạt → thủy quái/hit (`lost` dạng list dict LIFO) → bến/hái (`fresh=100`, hao từ bước sau) → bắt cá → xét hết giờ → cá bơi/sinh.
   - **Quan:** đồng hồ/timer → hao tươi `stock` thô, phát hết `spoiled` theo `id_key`, sau đó với các đơn `waiting` bị ảnh hưởng bởi cá thể vừa ươn, xử lý theo `(order_tick, id_key(table_id))`: nhả toàn bộ phần giữ cũ và thử giữ lại đúng 1 lần theo tươi nhất (hòa theo `id_key`), thiếu thì chuyển `unfulfillable` → nấu/chín → di chuyển/tương tác (`cook_started` tiêu đúng ID đã giữ, chốt `base_price` và `items` sắp theo `(kind, id_key)`) → thanh toán/kiên nhẫn/đóng ca → khách mới.

## 3. Bảng phân tích tác động (Impact Analysis)

| Module / Lớp | File cần sửa | Thay đổi chính | Test bị ảnh hưởng | Phụ trách |
|---|---|---|---|---|
| Contract & Schema | [`game.contract.json`](../../game.contract.json), [`chonoi/__init__.py`](../../chonoi/__init__.py), [`chonoi/contract.py`](../../chonoi/contract.py) | `contract_version: "1.2"`, thêm `tuning.freshness` (`100`, `0.5`, `0.25`, `30`) | `test_phase1_rules.py`, `test_phase2_rules.py`, `test_smoke_p1.py` | `giangj` |
| Adapter Kho | [`chonoi/inventory.py`](../../chonoi/inventory.py), [`docs/contracts/inventory.sample.json`](../contracts/inventory.sample.json) | `snap_fresh` (`Fraction`), `validate_items_list`, từ chối count-map (`exit 2`), atomic `os.replace` theo `id_key` | `test_smoke_p1.py` (`Integration`), `test_python_starter_units.py` | `giangj` |
| Buổi sáng (`Gather`) | [`chonoi/sim/gather.py`](../../chonoi/sim/gather.py) | `hold` lưu `{id, kind, fresh: Fraction}`, cấp ID `I1..`, hao `0.5/s` đầu tick, `spoiled`, `lost` LIFO dict | `test_smoke_p1.py`, `test_phase1_rules.py`, `test_phase2_rules.py`, `test_phase3_rules.py` (mới) | `giangj` |
| Quán (`Quan`) | [`chonoi/sim/quan.py`](../../chonoi/sim/quan.py) | `stock` list cá thể, hao `0.25/s`, `spoiled`, nhả & giữ lại 1 lần theo `(order_tick, table_id)`, `unfulfillable`, chốt giá & boa theo `avg_fresh` | `test_phase1_rules.py`, `test_phase2_rules.py`, `test_phase3_rules.py` (mới) | `giangj` |
| Ngày & Tiệm (`Day`/`Shop`) | [`chonoi/sim/day.py`](../../chonoi/sim/day.py), [`chonoi/sim/shop.py`](../../chonoi/sim/shop.py) | Chia sẻ `IdAllocator` xuyên Ngày cho ID `I`, bàn giao `hold -> stock` cùng tick không hao thêm, `ShopSim.stock` giữ schema cá thể không hao | `test_phase2_rules.py`, `test_phase3_rules.py` (mới) | `giangj` |
| Scenario Validator | [`chonoi/scenario.py`](../../chonoi/scenario.py) | Nhận `gather.hold`, `quan.stock` dạng mảng cá thể, `customers[].reserved` mảng ID; kiểm duy nhất ID toàn cục, auto-reserve; Ngày 2+ cấp ID mới | `test_phase1_rules.py`, `test_phase2_rules.py`, `test_phase3_rules.py` | `giangj` |
| HUD Trình duyệt | [`chonoi/web/index.html`](../../chonoi/web/index.html) | Hiển thị độ tươi từng cá thể trong giỏ/kho (thanh màu + số) & gắn nhãn/viền cảnh báo hàng `ƯƠN (< 30)` | Kiểm live `test_live.py`, `test_phase2_rules.py` | `giangj` |

## 4. Thứ tự tích hợp giữ `main` luôn chạy được

1. Cập nhật tài liệu kế hoạch, ADR, `game.contract.json` (`1.2`), `chonoi/contract.py`, `chonoi/inventory.py` và `docs/contracts/*`.
2. Cập nhật lõi mô phỏng `gather.py` → `quan.py` → `shop.py` → `day.py` → `scenario.py` theo cùng hợp đồng `list[{id, kind, fresh}]`.
3. Cập nhật HUD `chonoi/web/index.html` + chuyển đổi fixture các bài test P1/P2 sang schema v1.2 (ghi rõ lý do chuyển fixture tại `CHANGELOG.md` và `docs/verification/phase-3.md`) rồi đẩy `main` xanh toàn bộ.
4. Viết mới `tests/test_phase3_rules.py` (`AC-P3-01`..`AC-P3-12`), tạo bộ bằng chứng tại `docs/proof/phase-3/`, hoàn tất verification & gắn thẻ `phase-3`.
