# Changelog

## Phase 1 (2026-11-21) — Test Contract v1.0
- Hoàn thiện kickoff cá nhân (`TEAM.md`, `game.contract.json` với `team="Giang"`, `team_size=1`), hợp đồng tích hợp (`docs/contracts/README.md`) và 2 AI skills (`verify-contract`, `phase-release`).
- Triển khai đầy đủ luật buổi sáng (`chonoi/sim/gather.py`): `dive`/`surface`, oxy dưới nước & hồi trên mặt nước, `oxygen_empty`, đếm ngạt `choke`, `faint` bỏ giỏ LIFO và xuất kho rỗng, hái nút + `node_regrown`, bắt cá dưới nước với hồi chiêu, ưu tiên cập bến (`docked`).
- Triển khai đầy đủ luật buổi tối (`chonoi/sim/quan.py`) & kiểm mâu thuẫn (`chonoi/scenario.py`): lịch khách, giữ chỗ nguyên liệu, `no_dish`, interact ưu tiên `(dist, bếp trước bàn, id)`, nấu/nhấc/phục vụ, tính boa & uy tín chính xác bằng `Decimal`, đóng ca `closing`, trả mã thoát `2` trước khi ghi file khi scenario sai.
- Sửa HUD `chonoi/web/index.html` hiển thị đúng `dish_id` từ payload món trên bếp và `Kho khả dụng`.
- Bổ sung bộ test hộp đen `tests/test_phase1_rules.py` (tổng 42/42 test pass) và bằng chứng thật tại `docs/proof/phase-1/`.

## Unreleased
