# TEAM

**Tên nhóm:** Giang  **Số người:** 1  (khớp `team_size` trong `game.contract.json`)

| Thành viên | GitHub handle | Module chính | Vai quy trình | Người dự phòng cho |
|---|---|---|---|---|
| Lê Danh Giang (MSV: 2A202603912 · 26ai.giangld@vinuni.edu.vn) | giangj | `sim/gather`, `sim/quan`, `client/ui`, `qa` | PO, Integrator, QA lead, Scrum/Release | Tự kiểm chéo bằng bộ test hộp đen & checklist DoD |

**Vai quy trình:** PO (đầu mối hỏi giảng viên, giữ `docs/clarify.md`) · Integrator (giữ `docs/contracts/`, gắn tag) · QA lead · Scrum/Release. Có thể kiêm.

## Thỏa thuận làm việc nhóm (điền trong 15 phút kickoff, ≤ 10 dòng)

- Kênh liên lạc: Làm độc lập 1 thành viên (`giangj`), mọi trao đổi và giả định thiết kế với AI được ghi trực tiếp trong `docs/clarify.md`.
- Khi bất đồng về thiết kế hoặc gặp điểm mơ hồ: Dựa trên Test Contract & PRD của từng phase; tự quyết giả định hợp lệ và ghi lại lý do vào `docs/clarify.md` (kèm ADR nếu đổi hợp đồng/schema).
- Khi vướng quá 10 phút: Tách nhỏ lát việc, đối chiếu lại `docs/contracts/` và chạy kiểm thử hộp đen để khoanh vùng nguyên nhân.
- Giờ standup giữa phase: Rà tiến độ giữa mỗi phase và ghi lại tóm tắt vào `docs/standup.md`.
- Cách đọc code của nhau: Tự rà soát diff từng lát chức năng trước khi commit và kiểm chứng chéo bằng bộ test tự động.
- Cách làm việc với Git: Commit trực tiếp theo từng lát hoàn chỉnh lên nhánh `main` (bằng tài khoản `giangj`), luôn chạy `python3 -m unittest discover -s tests -v` xanh trước khi push, gắn tag `phase-1`…`phase-4` trên `main` khi đạt DoD.
