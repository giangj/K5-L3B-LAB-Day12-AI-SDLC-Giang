# Báo Cáo Kiểm Chứng Phase 4 — Test Contract v1.3 & Release v1.0.0

- **Nhóm:** Giang (thực hiện độc lập, 1 học viên solo 100% Core)
- **Sinh viên:** Lê Danh Giang (MSV: 2A202603912, Email: 26ai.giangld@vinuni.edu.vn)
- **Thời gian thực hiện:** 2026-11-21
- **Môi trường thử nghiệm:** Windows 11 / Python 3.11.9 (stdlib: zlib, struct, math, time)

---

## 1. Bảng đối chiếu Tiêu chí chấp nhận (AC-P4-xx)

| Mã AC | Tiêu chí | Kết quả quan sát | Ngưỡng yêu cầu | Đánh giá | Bằng chứng |
|:---|:---|:---|:---|:---:|:---|
| **AC-P4-01** | Contract v1.3 khai đúng schema | `contract_version: "1.3"`, `bench_cmd`, `soak_cmd` hợp lệ | Có đủ 2 lệnh ở gốc Contract | **ĐẠT** | [game.contract.json](file:///e:/AI_vin20k/lab-12/game.contract.json) |
| **AC-P4-02** | Hiệu năng benchmark cảnh chuẩn | `avg_fps = 313.08`, `p1_low_fps = 76.77`, `load_ms = 13.13` (9,393 frames / 30s) | FPS >= 60, p1-low >= 30, load <= 10s | **ĐẠT** | [bench.json](file:///e:/AI_vin20k/lab-12/docs/proof/phase-4/bench.json), [bench_frame.png](file:///e:/AI_vin20k/lab-12/docs/proof/phase-4/bench_frame.png) |
| **AC-P4-03** | Chạy bền vững nhiều ngày (Soak) | `days_completed = 10`, `crashes = 0`, thời gian `22.903s` (D1..D10 hoàn thành xuất sắc) | 10 ngày, 0 crash, 1 process | **ĐẠT** | [soak.json](file:///e:/AI_vin20k/lab-12/docs/proof/phase-4/soak.json) |
| **AC-P4-04** | 3 Cảnh báo & Tương phản cao | Có đủ chữ & biểu tượng: `⚠ THỦY QUÁI GẦN!`, `⚠ OXY SẮP HẾT!`, `⚠ KHÁCH SẮP GIẬN!`; High Contrast hoạt động mượt qua phím `H` / `?hc=1` | Chữ hoặc biểu tượng, có chế độ HC | **ĐẠT** | [hc_gather_warnings.png](file:///e:/AI_vin20k/lab-12/docs/proof/phase-4/hc_gather_warnings.png), [hc_quan_warning.png](file:///e:/AI_vin20k/lab-12/docs/proof/phase-4/hc_quan_warning.png) |
| **AC-P4-05** | Clone sạch chạy tối đa 3 lệnh | `git clone ... && cd ... && python3 -m chonoi.live --mode day` mở web ngay | Tối đa 3 lệnh | **ĐẠT** | [README.md](file:///e:/AI_vin20k/lab-12/README.md) |
| **AC-P4-06** | Hồi quy toàn bộ test P1–P4 | `62/62 OK` trong 34.153s | Toàn bộ xanh 100% | **ĐẠT** | [test_results.txt](file:///e:/AI_vin20k/lab-12/docs/proof/phase-4/test_results.txt) |

---

## 2. Chi tiết Số liệu Đo đạc Thực tế

### 2.1. Benchmark Cảnh Lặn Sông Buổi Sáng (AC-P4-02)
Lệnh thực hiện:
```powershell
python3 -m chonoi.bench --seed 42 --duration 30 --out docs/proof/phase-4/bench.json --preview docs/proof/phase-4/bench_frame.png
```
Nội dung file `docs/proof/phase-4/bench.json`:
```json
{
  "avg_fps": 313.08,
  "p1_low_fps": 76.77,
  "frames": 9393,
  "measured_s": 30.0023,
  "load_ms": 13.13
}
```
*Nhận xét:*
- Tốc độ khung hình trung bình đạt **313.08 FPS**, gấp **5.2 lần** yêu cầu tối thiểu (>= 60 FPS).
- Tỷ lệ giật khung hình 1% thấp nhất đạt **76.77 FPS**, gấp **2.5 lần** yêu cầu (>= 30 FPS).
- Thời gian tải khung hình đầu tiên chỉ mất **13.13 ms**, thấp hơn rất nhiều so với ngưỡng cho phép (10,000 ms).
- Bộ dựng hình đạt hiệu năng cao nhờ kỹ thuật sao chép mảng nhớ tĩnh trong bộ nhớ (`self.buf[:] = self.bg`) loại bỏ cấp phát rác trên heap.

### 2.2. Kiểm thử Bền vững 10 Ngày (AC-P4-03)
Lệnh thực hiện:
```powershell
python3 -m chonoi.soak --seed 7 --days 10 --out docs/proof/phase-4/soak.json
```
Nội dung file `docs/proof/phase-4/soak.json`:
```json
{
  "days": 10,
  "days_completed": 10,
  "crashes": 0,
  "results": [
    { "day": 1, "earned": 39, "reputation": 3.2, "score": 339 },
    { "day": 2, "earned": 39, "reputation": 3.2, "score": 339 },
    { "day": 3, "earned": 78, "reputation": 3.4, "score": 378 },
    { "day": 4, "earned": 117, "reputation": 3.6, "score": 417 },
    { "day": 5, "earned": 117, "reputation": 3.6, "score": 417 },
    { "day": 6, "earned": 156, "reputation": 3.8, "score": 456 },
    { "day": 7, "earned": 156, "reputation": 3.8, "score": 456 },
    { "day": 8, "earned": 195, "reputation": 4.0, "score": 595 },
    { "day": 9, "earned": 234, "reputation": 4.2, "score": 634 },
    { "day": 10, "earned": 234, "reputation": 4.2, "score": 634 }
  ],
  "duration_s": 22.903
}
```
*Nhận xét:*
- Hệ sinh thái chạy mượt mà 10 ngày đêm liên tục trong 1 tiến trình duy nhất.
- Không rò rỉ bộ nhớ, không crash (`crashes: 0`), doanh thu lũy kế và uy tín tăng trưởng ổn định.

---

## 3. Ảnh Chụp Minh Chứng Chế Độ Tương Phản Cao (AC-P4-04)
1. **Buổi sáng (Lặn sông):**
   - Cảnh báo Thủy quái gần: viền vàng sáng + dòng chữ `⚠ THỦY QUÁI GẦN!` nổi bật ở giữa màn hình.
   - Cảnh báo Oxy: dòng chữ đỏ cam `⚠ OXY SẮP HẾT!` khi oxy dưới 25% dung tích.
   - File lưu: `docs/proof/phase-4/hc_gather_warnings.png`.
2. **Buổi tối (Quán ăn):**
   - Cảnh báo Khách sắp giận: biểu tượng và chữ `⚠ KHÁCH SẮP GIẬN!` ở thanh thông báo trên đỉnh và ngay trên bàn của khách sắp hết lòng kiên nhẫn.
   - File lưu: `docs/proof/phase-4/hc_quan_warning.png`.

---

## 4. Kết luận
Phase 4 hoàn tất 100% mục tiêu: Contract v1.3 chuẩn hóa, hiệu năng vượt ngưỡng, soak test bền bỉ, khả năng tiếp cận tốt với High Contrast, và toàn bộ 62 kiểm thử hồi quy thành công mỹ mãn.
Mã nguồn đã sẵn sàng phát hành bản phát hành chính thức **v1.0.0**.
