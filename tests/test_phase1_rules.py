"""Kiểm thử hộp đen đầy đủ luật chơi Phase 1 (Test Contract v1.0, AC-P1-01 .. AC-P1-14)."""

import json
import os
import unittest

from helpers import Workdir, events, frames, read_jsonl, run_headless, snapshots, write_json


def load_contract():
    with open("game.contract.json", encoding="utf-8") as f:
        return json.load(f)


class GatherRulesP1(unittest.TestCase):
    def test_dive_surface_and_oxygen_refill(self):
        """AC-P1-02, AC-P1-03: dive/surface chỉ phát khi đổi phía surface_depth; oxy trừ dưới nước và hồi trên mặt nước."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"gather": {
                "player": {"pos": [20, 0.45], "oxygen_ticks": 100},
                "random_fish": False,
            }})
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "move": [0, 1]},   # lặn xuống vượt 0.5
                {"tick": 12, "move": [0, -1]}, # ngoi lên mặt nước
                {"tick": 25, "move": [0, 0]},
            ))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "35",
                                     "--scenario", sc, "--inputs", inp, "--snapshot-every", "1", "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            dive_ev = events(rows, "dive")
            surf_ev = events(rows, "surface")
            self.assertEqual(len(dive_ev), 1)
            self.assertEqual(len(surf_ev), 1)
            self.assertGreater(dive_ev[0]["data"]["pos"][1], 0.5)
            self.assertLessEqual(surf_ev[0]["data"]["pos"][1], 0.5)
            snaps = {s["tick"]: s for s in snapshots(rows)}
            # Sau khi ở mặt nước oxy hồi +6/tick và kẹp max (1800)
            last_p = snaps[35]["player"]
            self.assertTrue(last_p["at_surface"])
            self.assertGreater(last_p["oxygen_ticks"], snaps[dive_ev[0]["tick"]]["player"]["oxygen_ticks"])

    def test_oxygen_empty_choke_surface_save_and_faint_lifo(self):
        """AC-P1-03, AC-P1-04: oxygen_empty, ngạt đúng t+59, nổi lên cứu ở t+59, ngất bỏ LIFO & kho rỗng."""
        # 1) Chạm oxy 0 ở tick 1 (bước 0->1), ở dưới nước liên tục -> choke ở tick 60 (1 + 59)
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"gather": {
                "player": {"pos": [20, 5], "oxygen_ticks": 1, "hp": 1},
                "hold": [
                    {"id": "I1", "kind": "ca_loc", "fresh": 100},
                    {"id": "I2", "kind": "bong_sung", "fresh": 100},
                    {"id": "I3", "kind": "ca_linh", "fresh": 100},
                ],
                "random_fish": False,
            }})
            inv = w.path("inv.json")
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "100",
                                     "--scenario", sc, "--inventory-out", inv, "--snapshot-every", "1", "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            self.assertEqual([e["tick"] for e in events(rows, "oxygen_empty")], [1])
            snaps = {s["tick"]: s for s in snapshots(rows)}
            self.assertEqual(snaps[1]["player"]["zero_oxy_ticks"], 1)
            choke_ev = events(rows, "choke")
            self.assertEqual([e["tick"] for e in choke_ev], [60])
            self.assertEqual(choke_ev[0]["data"]["hp"], 0)
            faint_ev = events(rows, "faint")
            self.assertEqual(len(faint_ev), 1)
            self.assertEqual(faint_ev[0]["tick"], 60)
            self.assertEqual(faint_ev[0]["data"]["cause"], "choke")
            self.assertEqual(faint_ev[0]["data"]["hp"], 0)
            self.assertEqual([it["kind"] for it in faint_ev[0]["data"]["lost"]], ["ca_linh", "bong_sung", "ca_loc"])
            self.assertEqual([it["id"] for it in faint_ev[0]["data"]["lost"]], ["I3", "I2", "I1"])
            end_ev = events(rows, "gather_end")
            self.assertEqual(end_ev[0]["data"], {"reason": "fainted", "inventory": {"items": []}})
            with open(inv, encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"items": []})

        # 2) Nổi lên mặt nước đúng bước thứ 60 (tick 59->60): không ngạt!
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"gather": {
                "player": {"pos": [20, 0.505], "oxygen_ticks": 1, "hp": 1},
                "random_fish": False,
            }})
            # Giữ ở d=0.505 (vel=0) tới tick 59, tick 59 bơi lên -1 để vượt lên <= 0.5
            inp = write_json(w.path("in.json"), frames({"tick": 59, "move": [0, -1]}))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "65",
                                     "--scenario", sc, "--inputs", inp, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            self.assertEqual(events(rows, "choke"), [])
            self.assertEqual(events(rows, "faint"), [])
            self.assertEqual(len(events(rows, "surface")), 1)

    def test_gather_nodes_tiebreak_hold_full_and_regrow(self):
        """AC-P1-05: hái nút ở mặt nước (hòa chọn id nhỏ), dưới nước bị chặn, hold_full, node_regrown và hái ngay."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"gather": {
                "player": {"pos": [20, 0]},
                "nodes": [
                    {"id": "N2", "kind": "bong_sung", "pos": [21, 0], "regrow_ticks": 0},
                    {"id": "N1", "kind": "bong_dien_dien", "pos": [19, 0], "regrow_ticks": 0},
                    {"id": "N3", "kind": "bong_sung", "pos": [30, 0], "regrow_ticks": 2},
                ],
                "hold": [{"id": f"I{i + 1}", "kind": "ca_loc", "fresh": 100} for i in range(11)],
                "random_fish": False,
            }})
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "interact": True},   # hái N1 (hòa khoảng cách 1m với N2 -> chọn N1)
                {"tick": 1, "interact": False},
                {"tick": 2, "interact": True},   # giỏ đầy 12/12 -> hold_full cho N2
                {"tick": 3, "interact": False},
            ))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "5",
                                     "--scenario", sc, "--inputs", inp, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            g_ev = events(rows, "gather")
            self.assertEqual(len(g_ev), 1)
            self.assertEqual(g_ev[0]["data"], {"node_id": "N1", "kind": "bong_dien_dien", "amount": 1})
            hf_ev = events(rows, "hold_full")
            self.assertEqual(len(hf_ev), 1)
            self.assertEqual(hf_ev[0]["data"], {"action": "gather", "node_id": "N2", "required": 1, "free": 0})
            rg_ev = events(rows, "node_regrown")
            self.assertEqual(len(rg_ev), 1)
            self.assertEqual(rg_ev[0]["tick"], 2)
            self.assertEqual(rg_ev[0]["data"]["node_id"], "N3")

        # Nút mọc lại từ 1 về 0 trong tick k và hái ngay tại tick k; đồng thời bị chặn khi dưới nước
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"gather": {
                "player": {"pos": [30, 0]},
                "nodes": [{"id": "N3", "kind": "bong_sung", "pos": [30, 0], "regrow_ticks": 1}],
                "random_fish": False,
            }})
            inp = write_json(w.path("in.json"), frames({"tick": 0, "interact": True}))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "1",
                                     "--scenario", sc, "--inputs", inp, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            self.assertEqual([e["name"] for e in events(rows)], ["node_regrown", "gather"])

            sc2 = write_json(w.path("sc2.json"), {"gather": {
                "player": {"pos": [30, 0.6]},
                "nodes": [{"id": "N3", "kind": "bong_sung", "pos": [30, 0], "regrow_ticks": 0}],
                "random_fish": False,
            }})
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "1",
                                     "--scenario", sc2, "--inputs", inp, "--out", w.path("o2.jsonl"))
            self.assertEqual(code, 0, err)
            self.assertEqual(events(read_jsonl(w.path("o2.jsonl")), "gather"), [])

    def test_catch_fish_cooldown_hold_full_and_final_tick(self):
        """AC-P1-06, AC-P1-07: catch dưới nước, tie-break id, hồi chiêu t+30, hold_full không hồi, tick cuối."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"gather": {
                "player": {"pos": [20, 5]},
                "fish": [
                    {"id": "F10", "kind": "ca_linh", "pos": [21, 5]},
                    {"id": "F2", "kind": "ca_loc", "pos": [19, 5]},
                    {"id": "F1", "kind": "ca_linh", "pos": [21.5, 5]},
                ],
                "hold": [{"id": f"I{i + 1}", "kind": "bong_sung", "fresh": 100} for i in range(9)],  # còn 3 ô: đủ cho F2 (1 ô), rồi còn 2 ô không đủ F10 (3 ô)
            }})
            # Hồi chiêu catch = 0.5s = 30 tick: đặt ở tick 0 (t=1), dùng lại ở tick 30 (frame tick 30 -> bước 30->31)
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "catch": True},
                {"tick": 1, "catch": False},
                {"tick": 29, "catch": True},   # còn 1 tick hồi chiêu -> bỏ qua
                {"tick": 30, "catch": False},
                {"tick": 31, "catch": True},   # hết hồi chiêu -> bắt F10 (yield 3 <= free 2 -> hold_full!)
            ))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "35",
                                     "--scenario", sc, "--inputs", inp, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            fc = events(rows, "fish_caught")
            self.assertEqual(len(fc), 1)
            self.assertEqual(fc[0]["data"], {"fish_id": "F2", "kind": "ca_loc", "yield": 1})
            hf = events(rows, "hold_full")
            self.assertEqual(len(hf), 1)
            self.assertEqual(hf[0]["data"], {"action": "catch", "fish_id": "F10", "required": 3, "free": 2})
            last = snapshots(rows)[-1]
            self.assertEqual(last["player"]["catch_cd_ticks"], 0)
            self.assertEqual(len(last["fish"]), 2)  # F10 vẫn còn nguyên

        # Tick cuối: interact tại bến cho reason='docked' (ưu tiên hơn 'time' và hơn hái nút)
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"gather": {
                "player": {"pos": [5, 0]},  # đúng mép dock_radius=3 từ [2,0]
                "nodes": [{"id": "N1", "kind": "bong_sung", "pos": [5, 0]}],
                "hold": [{"id": "I1", "kind": "ca_loc", "fresh": 100}],
                "time_left_ticks": 1,
                "random_fish": False,
            }})
            inp = write_json(w.path("in.json"), frames({"tick": 0, "interact": True}))
            inv = w.path("inv.json")
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "5",
                                     "--scenario", sc, "--inputs", inp, "--inventory-out", inv, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            self.assertEqual(events(rows, "gather"), [])
            self.assertEqual(events(rows, "gather_end")[0]["data"]["reason"], "docked")
            self.assertEqual(rows[-1]["reason"], "docked")
            with open(inv, encoding="utf-8") as f:
                data = json.load(f)
                self.assertEqual(len(data["items"]), 1)
                self.assertEqual(data["items"][0]["id"], "I1")
                self.assertEqual(data["items"][0]["kind"], "ca_loc")
                self.assertAlmostEqual(data["items"][0]["fresh"], 100 - 1 / 120, delta=0.01)


class QuanRulesP1(unittest.TestCase):
    @staticmethod
    def _items(*kinds, fresh=100):
        return [{"id": f"I{i + 1}", "kind": k, "fresh": fresh} for i, k in enumerate(kinds)]

    def test_customer_schedule_reservation_and_no_dish(self):
        """AC-P1-08: lịch khách (tick 120, mỗi 900 tick), chọn món nấu được, giữ chỗ, no_dish."""
        with Workdir() as w:
            # Kho chỉ đủ nấu đúng 1 cá lóc nướng trui
            sc = write_json(w.path("sc.json"), {"quan": {"stock": self._items("ca_loc")}})
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "1050",
                                     "--scenario", sc, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            arr = events(rows, "customer_arrived")
            self.assertEqual(len(arr), 1)
            self.assertEqual(arr[0]["tick"], 120)
            self.assertEqual(arr[0]["data"], {"order_id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"})
            # Ở v1.0 có 1 bàn T1 (không phát no_dish lúc 1020); từ v1.1 có 4 bàn T1..T4 nên T2 trống phát no_dish ở tick 1020
            expected_no_dish = [] if len(load_contract()["tuning"]["quan"]["tables"]) == 1 else [1020]
            self.assertEqual([e["tick"] for e in events(rows, "no_dish")], expected_no_dish)

        # Bàn trống nhưng kho không đủ bất kỳ món nào -> no_dish đúng tick 120
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"quan": {"stock": self._items("bong_sung")}})
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "125",
                                     "--scenario", sc, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            nd = events(read_jsonl(w.path("o.jsonl")), "no_dish")
            self.assertEqual([e["tick"] for e in nd], [120])

    def test_interact_priority_and_non_interactable_cancels_turn(self):
        """AC-P1-09: hòa khoảng cách chọn bếp trước bàn; đối tượng gần nhất không tương tác được thì bỏ lượt."""
        # Bếp [2,8] và bàn [4,8] khi người chơi ở [3,8]: khoảng cách đều 1.0 -> chọn bếp B1
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"quan": {
                "player": {"pos": [3, 8]},
                "stock": self._items("ca_loc"),
                "tables": [{"id": "T1", "pos": [4, 8]}],
                "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"}],
                "random_customers": False,
            }})
            inp = write_json(w.path("in.json"), frames({"tick": 0, "interact": True}))
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "2",
                                     "--scenario", sc, "--inputs", inp, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            self.assertEqual(len(events(rows, "cook_started")), 1)
            self.assertEqual(events(rows, "cook_started")[0]["data"]["stove_id"], "B1")

        # Bếp đang idle nhưng hand đang bận: chọn bếp (gần hơn) -> bỏ lượt không giao bàn
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"quan": {
                "player": {"pos": [2.2, 8]},
                "tables": [{"id": "T1", "pos": [3.0, 8]}],
                "stoves": [{"id": "B1", "state": "idle"}],
                "hand": {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 60},
                "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_status": "assigned"}],
                "random_customers": False,
            }})
            inp = write_json(w.path("in.json"), frames({"tick": 0, "interact": True}))
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "1",
                                     "--scenario", sc, "--inputs", inp, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            self.assertEqual(events(rows, "cook_started"), [])
            self.assertEqual(events(rows, "served"), [])

    def test_full_cook_serve_tip_boundary_and_reputation_precision(self):
        """AC-P1-10, AC-P1-11: nấu -> ready (ready_ticks=0) -> nhấc -> phục vụ đúng ngưỡng boa 50%, uy tín & điểm."""
        # 1) Nấu Lẩu cá linh (120k niêm yết, cook 600t), đầu tick 1 hao 1/240 -> base_price=119, boa=floor(119*0.2)=23, uy tín 3.2, điểm 142+300=442
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"quan": {
                "player": {"pos": [2, 8]},
                "stock": self._items("ca_linh", "ca_linh", "ca_linh", "bong_dien_dien"),
                "tables": [{"id": "T1", "pos": [3.2, 8]}],
                "customers": [{"id": "C1", "table_id": "T1", "dish_id": "lau_ca_linh_dien_dien", "patience_ticks_left": 2430}],
                "random_customers": False,
            }})
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "interact": True},    # bắt đầu nấu ở tick 1 -> chín ở tick 601
                {"tick": 1, "interact": False},
                {"tick": 601, "interact": True},  # nhấc món ở tick 602
                {"tick": 602, "interact": False, "move": [1, 0]},
                {"tick": 625, "move": [0, 0], "interact": True},
            ))
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "1300",
                                     "--scenario", sc, "--inputs", inp, "--snapshot-every", "1", "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            cs = events(rows, "cook_started")[0]
            self.assertEqual([it["kind"] for it in cs["data"]["items"]], ["bong_dien_dien", "ca_linh", "ca_linh", "ca_linh"])
            self.assertEqual(cs["data"]["base_price"], 119)
            dr = events(rows, "dish_ready")[0]
            self.assertEqual(dr["tick"], 601)
            snaps = {s["tick"]: s for s in snapshots(rows)}
            self.assertEqual(snaps[601]["stoves"][0]["ready_ticks"], 0)
            dp = events(rows, "dish_picked")[0]
            self.assertEqual(dp["tick"], 602)
            sv = events(rows, "served")[0]
            self.assertEqual(sv["data"]["tip"], 23)
            self.assertGreaterEqual(sv["data"]["patience_ticks_left"], 1800)
            pd = events(rows, "paid")[0]
            self.assertEqual(pd["data"], {"order_id": "C1", "table_id": "T1", "base_price": 119, "tip": 23, "amount": 142, "reason": "finished_eating"})
            self.assertEqual(rows[-1]["score"], 142 + 300)

        # 2) Ngưỡng boa chính xác: còn đúng 1800 sau bước 1 (>= 50%) có boa; 1799 (< 50%) boa = 0; phục vụ ở tick patience==0 vẫn hợp lệ
        for pat_init, want_tip in ((1801, 12), (1800, 0), (1, 0)):
            with Workdir() as w:
                sc = write_json(w.path("sc.json"), {"quan": {
                    "player": {"pos": [9, 2]},
                    "hand": {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 60},
                    "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                                   "order_status": "assigned", "patience_ticks_left": pat_init}],
                    "random_customers": False,
                }})
                inp = write_json(w.path("in.json"), frames({"tick": 0, "interact": True}))
                code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "2",
                                         "--scenario", sc, "--inputs", inp, "--out", w.path("o.jsonl"))
                self.assertEqual(code, 0, err)
                rows = read_jsonl(w.path("o.jsonl"))
                sv = events(rows, "served")
                self.assertEqual(len(sv), 1, (pat_init, rows))
                self.assertEqual(sv[0]["data"]["tip"], want_tip, pat_init)
                self.assertEqual(events(rows, "customer_left"), [])

        # 3) Tránh sai số float nhị phân ở uy tín khi chạm mốc nguyên (3.8 + 0.2 = 4.0 -> floor = 4)
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"quan": {
                "reputation": 3.8,
                "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                               "state": "eating", "eat_ticks_left": 1, "base_price": 60, "tip": 12}],
                "random_customers": False,
            }})
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "1",
                                     "--scenario", sc, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            self.assertEqual(rows[-1]["reputation"], 4.0)
            self.assertEqual(rows[-1]["score"], 72 + 400)

    def test_patience_cleanup_and_closing_settlement(self):
        """AC-P1-12: khách bỏ đi hết kiên nhẫn (trừ uy tín, dọn bếp/tay); đóng ca trả ngay khách eating và closing không trừ uy tín."""
        # Hết kiên nhẫn trong lúc bếp đang nấu -> trừ 0.5 uy tín, bếp về idle, không hoàn nguyên liệu
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"quan": {
                "stock": self._items("ca_loc"),
                "stoves": [{"id": "B1", "state": "cooking", "dish": {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 60}, "cook_ticks_left": 200}],
                "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                               "order_status": "assigned", "patience_ticks_left": 1}],
                "random_customers": False,
            }})
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "2",
                                     "--scenario", sc, "--snapshot-every", "1", "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            left = events(rows, "customer_left")[0]
            self.assertEqual(left["tick"], 1)
            self.assertEqual(left["data"], {"order_id": "C1", "table_id": "T1", "reason": "patience", "reputation": 2.5})
            s1 = snapshots(rows)[1]
            self.assertEqual(s1["stoves"][0]["state"], "idle")
            self.assertIsNone(s1["stoves"][0]["dish"])
            self.assertEqual([(it["id"], it["kind"]) for it in s1["stock"]], [("I1", "ca_loc")])

        # Đóng ca ngay tick vừa giao món -> trả ngay reason='closing'; hoặc waiting ở tick cuối -> reason='closing' không trừ uy tín
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"quan": {
                "player": {"pos": [9, 2]},
                "hand": {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 60},
                "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_status": "assigned"}],
                "time_left_ticks": 1,
                "random_customers": False,
            }})
            inp = write_json(w.path("in.json"), frames({"tick": 0, "interact": True}))
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "5",
                                     "--scenario", sc, "--inputs", inp, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            self.assertEqual([e["name"] for e in events(rows)], ["served", "paid", "quan_end"])
            self.assertEqual(events(rows, "paid")[0]["data"]["reason"], "closing")
            self.assertEqual(rows[-1]["earned"], 72)

        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"quan": {
                "stock": self._items("ca_loc"),
                "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"}],
                "time_left_ticks": 1,
                "random_customers": False,
            }})
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "5",
                                     "--scenario", sc, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            left = events(rows, "customer_left")[0]
            self.assertEqual(left["data"]["reason"], "closing")
            self.assertEqual(left["data"]["reputation"], 3.0)

    def test_scenario_contradictions_exit_2_without_output(self):
        """AC-P1-13: mọi mâu thuẫn scenario quán trả mã 2 trước khi tạo file out."""
        bad_blocks = [
            {"stock": [], "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"}]},  # giữ quá kho
            {"stock": self._items("ca_loc"), "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "reserved": ["I99"]}]},  # giữ id không có
            {"stock": self._items("ca_loc", "bong_sung"), "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "reserved": ["I2"]}]},  # sai nguyên liệu
            {"customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_status": "assigned"}]},  # thiếu món
            {"hand": {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 60},
             "stoves": [{"id": "B1", "state": "ready", "dish": {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 60}}],
             "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_status": "assigned"}]},  # trùng đơn bếp+tay
            {"hand": {"order_id": "C1", "dish_id": "goi_bong_sung", "base_price": 40},
             "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_status": "assigned"}]},  # sai món
            {"customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "state": "eating", "eat_ticks_left": 10}]},  # thiếu base_price/tip
            {"customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "state": "waiting", "order_status": "served"}]},
        ]
        with Workdir() as w:
            out = w.path("out.jsonl")
            for idx, blk in enumerate(bad_blocks):
                sc = write_json(w.path(f"b{idx}.json"), {"quan": blk})
                code, _ = run_headless("--mode", "quan", "--seed", "1", "--ticks", "0", "--scenario", sc, "--out", out)
                self.assertEqual(code, 2, (idx, blk))
                self.assertFalse(os.path.exists(out))

    def test_end_to_end_gather_to_quan_and_contract_meta(self):
        """AC-P1-01, AC-P1-14: 2 tiến trình từ hái/bắt cá -> cập bến -> quán phục vụ -> trả tiền, tất định từng byte."""
        c = load_contract()
        self.assertIn(c["contract_version"], ("1.0", "1.1", "1.2", "1.3"))
        self.assertEqual(c["team"], "Giang")
        self.assertEqual(c["team_size"], 1)

        with Workdir() as w:
            # Đi tới N1 [12,0] hái rồi quay lại bến [2,0] cập bến
            sc_g = write_json(w.path("sc_g.json"), {"gather": {
                "player": {"pos": [12, 0]},
                "hold": [{"id": "I1", "kind": "ca_loc", "fresh": 100}],
                "fish": [{"id": "F1", "kind": "ca_loc", "pos": [12, 2]}],
                "random_fish": False,
            }})
            inp_g = write_json(w.path("in_g.json"), frames(
                {"tick": 0, "interact": True},     # hái N1 (bong_dien_dien) -> I2
                {"tick": 1, "interact": False, "move": [-1, 0]},
                {"tick": 160, "move": [0, 0], "interact": True},  # tới bến (<5m) và cập bến
            ))
            inv = w.path("catch.json")
            code, err = run_headless("--mode", "gather", "--seed", "11", "--ticks", "300",
                                     "--scenario", sc_g, "--inputs", inp_g, "--inventory-out", inv, "--out", w.path("g1.jsonl"))
            self.assertEqual(code, 0, err)
            code, err = run_headless("--mode", "gather", "--seed", "11", "--ticks", "300",
                                     "--scenario", sc_g, "--inputs", inp_g, "--out", w.path("g2.jsonl"))
            self.assertEqual(code, 0, err)
            with open(w.path("g1.jsonl"), "rb") as a, open(w.path("g2.jsonl"), "rb") as b:
                self.assertEqual(a.read(), b.read())
            with open(inv, encoding="utf-8") as f:
                inv_obj = json.load(f)
            self.assertEqual([(it["id"], it["kind"]) for it in inv_obj["items"]],
                             [("I1", "ca_loc"), ("I2", "bong_dien_dien")])

            # Mở quán từ file kho trên: khách gọi món nấu được (tick 120) -> đi tới B1 [2,8] -> nấu -> nhấc -> tới T1 [9,2] -> phục vụ -> trả tiền
            inp_q = write_json(w.path("in_q.json"), frames(
                {"tick": 120, "move": [-1, 0]},                   # [8,5] -> ~[2.2, 5]
                {"tick": 210, "move": [0, 1]},                    # ~[2.2, 5] -> ~[2.2, 7.8]
                {"tick": 255, "move": [0, 0], "interact": True},  # nấu (tối đa 480t cho canh chua / 360t cho cá lóc)
                {"tick": 256, "interact": False},
                {"tick": 745, "interact": True},                  # nhấc món ở tick 746
                {"tick": 746, "interact": False, "move": [1, 0]}, # ~[2.2, 7.8] -> ~[8.8, 7.8]
                {"tick": 850, "move": [0, -1]},                   # ~[8.8, 7.8] -> ~[8.8, 2.2]
                {"tick": 940, "move": [0, 0], "interact": True},  # giao món ở tick 941 (ăn 600t -> trả ở tick 1541)
            ))
            code, err = run_headless("--mode", "quan", "--seed", "11", "--ticks", "1700",
                                     "--inventory", inv, "--inputs", inp_q, "--out", w.path("q1.jsonl"))
            self.assertEqual(code, 0, err)
            q_rows = read_jsonl(w.path("q1.jsonl"))
            arr = events(q_rows, "customer_arrived")[0]
            dish_id = arr["data"]["dish_id"]
            price = c["tuning"]["menu"][dish_id]["price"]
            cs = events(q_rows, "cook_started")[0]
            base_price = cs["data"]["base_price"]
            self.assertLess(base_price, price)
            self.assertGreaterEqual(base_price, int(price * 0.96))
            tip = base_price // 5
            paid = events(q_rows, "paid")
            self.assertEqual(len(paid), 1)
            self.assertEqual(paid[0]["data"]["base_price"], base_price)
            self.assertEqual(paid[0]["data"]["tip"], tip)
            self.assertEqual(q_rows[-1]["earned"], base_price + tip)


if __name__ == "__main__":
    unittest.main()
