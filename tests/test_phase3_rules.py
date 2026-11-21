"""Kiểm thử hộp đen Phase 3 (TICKET-03 & Test Contract v1.2 — Độ tươi nguyên liệu)."""

import json
import math
import unittest

from chonoi.contract import load_contract
from helpers import Workdir, events, frames, read_jsonl, run_headless, snapshots, write_json


class Phase3FreshnessRules(unittest.TestCase):
    def test_p3_01_contract_v12_spoil_threshold_and_count_map_exit_2(self):
        """Contract v1.2, ngưỡng spoiled < 30 đúng tick 1 theo id_key, từ chối kho đếm cũ (exit 2)."""
        c = load_contract()
        self.assertIn(c["contract_version"], ("1.2", "1.3"))
        self.assertEqual(c["tuning"]["freshness"], {
            "initial": 100,
            "gather_decay_per_s": 0.5,
            "quan_decay_per_s": 0.25,
            "spoiled_below": 30,
        })
        with Workdir() as w:
            # Từ chối file kho đếm theo loại với exit 2
            old_inv = write_json(w.path("old.json"), {"items": {"ca_linh": 2}})
            self.assertEqual(run_headless("--mode", "quan", "--seed", "1", "--ticks", "0",
                                          "--inventory", old_inv, "--out", w.path("q.jsonl"))[0], 2)

            # Kịch bản chuẩn trong đề: fresh=30 ở gather không input -> tick 1 phát spoiled, sau đó không phát lặp
            # Nhiều cá thể cùng vượt ngưỡng phát theo id_key (I2 trước I10), hàng < 30 sẵn không phát thêm
            sc = write_json(w.path("sc.json"), {"gather": {
                "hold": [
                    {"id": "I10", "kind": "ca_linh", "fresh": 30},
                    {"id": "I2", "kind": "ca_loc", "fresh": 30},
                    {"id": "I1", "kind": "bong_sung", "fresh": 29},
                ],
                "random_fish": False,
                "monsters": [],
            }})
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "5",
                                     "--scenario", sc, "--out", w.path("g.jsonl"))
            self.assertEqual(code, 0, err)
            sp = events(read_jsonl(w.path("g.jsonl")), "spoiled")
            self.assertEqual([(e["tick"], e["data"]) for e in sp], [
                (1, {"item_id": "I2", "kind": "ca_loc", "location": "hold"}),
                (1, {"item_id": "I10", "kind": "ca_linh", "location": "hold"}),
            ])

    def test_p3_02_freshness_pause_lifo_and_monotonic_ids(self):
        """Hàng mới fresh=100 hao từ bước sau, pause đóng băng tươi, LIFO và ID I1.. liên tục."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"gather": {
                "player": {"pos": [12, 0]},  # sát N1 [12,0] (bong_dien_dien)
                "hold": [
                    {"id": "I2", "kind": "ca_loc", "fresh": 100},
                    {"id": "I5", "kind": "bong_sung", "fresh": 100},
                ],
                "random_fish": False,
                "monsters": [],
            }})
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "interact": True},   # nhặt I6 ở tick 1 (fresh=100 lúc nhặt, chưa hao ở tick 1)
                {"tick": 1, "interact": False, "pause": True},  # vào pause ở tick 2
                {"tick": 2, "pause": False},     # nhả nút pause
                {"tick": 4, "pause": True},      # cạnh lên thứ 2 -> resume & chạy sim_tick=2 ở tick 5
                {"tick": 5, "pause": False, "move": [-1, 0]},
            ))
            inv = w.path("inv.json")
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "10",
                                     "--scenario", sc, "--inputs", inp, "--snapshot-every", "1",
                                     "--inventory-out", inv, "--out", w.path("g.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("g.jsonl"))
            snaps = {s["tick"]: s for s in snapshots(rows)}
            # tick 1 vừa hái I6 -> I6.fresh == 100
            self.assertEqual(snaps[1]["hold"][-1], {"id": "I6", "kind": "bong_dien_dien", "fresh": 100})
            # Đang pause từ tick 2..4 -> I2/I6 giữ nguyên fresh của tick 1
            self.assertEqual(snaps[4]["hold"], snaps[1]["hold"])
            # Từ tick 5..10 chạy thêm 6 sim_tick (sim_tick=7) -> I6 hao 6 bước = 6/120 = 0.05 -> 99.95
            self.assertAlmostEqual(snaps[10]["hold"][-1]["fresh"], 100 - 6 / 120, delta=0.01)

    def test_p3_03_quan_spoil_rereserve_and_unfulfillable(self):
        """Hao 0.25/s ở quán, nhả toàn bộ giữ chỗ đơn ươn & giữ lại 1 lần theo (order_tick, table_id), hoặc unfulfillable."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"quan": {
                "stock": [
                    {"id": "I1", "kind": "ca_loc", "fresh": 30},     # sẽ ươn ở tick 1 -> ảnh hưởng C2
                    {"id": "I2", "kind": "ca_loc", "fresh": 80},     # giữ cho C1
                    {"id": "I3", "kind": "ca_loc", "fresh": 60},     # dự phòng tươi nhất cho C2 giữ lại
                    {"id": "I4", "kind": "ca_keo", "fresh": 30},     # sẽ ươn ở tick 1 -> ảnh hưởng C3
                    {"id": "I5", "kind": "ca_keo", "fresh": 90},     # còn 1 con tươi, không đủ 2 cho ca_keo_nuong -> nhả & unfulfillable
                ],
                "customers": [
                    {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_tick": 0, "reserved": ["I2"]},
                    {"id": "C2", "table_id": "T2", "dish_id": "ca_loc_nuong_trui", "order_tick": 1, "reserved": ["I1"]},
                    {"id": "C3", "table_id": "T3", "dish_id": "ca_keo_nuong", "order_tick": 2, "reserved": ["I4", "I5"], "patience_ticks_left": 2},
                ],
                "random_customers": False,
            }})
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "3",
                                     "--scenario", sc, "--snapshot-every", "1", "--out", w.path("q.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("q.jsonl"))
            sp = events(rows, "spoiled")
            self.assertEqual([e["data"]["item_id"] for e in sp], ["I1", "I4"])
            s1 = snapshots(rows)[1]
            by_c = {c["id"]: c for c in s1["customers"]}
            self.assertEqual(by_c["C1"]["reserved"], ["I2"])
            self.assertEqual(by_c["C2"]["reserved"], ["I3"])
            self.assertEqual(by_c["C2"]["order_status"], "reserved")
            self.assertEqual(by_c["C3"]["reserved"], [])
            self.assertEqual(by_c["C3"]["order_status"], "unfulfillable")
            # Tick 2 C3 hết kiên nhẫn bỏ đi (không còn nấu được)
            left = events(rows, "customer_left")
            self.assertEqual((left[0]["tick"], left[0]["data"]["order_id"], left[0]["data"]["reason"]), (2, "C3", "patience"))

    def test_p3_04_cook_items_sorted_base_price_floor_tip_and_handoff(self):
        """cook_started sắp (kind, id_key), chốt floor(price*avg_fresh/100), boa theo giá đã chốt, bàn giao giữ ngưỡng 30."""
        with Workdir() as w:
            # 1) Bàn giao 2 tiến trình từ gather (fresh: 100 ở frame 0 cập bến) -> quan --ticks 0 & nấu giá theo tươi
            sc_g = write_json(w.path("sc_g.json"), {"gather": {
                "player": {"pos": [2, 0]},
                "hold": [
                    {"id": "I10", "kind": "ca_linh", "fresh": 100},
                    {"id": "I2", "kind": "ca_linh", "fresh": 100},
                    {"id": "I1", "kind": "bong_dien_dien", "fresh": 100},
                    {"id": "I3", "kind": "ca_linh", "fresh": 100},
                ],
                "random_fish": False,
                "monsters": [],
            }})
            inv = w.path("catch.json")
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "5",
                                     "--scenario", sc_g, "--inputs", write_json(w.path("ig.json"), frames({"tick": 0, "interact": True})),
                                     "--inventory-out", inv, "--out", w.path("g.jsonl"))
            self.assertEqual(code, 0, err)
            with open(inv, encoding="utf-8") as f:
                saved = json.load(f)
            # Xuất file sắp theo id_key: I1, I2, I3, I10
            self.assertEqual([it["id"] for it in saved["items"]], ["I1", "I2", "I3", "I10"])

            # Quan nhận --inventory --ticks 0 đọc nguyên id, kind, fresh
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "0",
                                     "--inventory", inv, "--out", w.path("q0.jsonl"))
            self.assertEqual(code, 0, err)
            self.assertEqual(snapshots(read_jsonl(w.path("q0.jsonl")))[0]["stock"],
                             events(read_jsonl(w.path("g.jsonl")), "gather_end")[0]["data"]["inventory"]["items"])

            # 2) Nấu thử món với độ tươi chính xác 50 và 40 (tb = 45): lau_ca_linh (120 -> floor(120*50/100)) hoặc ca_loc (60 * 50/100 = 30, tip = 6)
            sc_q = write_json(w.path("sc_q.json"), {"quan": {
                "player": {"pos": [2, 8]},
                "stock": [
                    {"id": "I10", "kind": "ca_linh", "fresh": 50.00416666666666},
                    {"id": "I2", "kind": "ca_linh", "fresh": 50.00416666666666},
                    {"id": "I3", "kind": "ca_linh", "fresh": 50.00416666666666},
                    {"id": "I1", "kind": "bong_dien_dien", "fresh": 50.00416666666666},
                ],
                "tables": [{"id": "T1", "pos": [2.8, 8]}],
                "customers": [{"id": "C1", "table_id": "T1", "dish_id": "lau_ca_linh_dien_dien"}],
                "random_customers": False,
            }})
            inp_q = write_json(w.path("iq.json"), frames(
                {"tick": 0, "interact": True},   # cook ở tick 1 -> avg_fresh == 50 -> base_price = 60
                {"tick": 1, "interact": False},
                {"tick": 601, "interact": True},
                {"tick": 602, "interact": False, "move": [1, 0]},
                {"tick": 620, "move": [0, 0], "interact": True},
            ))
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "650",
                                     "--scenario", sc_q, "--inputs", inp_q, "--out", w.path("q1.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("q1.jsonl"))
            cs = events(rows, "cook_started")[0]
            self.assertEqual([(it["kind"], it["id"]) for it in cs["data"]["items"]],
                             [("bong_dien_dien", "I1"), ("ca_linh", "I2"), ("ca_linh", "I3"), ("ca_linh", "I10")])
            self.assertEqual(cs["data"]["base_price"], 60)
            sv = events(rows, "served")[0]
            self.assertEqual(sv["data"]["tip"], 12)

    def test_p3_05_day_v12_ids_shop_no_decay_and_contradictions(self):
        """Day 1 giữ ID mẫu hold, Day 2+ cấp ID mới tiếp nối, Shop stock không hao tươi, lỗi reserved exit 2."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "gather": {
                    "player": {"pos": [2, 0]},
                    "hold": [{"id": "I1", "kind": "ca_loc", "fresh": 100}],
                    "time_left_ticks": 2,
                    "random_fish": False,
                    "monsters": [],
                },
                "quan": {"time_left_ticks": 3, "random_customers": False},
            })
            inp = write_json(w.path("in.json"), frames({"tick": 6, "shop_done": True}))
            code, err = run_headless("--mode", "day", "--days", "2", "--seed", "1", "--ticks", "15",
                                     "--scenario", sc, "--inputs", inp, "--snapshot-every", "1", "--out", w.path("d.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("d.jsonl"))
            snaps = snapshots(rows)
            d1_g = [s for s in snaps if s["day"] == 1 and s["phase"] == "gather"][0]
            d1_s = [s for s in snaps if s["day"] == 1 and s["phase"] == "shop"]
            d2_g = [s for s in snaps if s["day"] == 2 and s["phase"] == "gather"][0]
            self.assertEqual(d1_g["hold"][0]["id"], "I1")
            self.assertEqual(d2_g["hold"][0]["id"], "I2")  # Day 2+ cấp ID mới
            # Kho ở Shop giữ đúng schema cá thể và không bị hao tươi giữa các tick Shop
            self.assertEqual(d1_s[0]["stock"], d1_s[-1]["stock"])

            # Lỗi reserved trùng / ươn / thiếu -> exit 2 trước khi tạo file
            bad_out = w.path("bad_out.jsonl")
            for blk in (
                {"stock": [{"id": "I1", "kind": "ca_loc", "fresh": 20}],
                 "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "reserved": ["I1"]}]},
                {"stock": [{"id": "I1", "kind": "ca_loc", "fresh": 90}],
                 "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "reserved": ["I1"]},
                               {"id": "C2", "table_id": "T2", "dish_id": "ca_loc_nuong_trui", "reserved": ["I1"]}]},
            ):
                bad_sc = write_json(w.path("bad.json"), {"quan": blk})
                self.assertEqual(run_headless("--mode", "quan", "--seed", "1", "--ticks", "0",
                                              "--scenario", bad_sc, "--out", bad_out)[0], 2)


if __name__ == "__main__":
    unittest.main()
