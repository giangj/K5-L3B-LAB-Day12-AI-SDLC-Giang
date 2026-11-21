# Ma trận kiểm chứng — Phase 2 (TICKET-02 & Test Contract v1.1)

- **Ngày kiểm chứng:** 2026-11-21
- **Người thực hiện:** Lê Danh Giang (`@giangj`)
- **Trạng thái tổng thể:** ĐẠT (`53/53` test pass trong `docs/proof/phase-2/test_results.txt`)

## 1. Bảng truy vết Yêu cầu ↔ Mã nguồn ↔ Kiểm thử ↔ Bằng chứng

| ID | Yêu cầu (Contract v1.1 / PRD / TICKET-02) | Mã nguồn chính | Kiểm thử tự động (`tests/test_phase2_rules.py`) | Bằng chứng / Kết quả |
|---|---|---|---|---|
| AC-P2-01 | `game.contract.json` đạt chuẩn `1.1`: 6 nút hái (gồm `keo_neo`), `fish_initial=8`, 3 loài (`ca_linh`, `ca_loc`, `ca_keo`), Cá Sấu `M1`/`M2`, 2 bếp `B1`/`B2`, 4 bàn `T1..T4`, 6 món thực đơn, `day_plan` D1–D5, `shop.upgrades` (`oxygen`, `hp`). | [`game.contract.json`](../../game.contract.json), [`chonoi/contract.py`](../../chonoi/contract.py), [`chonoi/inventory.py`](../../chonoi/inventory.py) | `test_ac_p2_01_contract_v11_structure` | PASS |
| AC-P2-02 | Đàn cá bơi `1.5 m/s`, đổi hướng theo `fish_turn` (`120` tick), phản xạ mép & góc, sinh đàn mới tại `360·k` với `clearance > 1 m`, tối đa `12` đàn. | [`chonoi/sim/gather.py`](../../chonoi/sim/gather.py) | `test_ac_p2_02_fish_swim_reflection_and_spawn` | PASS |
| AC-P2-03 | Thủy quái Cá Sấu (`M1` mọi ngày, `M2` từ Ngày 3) tuần tra `patrol`, rượt `chase` khi vào tầm và dưới mặt nước, đánh `monster_hit` trừ `1` HP, rơi `floor(hold*0.5)` LIFO, `90` tick bất tử, `60` tick `recoil`, `hp==0` phát `faint(cause="monster")`. | [`chonoi/sim/gather.py`](../../chonoi/sim/gather.py) | `test_ac_p2_03_monster_patrol_chase_hit_recoil_and_faint` | PASS |
| AC-P2-04 | Ngạt nước (`choke`) xuyên trạng thái bất tử (`invuln_ticks > 0`) và không làm rơi hàng trong giỏ (`lost`). | [`chonoi/sim/gather.py`](../../chonoi/sim/gather.py) | `test_ac_p2_04_choke_pierces_invuln_without_item_drop` | PASS |
| AC-P2-05 | Quán tối mở rộng 2 bếp `B1`/`B2` nấu song song, 4 bàn `T1..T4`, đủ 6 món (kể cả `lau_mam` 200đ / 720 tick). | [`chonoi/sim/quan.py`](../../chonoi/sim/quan.py) | `test_ac_p2_05_two_stoves_four_tables_and_new_dishes` | PASS |
| AC-P2-06 | `pause` theo cạnh lên (`Esc`/`P`): đóng băng `sim_tick`, `phase_tick` và toàn bộ bộ đếm; bỏ qua di chuyển, `interact`, `catch`, `buy`, `shop_done`; cạnh lên kế phát `resumed` và chạy gameplay ngay trong tick đó; giữ nút qua chuyển pha không tạo cạnh mới. | [`chonoi/runner.py`](../../chonoi/runner.py), [`chonoi/inputs.py`](../../chonoi/inputs.py) | `test_ac_p2_06_pause_freezes_sim_and_preserves_button_edge` | PASS |
| AC-P2-07 | Chế độ `--mode day --days 1..5`: chạy tuần hoàn `gather -> quan -> shop` liên tục, phát `day_start`, `day_plan`, `phase_start`, `gather_end`, `quan_end`, `shop_end`, kết thúc `days_complete`. | [`chonoi/sim/day.py`](../../chonoi/sim/day.py), [`chonoi/headless.py`](../../chonoi/headless.py) | `test_ac_p2_07_to_10_day_mode_menu_filter_shop_and_multiday_upgrades` | PASS (`day_smoke.jsonl`) |
| AC-P2-08 | Ngất buổi sáng vẫn chuyển sang buổi tối với kho rỗng (`stock == {}`); thực đơn quán trong `day` lọc theo `day_plan.dishes`. | [`chonoi/sim/day.py`](../../chonoi/sim/day.py), [`chonoi/sim/quan.py`](../../chonoi/sim/quan.py) | `test_ac_p2_07_to_10_day_mode_menu_filter_shop_and_multiday_upgrades` | PASS |
| AC-P2-09 | `ShopSim`: xử lý `buy` trước `shop_done`, kiểm đủ tiền (`funds`), tối đa cấp (`max_level`), tên lạ (`unknown`), cập nhật `upgrades` và `money` vào snapshot `DaySim` ngay trên tick mua. | [`chonoi/sim/shop.py`](../../chonoi/sim/shop.py), [`chonoi/sim/day.py`](../../chonoi/sim/day.py) | `test_ac_p2_07_to_10_day_mode_menu_filter_shop_and_multiday_upgrades` | PASS (`day_smoke.jsonl`) |
| AC-P2-10 | Nâng cấp `oxygen` / `hp` chỉ áp dụng vào `active_upgrades` (`oxygen_max_ticks = 2700`, `hp_max`) khi khởi tạo Ngày kế tiếp; Ngày 3 trở đi tự động xuất hiện `M2`. | [`chonoi/sim/day.py`](../../chonoi/sim/day.py) | `test_ac_p2_07_to_10_day_mode_menu_filter_shop_and_multiday_upgrades` | PASS (`day_smoke.jsonl`: Day 2 `oxygen_max_ticks = 2700`) |
| AC-P2-11 | Mọi mâu thuẫn scenario của `day`, `monsters` hoặc trường v1.1 đều thoát mã `2` trước khi tạo file output. | [`chonoi/scenario.py`](../../chonoi/scenario.py) | `test_ac_p2_11_day_scenario_contradictions_exit_2` | PASS |
| AC-P2-12 | Hiệu năng & tất định trọn 1 Ngày headless (`<= 22200` tick): chạy `< 20s` và 2 lần chạy cho file JSONL giống nhau từng byte. | [`chonoi/sim/day.py`](../../chonoi/sim/day.py), [`chonoi/headless.py`](../../chonoi/headless.py) | `test_ac_p2_12_full_day_performance_and_determinism` | PASS |
| AC-P2-13 | Bàn giao 2 tiến trình với nguyên liệu mới (`ca_keo`, `keo_neo`) sang quán nấu và phục vụ món `lau_mam` (200đ + 40đ boa = 240đ). | [`chonoi/inventory.py`](../../chonoi/inventory.py), [`chonoi/sim/quan.py`](../../chonoi/sim/quan.py) | `test_ac_p2_13_two_process_handoff_v11_ingredients` | PASS (`integration.json`, `integration_quan.jsonl`) |
| AC-P2-14 | Giao diện web `chonoi.live` hỗ trợ `--mode day`, nút `Pause` (`Esc`/`P`), màn hình mở đầu Ngày/Tối, màn hình Shop nâng cấp, cảnh báo `Thủy quái!` + viền tím, HUD `>= 18px`. | [`chonoi/live.py`](../../chonoi/live.py), [`chonoi/web/index.html`](../../chonoi/web/index.html) | `test_ac_p2_14_live_server_day_mode` | PASS |

## 2. Lý do cập nhật các bài test cũ khi nâng Contract từ v1.0 lên v1.1

Theo quy định tại [`AGENTS.md`](../../AGENTS.md), khi Contract v1.1 thay đổi cấu hình mặc định hoặc mở rộng tập nút/mode so với v1.0, các khẳng định viết cứng v1.0 đã được cập nhật kèm giải trình rõ ràng ở commit `f6f7392`:

1. `tests/test_smoke_p1.py`:
   - `test_gather_snapshot_has_gather_fields`: trước đây kiểm `len(s["fish"]) == 6` (v1.0), nay đọc từ `tuning_gather()["fish_initial"]` (`8` đàn cá ở v1.1).
   - `test_con_03_bad_input_exit_2`: thay `"attack"` bằng `"fly"` khi kiểm nút lạ vì v1.1 đã định nghĩa `"attack"` trong bảng nút.
   - `test_con_03_old_and_future_modes_rejected`: thay `"day"` bằng `"arena"` khi kiểm mode lạ vì v1.1 chính thức hỗ trợ `--mode day`.
2. `tests/test_python_starter_units.py`:
   - `test_catch_is_a_v10_button_and_attack_is_not`: giữ kiểm tra từ chối `"attack"` với `buttons=BUTTONS_V10`, đồng thời kiểm bảng nút mặc định v1.1 chấp nhận `"attack"` và từ chối `"jump"`.
3. `tests/test_phase1_rules.py`:
   - `test_customer_schedule_reservation_and_no_dish`: trước đây v1.0 chỉ có 1 bàn `T1` nên không có `no_dish` ở tick 1020; từ v1.1 có 4 bàn `T1..T4` nên kỳ vọng `no_dish` ở tick 1020 khi `len(tables) > 1` (vẫn giữ nhánh `[]` nếu `len(tables) == 1`).
   - `test_end_to_end_gather_to_quan_and_contract_meta`: chấp nhận `contract_version` thuộc `("1.0", "1.1", "1.2", "1.3")` và đối chiếu `base_price` / `tip` theo `menu[dish_id]` khi khách có thể gọi món mới ở v1.1.

## 3. Lệnh kiểm chứng & Bằng chứng thực tế

```bash
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
```
- Kết quả (`docs/proof/phase-2/test_results.txt`): **`Ran 53 tests in 24.891s — OK`**.
- Bằng chứng 2 tiến trình v1.1:
  - [`docs/proof/phase-2/integration.json`](../proof/phase-2/integration.json): `{"items":{"bong_dien_dien":1,"ca_keo":1,"ca_linh":2,"keo_neo":1}}`
  - [`docs/proof/phase-2/integration_quan.jsonl`](../proof/phase-2/integration_quan.jsonl): `cook_started(dish_id="lau_mam", base_price=200)` ở tick `1` → `served` ở tick `919` → `paid(amount=240)` ở tick `1519`, cuối lượt `earned=240, reputation=3.2, score=540`.
- Bằng chứng vòng Ngày & nâng cấp Shop:
  - [`docs/proof/phase-2/day_smoke.jsonl`](../proof/phase-2/day_smoke.jsonl): Ngày 1 pha `shop` mua `oxygen` lv1 (`200`đ) tại tick `13`, `upgrades == {"oxygen": 1}` ngay trên snapshot `shop`, còn `active_upgrades == {}`; sang Ngày 2 pha `gather`, `active_upgrades == {"oxygen": 1}` và `oxygen_max_ticks == 2700`.
