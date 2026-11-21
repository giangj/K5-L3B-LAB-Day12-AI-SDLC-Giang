# Retro nhóm

## Phase 2 (nhanh)
- Điều tốt: Mô hình tách pha (`GatherSim`, `QuanSim`, `ShopSim`, `DaySim`) và `Streams` riêng (`fish_spawn`, `fish_turn`, `customer_dish`) giúp mở rộng từ v1.0 lên v1.1 (8 đàn cá bơi, 2 Cá Sấu, 2 bếp/4 bàn/6 món, vòng Ngày 1–5 + Shop + Pause) mà vẫn giữ tính tất định từng byte.
- Điều tệ: Ban đầu `DaySim.step()` chỉ chép `upgrades` và `money` từ `ShopSim` khi `shop` kết thúc (`done`), làm snapshot giữa pha `shop` bị lệch `{}`; ngoài ra 3 unit/smoke test starter + 2 assert Phase 1 viết cứng hằng số v1.0 cần cập nhật khi Contract lên v1.1.
- 1 hành động cho Phase 3: Trước khi sửa code cho Contract v1.2, viết ADR + Bảng tác động đầy đủ các điểm chạm kho hàng/snapshot giữa pha, và quy định `DaySim` luôn đồng bộ trạng thái từ pha con sau mỗi tick (kể cả chưa `done`).

## Phase 4 (cuối)
- **Rà lại hành động Phase 2:** Đã hoàn thành 100%. Trước khi bước vào Phase 3, nhóm đã lập `docs/adr/0001-freshness-inventory-v12.md`, phân tích bảng tác động chuyển dịch kho cá thể `{"items": [{"id": "I1", ...}]}`, và refactor `DaySim.step()` đồng bộ `money`, `earned`, `reputation`, `upgrades`, `stock` ra lớp ngoài trên từng tick. Nhờ đó Phase 3 và Phase 4 không gặp bất kỳ lỗi lệch trạng thái snapshot nào.
- **Điều tốt:**
  - Kiến trúc Contract-driven phát huy hiệu quả tối đa: tách biệt rõ ràng giữa luật vật lý, mô phỏng sim và giao diện hiển thị web/CLI.
  - Tối ưu hóa hiệu năng render benchmark chuẩn 1280×720 bằng bộ đệm tái sử dụng `self.buf[:] = self.bg` giúp đạt **313.08 FPS** và p1-low **76.77 FPS**, vượt xa chuẩn đề bài.
  - Soak test chạy trơn tru 10 ngày trong 1 tiến trình duy nhất với **0 crashes**, đảm bảo độ tin cậy vận hành lâu dài.
  - Hỗ trợ tốt khả năng tiếp cận (Accessibility) với 3 cảnh báo chữ + biểu tượng `⚠` và chế độ Tương phản cao (High Contrast) dễ dùng.
- **Điều tệ:**
  - Khởi đầu trên môi trường Windows local gặp vấn đề lệnh `python3` trỏ Microsoft Store stub (đã xử lý triệt để bằng shim trong scratch prepended PATH).
  - Một số cú pháp gọi lớp giữa các pha con (như tham số `InputState` trong `soak.py`) ban đầu viết theo giả định trước khi chạy test phát hiện ra.
- **Số liệu:**
  - Số commit theo người: 100% commit và tag thực hiện bởi Lê Danh Giang (@giangj) qua 4 phase (tổng cộng ~25 commits).
  - Cách đọc code: Tự review từng file diff, kiểm tra hợp đồng bất biến (Contract Invariants) và chạy regression toàn bộ test suite trước khi commit/push.
  - Phân bổ công việc: Solo toàn diện cả 4 phase từ kiến trúc, luật chơi, giao diện Canvas, bench/soak đến hồ sơ phát hành.
- **Một lần AI sai và cách nhóm phát hiện:**
  - *Lần 1 (Phase 3):* AI đề xuất dùng kiểu `float` thông thường để tính độ tươi hao hụt theo giây. Nhóm phát hiện số thực float sẽ tích lũy sai số dấu phẩy động làm lệch byte JSONL và sai lệch ngưỡng ươn (`< 30`); nhóm đã chốt giải pháp dùng `fractions.Fraction` với đơn vị `1/240` điểm/tick.
  - *Lần 2 (Phase 4):* Khi sinh mã `chonoi/soak.py`, AI khởi tạo `InputState(move=move, rising=btns, held=btns, buttons=BUTTONS_V11)` do nhớ nhầm constructor. Khi chạy `test_ac_p4_03`, test báo lỗi `unexpected keyword argument 'rising'`. Nhóm kiểm tra lại `chonoi/inputs.py` và sửa thành `InputState(move=move, held=btns, edges=btns, buy=buy)`.
- **Nếu làm lại, đổi gì:**
  - Xây dựng bộ công cụ benchmark và bot soak test tự động ngay từ Phase 1 thay vì đợi tới Phase 4, giúp phát hiện sớm các vấn đề về phân bổ bộ nhớ và hiệu năng của vòng lặp mô phỏng.
