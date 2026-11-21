# Clarify — câu hỏi và câu trả lời (PO ghi, cả nhóm dùng chung)

| # | Ngày giờ | Câu hỏi | Trả lời / giả định | Ai quyết |
|---|---|---|---|---|
| 1 | 2026-11-21 16:13 | Làm bài lab cá nhân (1 thành viên, không có nhóm) thì điền `TEAM.md` và `game.contract.json` thế nào? | Ghi trung thực 1 thành viên: Lê Danh Giang (`@giangj`, MSV `2A202603912`), `"team": "Giang"`, `"team_size": 1`. Không sửa `tools/check_team.py` hay `tests/test_team_check.py`. | Giang (`giangj`, PO) |
| 2 | 2026-11-21 16:45 | Có làm các mục Mở rộng (nhóm 5–6 người) ngoài phần Lõi không? | Theo đề bài, nhóm ≤ 4 người không bắt buộc Mở rộng; giữ đúng 100% phạm vi Lõi qua 4 phase, không tự ý thêm tính năng ngoài đề. | Giang (`giangj`, PO) |
| 3 | 2026-11-21 16:50 | Ở `quan`, trên cùng tick đóng ca (`time_left_ticks == 0`) nếu đồng thời còn khách `eating` và khách `waiting`, xử lý theo thứ tự nào? | Theo mục F: xử lý tất cả khách `eating` (trả `paid` với `reason: "closing"`, sắp theo `table_id`) trước rồi mới xử lý khách `waiting` (`customer_left` với `reason: "closing"`, sắp theo `table_id`), sau cùng mới phát `quan_end`. | Giang (`giangj`, PO) |
| 4 | 2026-11-21 16:55 | Tính tỷ lệ kiên nhẫn cho tiền boa (`tip_min_patience_ratio = 0.5`) và cộng/trừ uy tín có rủi ro sai số dấu phẩy động nhị phân không? | Có (`3.0 + 5*0.2` hoặc `3.8 + 0.2` dễ lệch nhị phân trước `math.floor`). Giả định dùng `decimal.Decimal` cho ngưỡng boa, `floor(base_price * tip_rate)` và cộng/trừ uy tín trước khi chuyển `float`. | Giang (`giangj`, PO) |
