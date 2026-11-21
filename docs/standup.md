# Standup giữa phase (mỗi người một dòng, 2–3 phút)

| Phase | Người | Đã xong | Sắp làm | Vướng gì |
|---|---|---|---|---|
| P1 | `giangj` | Kickoff `TEAM.md`, contract v1.0, 2 skills, `gather.py`, `scenario.py`, `quan.py`, fix `web/index.html` | Viết `tests/test_phase1_rules.py`, tạo proof 2 tiến trình, cập nhật ma trận & gắn tag `phase-1` | Trên Windows `python3` trỏ Store alias → dùng shim `python3.exe` trong scratch trên `PATH`, giữ nguyên `game.contract.json` |
| P2 | `giangj` | Nâng cấp Contract v1.1 (`game.contract.json`), đàn cá bơi & sinh cá `360*k`, Cá Sấu M1/M2 (patrol/chase/hit/recoil), 2 bếp/4 bàn/6 món, `Pause` (`Esc`/`P`), `ShopSim`, `DaySim` (D1–D5), HUD web & Menu | Tạo proof `docs/proof/phase-2/`, cập nhật `docs/verification/phase-2.md`, `docs/retro.md`, gắn tag `phase-2` | Phát hiện `DaySim.step()` đồng bộ `upgrades`/`money` muộn lúc `shop.done` → đã sửa đồng bộ mỗi tick (`test_ac_p2_07..10` xanh) |
