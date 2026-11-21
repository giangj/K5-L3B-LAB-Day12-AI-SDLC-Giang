---
name: verify-contract
description: Verify game.contract.json, run full black-box & unit tests, check byte-level determinism and two-process inventory handoff, and store proof artifacts under docs/proof/phase-n/.
---

# Skill: verify-contract

Dùng skill này mỗi khi hoàn thiện một lát chức năng hoặc trước khi gắn tag phase (`phase-1` … `phase-4`).

## Các bước thực hiện

1. **Kiểm tra cấu hình contract (`game.contract.json`)**:
   - Xác nhận `contract_version`, `team` (`"Giang"`), `team_size` (`1` khớp `TEAM.md`), `build_cmd`, `run_cmd`, `headless_cmd`.
   - Kiểm tra các thông số `tuning` khớp đúng đặc tả của phase hiện tại.

2. **Chạy `build_cmd` và toàn bộ bộ test**:
   ```bash
   PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
   ```
   - Yêu cầu: **100% test pass** (thoát mã `0`).

3. **Kiểm tra tính tất định từng byte (Determinism)**:
   - Chạy cùng `--mode`, `--seed`, `--ticks`, `--inputs`, `--scenario` 2 lần ra `o1.jsonl` và `o2.jsonl`.
   - So sánh từng byte (trên Windows `fc /b` hoặc Python `read_bytes()`; trên Linux/macOS `cmp`). Phải giống hệt nhau 100%.

4. **Kiểm tra bàn giao kho 2 tiến trình (`gather` → `quan`)**:
   - Chạy `--mode gather ... --inventory-out catch.json --out gather.jsonl`.
   - Chạy `--mode quan ... --inventory catch.json --ticks 0 --out quan.jsonl`.
   - Đối chiếu `gather_end.data.inventory`, nội dung `catch.json`, và `snapshot.stock` của `quan.jsonl` tại tick 0.

5. **Lưu bằng chứng thật**:
   - Lưu log chạy test và các file JSON/JSONL kiểm chứng thực tế vào `docs/proof/phase-<n>/`.
   - Liên kết trực tiếp vào bảng truy vết `docs/verification/phase-<n>.md`.
