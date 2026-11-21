# Kế hoạch Phase 1 (≤ 1 trang)

- **Mục tiêu:** Hoàn thiện lõi 2 buổi sáng (`gather`) và tối (`quan`) theo đúng PRD-0 & Test Contract v1.0, bàn giao kho 2 tiến trình qua file JSON nguyên tử, cập nhật UI đọc snapshot đúng và đẩy tag `phase-1` trên `main` với đủ bộ kiểm thử và bằng chứng thật.

- **Việc / người / phụ thuộc (làm độc lập 1 thành viên — `giangj`):**
  1. **Kickoff & Contract (`AC-P1-01`, `AC-P1-02`)**: Điền `TEAM.md` (`team_size=1`), `game.contract.json` (`team="Giang"`, `team_size=1`), chốt `docs/contracts/README.md`, viết 2 AI skills trong `.agents/skills/` và cập nhật `AGENTS.md`. *(Không phụ thuộc — làm trước).*
  2. **Lát 1 & 2 — `chonoi/sim/gather.py` (`AC-P1-03` .. `AC-P1-07`)**: Triển khai `dive`/`surface`, tiêu & hồi oxy, đếm ngạt `zero_oxy_ticks` (`choke` ở `t+59`), `faint` bỏ giỏ LIFO và xuất kho rỗng, hái nút trên mặt nước (`gather`, `hold_full`, `node_regrown`), bắt cá dưới nước (`catch`, `fish_caught`, `catch_cd_ticks`, `hold_full`), ưu tiên bến và hành động ở tick cuối. *(Phụ thuộc Bước 1).*
  3. **Lát 3 & 4 — `chonoi/scenario.py` & `chonoi/sim/quan.py` (`AC-P1-08` .. `AC-P1-13`)**: Bổ sung kiểm tra mâu thuẫn scenario (`BadInput` → mã 2); triển khai lịch khách, chọn món đều trong các món nấu được, giữ chỗ nguyên liệu, `no_dish`, tương tác `(dist, bếp trước bàn, id)`, nấu/bưng/phục vụ, tính boa (`Decimal`), thanh toán & uy tín, đóng ca (`closing`) và `quan_end`. *(Phụ thuộc Bước 1; song song với Bước 2 trên cùng hợp đồng kho).*
  4. **Client UI — `chonoi/web/index.html` (`AC-P1-14`)**: Sửa hiển thị payload món trên bếp (`dish.dish_id`) và hiển thị kho khả dụng (trừ phần khách đang giữ chỗ), trạng thái đơn khách hàng. *(Phụ thuộc Bước 3).*
  5. **QA, Proofs & Release tag `phase-1`**: Viết bộ test hộp đen `tests/test_phase1_rules.py`, chạy kiểm chứng toàn bộ + smoke 2 tiến trình, lưu bằng chứng vào `docs/proof/phase-1/`, điền `docs/verification/phase-1.md`, `docs/clarify.md`, `docs/standup.md`, `docs/ai-usage-log.md`, `CHANGELOG.md`, `README.md`, gắn tag `phase-1`. *(Phụ thuộc Bước 2, 3, 4).*

- **Rủi ro & giảm thiểu:**
  - *Sai khác thứ tự xử lý trong tick hoặc điều kiện biên (tick chạm oxy 0, tick cuối ca, tick kiên nhẫn về 0):* bám sát từng dòng mục F Test Contract v1.0 và viết test biên riêng cho từng trường hợp.
  - *Sai số dấu phẩy động ở tỷ lệ boa 0.5 hoặc uy tín cộng/trừ:* dùng `decimal.Decimal` để tính toán chính xác trước khi làm tròn hoặc `math.floor`.
  - *Cảnh báo `check_team.py` trong CI khi `team_size=1`:* giữ nguyên `tools/check_team.py` và `tests/test_team_check.py`; CI chạy với `continue-on-error: true` nên không làm hỏng pipeline.
