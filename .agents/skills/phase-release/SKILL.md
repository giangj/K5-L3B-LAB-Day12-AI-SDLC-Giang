---
name: phase-release
description: Checklist to finalize a phase (update AGENTS.md, docs/verification, docs/clarify.md, docs/ai-usage-log.md, docs/standup.md, CHANGELOG.md, run regression, commit, push, and tag phase-n on main).
---

# Skill: phase-release

Dùng skill này ở bước chốt mỗi phase để đảm bảo đủ DoD trước khi đẩy tag `phase-n`.

## Checklist chốt phase

1. **Cập nhật quy trình & nhật ký**:
   - `AGENTS.md`: bổ sung lệnh, quy ước hoặc bất biến mới của phase hiện tại.
   - `docs/plan/phase-<n>.md`: đối chiếu mục tiêu và AC đã chốt.
   - `docs/clarify.md`: ghi đủ câu hỏi/giả định thiết kế phát sinh trong phase.
   - `docs/standup.md`: ghi dòng tóm tắt giữa phase (đã xong / sắp làm / vướng gì).
   - `docs/ai-usage-log.md`: ghi công cụ/model, việc đã làm, ước lượng token và lỗi AI nếu có.
   - `CHANGELOG.md`: tổng hợp thay đổi theo phase (ghi rõ breaking change nếu có).

2. **Kiểm chứng & bằng chứng**:
   - Gọi skill `verify-contract` chạy toàn bộ bộ test (gồm regression các phase trước).
   - Hoàn thiện `docs/verification/phase-<n>.md` (mỗi `AC-Pn-xx` trỏ tới file bằng chứng thật trong `docs/proof/phase-<n>/` và ghi trung thực `đạt` / `chưa đạt`).

3. **Commit, push và gắn tag trên `main`**:
   - Kiểm tra `git status` không có file rác ngoài ý muốn.
   - Commit toàn bộ thay đổi trên `main` và `git push origin main`.
   - Gắn annotated tag đúng tên `phase-<n>` tại commit bàn giao trên `main` và đẩy tag:
     ```bash
     git tag -a phase-<n> -m "Phase <n>: ..."
     git push origin phase-<n>
     ```
   - Ở Phase 4, tạo thêm GitHub Release `v1.0.0` trỏ tới đúng commit của tag `phase-4`.
