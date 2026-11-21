# AGENTS.md — hướng dẫn chung cho mọi agent AI của nhóm

> Cập nhật file này qua các phase (lịch sử git phải cho thấy điều đó). Ngắn gọn, có lệnh chạy thật.

## Lệnh
- Test: `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v`
- Headless:
  - Buổi rời: `python3 -m chonoi.headless --mode gather|quan --seed 1 --ticks 600 --out out.jsonl`
  - Vòng ngày v1.1: `python3 -m chonoi.headless --mode day --days 1 --seed 1 --ticks 22200 --out day.jsonl`
- Chơi thử trên trình duyệt: `python3 -m chonoi.live --mode day` (hoặc `--mode gather|quan`; WASD, E, Space, Esc/P tạm dừng, R chơi lại)
- Lưu ý Windows local: đảm bảo `python3` trỏ tới Python 3.11+ (tạo shim `python3.exe` trong scratch nằm trước trên `PATH`, không sửa `python3` trong `game.contract.json`).

## Cấu trúc & quy ước
- Khung chung: `chonoi/{headless,inputs,scenario,contract,rng,ids,jsonl,inventory,runner,live}.py` và `chonoi/web/`.
- Luật chơi: `chonoi/sim/gather.py`, `chonoi/sim/quan.py`, `chonoi/sim/shop.py`, `chonoi/sim/day.py`, và kiểm mâu thuẫn mức luật trong `chonoi/scenario.py`.
- **Số liệu chỉ đọc từ `game.contract.json` / dữ liệu**, không hard-code trong luật.
- Mọi số ngẫu nhiên đi qua `Streams` (`chonoi/rng.py`); dùng các stream tách biệt (`fish_spawn`, `fish_turn`, `customer_dish`) để tránh lệch chuỗi RNG; không dùng `random` toàn cục hay đồng hồ hệ thống.
- Sắp danh sách thực thể bằng `ids.sort_by_id`; cấp id bằng `IdAllocator`.
- **Bất biến Phase 1 (Contract v1.0):**
  - `gather`: tính oxy theo `d` cuối bước; bước vừa chạm `oxy == 0` dưới nước vẫn tăng `zero_oxy_ticks` (đủ `choke_interval_ticks` mới trừ 1 HP); khi `hp == 0`, bỏ giỏ LIFO phát `faint` rồi `gather_end(fainted)`; tại `interact` ưu tiên bến trước hái; `catch` chỉ dưới nước khi `catch_cd_ticks == 0`; `hold_full` giữ nguyên cá/nút và không đặt hồi chiêu.
  - `quan`: dùng `decimal.Decimal` tính ngưỡng boa (`tip_min_patience_ratio`), boa `floor`, và uy tín; kiểm giữ chỗ `reserved <= stock` khi khởi tạo `QuanSim`; hết giờ thì khách `eating` trả tiền (`closing`), khách `waiting` rời (`closing`, không phạt uy tín).
- **Bất biến Phase 2 (Contract v1.1):**
  - `gather`: thứ tự tick cố định: timer/regrow → bơi/oxy/ngạt (ngạt xuyên bất tử, không rơi hàng) → cập nhật quái theo id & hit (`floor(hold * 0.5)` LIFO, 90 tick bất tử, recoil 60 tick) → `interact` → `catch` (dùng vị trí cá TRƯỚC khi cá bơi!) → hết giờ → cá bơi & phản xạ mép/góc → sinh cá mới (`360·k`, trần 12, clearance > 1 m).
  - `pause`: cạnh lên `pause` chỉ tăng `tick` ngoài và đóng băng `sim_tick`/`phase_tick`/timer; bỏ qua hành động & `buy`; cạnh lên `pause` kế phát `resumed` và chạy gameplay ngay trong tick đó. Giữ nút qua chuyển pha không tạo cạnh mới.
  - `day` & `shop`: trong `day`, menu quán lọc theo `day_plan.dishes`; ngất sáng vẫn mở quán kho rỗng; trong Shop xử lý `buy` trước `shop_done`; nâng cấp `oxygen`/`hp` lưu vào `upgrades` ngay nhưng chỉ chép sang `active_upgrades` khi dựng Ngày kế tiếp.
- **Bất biến Phase 3 (Contract v1.2):**
  - Kho hàng dùng mảng cá thể `{"items": [{"id": "I1", "kind": ..., "fresh": ...}]}` (`exit 2` nếu nhận kho đếm cũ); `I1, I2, ...` cấp liên tục xuyên pha và Ngày; xuất file nguyên tử (`os.replace`) sắp theo `id_key`; LIFO giữ thứ tự vào giỏ.
  - Tính độ tươi bằng `fractions.Fraction` theo đơn vị `1/240` điểm tươi (`0.5/s = 2/240`, `0.25/s = 1/240`); hàng mới `fresh=100` chỉ hao từ bước sau; `paused`, món chín và Shop không hao; phát `spoiled` đúng 1 lần theo `id_key` khi đi từ `>= 30` xuống `< 30`.
  - Ở `quan`, sau khi hao tươi và phát hết `spoiled`, nhả toàn bộ giữ chỗ của các đơn bị ươn và thử giữ lại đúng 1 lần theo `(order_tick, id_key(table_id))` (chọn tươi nhất, hòa theo `id_key`, thiếu chuyển `unfulfillable`); `cook_started` tiêu đúng ID đã giữ, chốt `base_price = floor(list_price * avg_fresh / 100)`, `items` sắp `(kind, id_key)`; boa `floor(base_price * 0.2)`.
  - Trong `DaySim`, đồng bộ `money`/`earned`/`reputation`/`upgrades`/`stock` ra lớp bọc ngay mỗi tick (kể cả khi pha con chưa `done`).

## Nên tránh
- Không sửa `tools/check_team.py` hoặc `tests/test_team_check.py`.
- Không làm hỏng nhánh chính: trước khi đẩy, chạy test.
- Không bịa yêu cầu: chỗ mơ hồ thì ghi `docs/clarify.md`.
- Không sửa test cho xanh khi luật sai; nếu Contract mới thay đổi hành vi cũ (v1.0 → v1.1), ghi rõ lý do trong commit và `docs/verification/`.

## Skills / hooks của nhóm
- `verify-contract` ([`.agents/skills/verify-contract/SKILL.md`](.agents/skills/verify-contract/SKILL.md))
- `phase-release` ([`.agents/skills/phase-release/SKILL.md`](.agents/skills/phase-release/SKILL.md))
