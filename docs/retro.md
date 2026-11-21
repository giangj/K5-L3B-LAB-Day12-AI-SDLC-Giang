# Retro nhóm

## Phase 2 (nhanh)
- Điều tốt: Mô hình tách pha (`GatherSim`, `QuanSim`, `ShopSim`, `DaySim`) và `Streams` riêng (`fish_spawn`, `fish_turn`, `customer_dish`) giúp mở rộng từ v1.0 lên v1.1 (8 đàn cá bơi, 2 Cá Sấu, 2 bếp/4 bàn/6 món, vòng Ngày 1–5 + Shop + Pause) mà vẫn giữ tính tất định từng byte.
- Điều tệ: Ban đầu `DaySim.step()` chỉ chép `upgrades` và `money` từ `ShopSim` khi `shop` kết thúc (`done`), làm snapshot giữa pha `shop` bị lệch `{}`; ngoài ra 3 unit/smoke test starter + 2 assert Phase 1 viết cứng hằng số v1.0 cần cập nhật khi Contract lên v1.1.
- 1 hành động cho Phase 3: Trước khi sửa code cho Contract v1.2, viết ADR + Bảng tác động đầy đủ các điểm chạm kho hàng/snapshot giữa pha, và quy định `DaySim` luôn đồng bộ trạng thái từ pha con sau mỗi tick (kể cả chưa `done`).

## Phase 4 (cuối)
- Rà lại hành động Phase 2: đã làm chưa? vì sao?
- Điều tốt / điều tệ:
- Số liệu: số commit theo người, cách đọc code của nhau, token theo người:
- Một lần AI sai và cách nhóm phát hiện:
- Nếu làm lại, đổi gì:
