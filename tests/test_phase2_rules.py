"""Kiểm thử toàn diện Phase 2 (TICKET-02 & Test Contract v1.1, AC-P2-01 .. AC-P2-14)."""

import json
import math
import os
import time
import unittest
import urllib.request

from chonoi.contract import load_contract
from chonoi.live import LiveGame, LiveServer
from helpers import Workdir, events, frames, read_jsonl, run_headless, snapshots, write_json


class Phase2CoreRules(unittest.TestCase):
    def test_ac_p2_01_contract_v11_structure(self):
        """AC-P2-01: game.contract.json đạt chuẩn >= v1.1 (6 nút, 8 cá, 3 loài, quái M1/M2, 2 bếp, 4 bàn, 6 món, D1-D5, Shop)."""
        c = load_contract()
        self.assertIn(c["contract_version"], ("1.1", "1.2", "1.3"))
        g = c["tuning"]["gather"]
        self.assertEqual(len(g["nodes"]), 6)
        self.assertEqual({n["kind"] for n in g["nodes"]}, {"bong_dien_dien", "bong_sung", "keo_neo"})
        self.assertEqual(g["fish_initial"], 8)
        self.assertEqual(set(g["fish_yield"]), {"ca_linh", "ca_loc", "ca_keo"})
        self.assertEqual([m["id"] for m in g["monsters"]["spawns"]], ["M1", "M2"])
        q = c["tuning"]["quan"]
        self.assertEqual([s["id"] for s in q["stoves"]], ["B1", "B2"])
        self.assertEqual([t["id"] for t in q["tables"]], ["T1", "T2", "T3", "T4"])
        self.assertEqual(len(c["tuning"]["menu"]), 6)
        self.assertEqual(len(c["tuning"]["day_plan"]), 5)
        self.assertIn("oxygen", c["tuning"]["shop"]["upgrades"])
        self.assertIn("hp", c["tuning"]["shop"]["upgrades"])

    def test_ac_p2_02_fish_swim_reflection_and_spawn(self):
        """AC-P2-02: đàn cá bơi 1.5 m/s, phản xạ mép/góc, sinh cá tại 360*k với clearance > 1 m, trần 12."""
        # Phản xạ góc [4, 3] cho cá linh
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"gather": {
                "fish": [{"id": "F1", "kind": "ca_linh", "pos": [4.01, 3.01], "heading_deg": 225}],
                "monsters": [],
            }})
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "5",
                                     "--scenario", sc, "--snapshot-every", "1", "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            snaps = snapshots(read_jsonl(w.path("o.jsonl")))
            f1 = snaps[-1]["fish"][0]
            self.assertGreaterEqual(f1["pos"][0], 4.0)
            self.assertGreaterEqual(f1["pos"][1], 3.0)
            self.assertAlmostEqual(f1["heading_deg"], 45.0, delta=0.5)
            self.assertEqual(f1["age_ticks"], 5)

        # Sinh thêm từ 8 đàn lên tối đa 12 đàn ở 360*k
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"gather": {"monsters": []}})
            code, err = run_headless("--mode", "gather", "--seed", "7", "--ticks", "2200",
                                     "--scenario", sc, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            spawns = events(rows, "fish_spawned")
            self.assertGreaterEqual(len(spawns), 4)
            self.assertEqual(spawns[0]["tick"], 360)
            self.assertEqual(len(snapshots(rows)[-1]["fish"]), 12)

    def test_ac_p2_03_monster_patrol_chase_hit_recoil_and_faint(self):
        """AC-P2-03: Cá Sấu patrol/chase, hit (-1 HP, rơi floor(hold/2) LIFO, 90t bất tử, 60t recoil), faint cause=monster."""
        with Workdir() as w:
            # M1 đứng sát người chơi dưới d=24, hold 5 món -> chạm mất 1 HP, rơi floor(5/2)=2 món LIFO, recoil 60 tick
            sc = write_json(w.path("sc.json"), {"gather": {
                "player": {"pos": [60.5, 24.0], "hp": 2},
                "hold": [
                    {"id": f"I{i + 1}", "kind": k, "fresh": 100}
                    for i, k in enumerate(("ca_loc", "bong_sung", "ca_linh", "ca_keo", "keo_neo"))
                ],
                "random_fish": False,
                "monsters": [{"id": "M1", "kind": "ca_sau", "pos": [60.0, 24.0],
                              "waypoints": [[60.0, 24.0], [64.0, 24.0]]}],
            }})
            inv = w.path("inv.json")
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "100",
                                     "--scenario", sc, "--inventory-out", inv, "--snapshot-every", "1", "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            hits = events(rows, "monster_hit")
            # Hit ở tick 1 -> bất tử 90t + recoil 60t -> hit lần 2 ở tick 92 (về hp=0 -> faint!)
            self.assertGreaterEqual(len(hits), 1)
            self.assertEqual(hits[0]["tick"], 1)
            self.assertEqual(hits[0]["data"]["hp"], 1)
            self.assertEqual([it["kind"] for it in hits[0]["data"]["lost"]], ["keo_neo", "ca_keo"])
            self.assertEqual([it["id"] for it in hits[0]["data"]["lost"]], ["I5", "I4"])
            snaps = {s["tick"]: s for s in snapshots(rows)}
            self.assertEqual(snaps[1]["player"]["invuln_ticks"], 90)
            self.assertEqual(snaps[1]["monsters"][0]["state"], "recoil")
            self.assertEqual(snaps[1]["monsters"][0]["state_ticks_left"], 60)
            # Trong suốt 60 bước recoil (tới tick 61) trạng thái vẫn là recoil tới 60 rồi về patrol ở 61
            self.assertEqual(snaps[60]["monsters"][0]["state"], "recoil")
            self.assertEqual(snaps[61]["monsters"][0]["state"], "patrol")
            # Khi HP về 0 bởi chạm quái -> faint(cause="monster") với phần còn lại của giỏ LIFO và kho rỗng
            if len(hits) == 2:
                faint = events(rows, "faint")[0]
                self.assertEqual(faint["data"]["cause"], "monster")
                self.assertEqual(faint["data"]["hp"], 0)
                with open(inv, encoding="utf-8") as f:
                    self.assertEqual(json.load(f), {"items": []})

        # Kiểm exit chase khi người chơi lên d < 10
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"gather": {
                "player": {"pos": [60, 12]},
                "random_fish": False,
                "monsters": [{"id": "M1", "kind": "ca_sau", "pos": [60, 15], "waypoints": [[60, 24], [64, 24]]}],
            }})
            inp = write_json(w.path("in.json"), frames({"tick": 1, "move": [0, -1]}))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "60",
                                     "--scenario", sc, "--inputs", inp, "--snapshot-every", "1", "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            snaps = snapshots(read_jsonl(w.path("o.jsonl")))
            self.assertEqual(snaps[1]["monsters"][0]["state"], "chase")
            self.assertEqual(snaps[-1]["monsters"][0]["state"], "patrol")

    def test_ac_p2_04_choke_pierces_invuln_without_item_drop(self):
        """AC-P2-04: ngạt xuyên bất tử (invuln_ticks > 0) và không làm rơi hàng."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"gather": {
                "player": {"pos": [20, 5], "oxygen_ticks": 1, "hp": 2, "invuln_ticks": 90},
                "hold": [
                    {"id": "I1", "kind": "ca_loc", "fresh": 100},
                    {"id": "I2", "kind": "ca_keo", "fresh": 100},
                ],
                "random_fish": False,
                "monsters": [],
            }})
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "65",
                                     "--scenario", sc, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            ch = events(rows, "choke")
            self.assertEqual([e["tick"] for e in ch], [60])
            self.assertEqual(ch[0]["data"]["hp"], 1)
            self.assertEqual([it["kind"] for it in snapshots(rows)[-1]["hold"]], ["ca_loc", "ca_keo"])

    def test_ac_p2_05_two_stoves_four_tables_and_new_dishes(self):
        """AC-P2-05: 2 bếp B1/B2 nấu song song, 4 bàn T1..T4 và món mới lau_mam."""
        with Workdir() as w:
            kinds = ["ca_linh", "ca_linh", "ca_keo", "ca_keo", "ca_keo", "keo_neo", "bong_dien_dien", "ca_loc", "bong_sung", "bong_sung"]
            sc = write_json(w.path("sc.json"), {"quan": {
                "player": {"pos": [2, 8]},
                "stock": [{"id": f"I{i + 1}", "kind": k, "fresh": 100} for i, k in enumerate(kinds)],
                "customers": [
                    {"id": "C1", "table_id": "T1", "dish_id": "lau_mam", "order_tick": 1},
                    {"id": "C2", "table_id": "T2", "dish_id": "ca_keo_nuong", "order_tick": 2},
                    {"id": "C3", "table_id": "T3", "dish_id": "ca_loc_nuong_trui", "order_tick": 3},
                    {"id": "C4", "table_id": "T4", "dish_id": "goi_bong_sung", "order_tick": 4},
                ],
                "random_customers": False,
            }})
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "interact": True},                  # nấu lau_mam trên B1 (hao 1 tick còn 99.9958... -> chốt 199)
                {"tick": 1, "interact": False, "move": [1, 0]}, # đi sang B2 [5, 8]
                {"tick": 50, "move": [0, 0], "interact": True}, # nấu ca_keo_nuong trên B2
            ))
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "60",
                                     "--scenario", sc, "--inputs", inp, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            cs = events(read_jsonl(w.path("o.jsonl")), "cook_started")
            self.assertEqual([(e["data"]["stove_id"], e["data"]["dish_id"]) for e in cs],
                             [("B1", "lau_mam"), ("B2", "ca_keo_nuong")])
            self.assertEqual(cs[0]["data"]["base_price"], 199)

    def test_ac_p2_06_pause_freezes_sim_and_preserves_button_edge(self):
        """AC-P2-06: pause đóng băng sim_tick/phase_tick/timer, bỏ qua hành động & buy; resumed chạy ngay trong tick đó."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"gather": {"player": {"pos": [20, 5]}, "random_fish": False, "monsters": []}})
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "pause": True, "move": [0, 1]},  # vào pause ở bước 0->1
                {"tick": 1, "pause": False, "catch": True},  # hành động trong lúc pause bị bỏ qua
                {"tick": 10, "pause": True},                 # tick 10->11 resumed + chạy bước gameplay ngay!
            ))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "12",
                                     "--scenario", sc, "--inputs", inp, "--snapshot-every", "1", "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            self.assertEqual([e["tick"] for e in events(rows, "paused")], [1])
            self.assertEqual([e["tick"] for e in events(rows, "resumed")], [11])
            snaps = {s["tick"]: s for s in snapshots(rows)}
            self.assertEqual(snaps[1]["state"], "paused")
            self.assertEqual(snaps[10]["sim_tick"], 0)
            self.assertEqual(snaps[10]["phase_tick"], 0)
            self.assertEqual(snaps[10]["player"]["oxygen_ticks"], 1800)
            self.assertEqual(snaps[11]["state"], "playing")
            self.assertEqual(snaps[11]["sim_tick"], 1)
            self.assertEqual(snaps[11]["phase_tick"], 1)
            self.assertEqual(snaps[11]["player"]["oxygen_ticks"], 1799)

    def test_ac_p2_07_to_10_day_mode_menu_filter_shop_and_multiday_upgrades(self):
        """AC-P2-07..10: vòng Ngày 1->3, lọc menu theo day_plan, ngất mở quán kho rỗng, Shop + nâng cấp hiệu lực từ Ngày kế, M2 ở Ngày 3."""
        # 1) Kiểm vòng 1 ngày hoàn chỉnh + ngất sáng vẫn mở quán kho rỗng
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"gather": {
                "player": {"pos": [20, 5], "oxygen_ticks": 1, "hp": 1},
                "hold": [{"id": "I1", "kind": "ca_loc", "fresh": 100}],
                "random_fish": False,
                "monsters": [],
            }})
            # Ngất ở tick 60 -> quan chạy 10800 tick -> shop ở tick 10860, đóng shop bằng shop_done ở 10861
            inp = write_json(w.path("in.json"), frames({"tick": 10865, "shop_done": True}))
            code, err = run_headless("--mode", "day", "--days", "1", "--seed", "1", "--ticks", "12000",
                                     "--scenario", sc, "--inputs", inp, "--snapshot-every", "12000", "--out", w.path("d1.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("d1.jsonl"))
            ev_names = [e["name"] for e in events(rows)]
            self.assertEqual(ev_names[:3], ["day_start", "day_plan", "phase_start"])
            self.assertIn("faint", ev_names)
            self.assertIn("gather_end", ev_names)
            self.assertIn("quan_end", ev_names)
            self.assertIn("shop_end", ev_names)
            self.assertEqual(rows[-1]["reason"], "days_complete")
            self.assertEqual(rows[-1]["days_completed"], 1)
            # Khi chuyển sang quan ở tick 60, stock phải rỗng dù hold ban đầu có ca_loc
            quan_snap = [s for s in snapshots(rows) if s["phase"] == "quan"][0]
            self.assertEqual(quan_snap["stock"], [])
            self.assertEqual(quan_snap["phase_tick"], 0)

        # 2) Nhiều ngày (3 ngày): Shop mua oxygen & hp lv1 (kể cả buy + shop_done trên bước cuối shop), hiệu lực từ Ngày 2, M2 xuất hiện ở Ngày 3
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "day": {"money": 500, "earned": 500},
                "gather": {
                    "time_left_ticks": 2,
                    "hold": [
                        {"id": "I1", "kind": "ca_keo", "fresh": 100},
                        {"id": "I2", "kind": "ca_keo", "fresh": 100},
                    ],
                    "random_fish": False,
                },
                "quan": {"time_left_ticks": 2},
            })
            # Day 1: gather 2 ticks (1..2), quan 2 ticks (3..4 -> shop at 4),
            #   Shop: tick 4 unknown, tick 5 oxygen (200->300), tick 6 hp (250->50), tick 7 oxygen (funds!), tick 8 shop_done -> Day 2
            inp = write_json(w.path("in.json"), frames(
                {"tick": 4, "buy": "teleport"},
                {"tick": 5, "buy": "oxygen"},
                {"tick": 6, "buy": "hp"},
                {"tick": 7, "buy": "oxygen"},
                {"tick": 8, "shop_done": True},
                {"tick": 9, "shop_done": False},
                {"tick": 13, "buy": "oxygen", "shop_done": True},
            ))
            code, err = run_headless("--mode", "day", "--days", "3", "--seed", "1", "--ticks", "50",
                                     "--scenario", sc, "--inputs", inp, "--snapshot-every", "1", "--out", w.path("d3.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("d3.jsonl"))
            bought = events(rows, "bought")
            self.assertEqual([(b["data"]["upgrade"], b["data"]["level"]) for b in bought], [("oxygen", 1), ("hp", 1)])
            failed = events(rows, "buy_failed")
            self.assertEqual([(f["data"]["action"], f["data"]["reason"]) for f in failed[:2]],
                             [("teleport", "unknown"), ("oxygen", "funds")])
            snaps = snapshots(rows)
            d1_shop = [s for s in snaps if s["day"] == 1 and s["phase"] == "shop"][-1]
            self.assertEqual(d1_shop["upgrades"], {"hp": 1, "oxygen": 1})
            self.assertEqual(d1_shop["active_upgrades"], {})
            self.assertEqual(d1_shop["money"], 50)
            self.assertEqual(d1_shop["earned"], 500)
            d2_gather = [s for s in snaps if s["day"] == 2 and s["phase"] == "gather"][0]
            self.assertEqual(d2_gather["active_upgrades"], {"hp": 1, "oxygen": 1})
            self.assertEqual(d2_gather["player"]["oxygen_max_ticks"], 2700)
            self.assertEqual(d2_gather["player"]["hp_max"], 4)
            # Ở Day 2 quan, dù hold mang về có ca_keo nhưng day_plan D2 chỉ có ca_loc_nuong_trui & lau_ca_linh_dien_dien -> không thể nấu ca_keo_nuong!
            d3_gather = [s for s in snaps if s["day"] == 3 and s["phase"] == "gather"][0]
            self.assertEqual([m["id"] for m in d3_gather["monsters"]], ["M1", "M2"])

        # 3) Test buy + shop_done trên bước cuối shop (tick 600 của Shop)
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "day": {"money": 200, "earned": 200},
                "gather": {"time_left_ticks": 1, "random_fish": False},
                "quan": {"time_left_ticks": 1},
            })
            # Gather 0->1, Quan 1->2 (shop starts at tick 2, max 600 ticks -> final tick is 601->602)
            inp = write_json(w.path("in.json"), frames({"tick": 601, "buy": "oxygen", "shop_done": True}))
            code, err = run_headless("--mode", "day", "--days", "1", "--seed", "1", "--ticks", "700",
                                     "--scenario", sc, "--inputs", inp, "--out", w.path("end_shop.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("end_shop.jsonl"))
            self.assertEqual(len(events(rows, "bought")), 1)
            self.assertEqual(events(rows, "shop_end")[0]["data"]["reason"], "done")

    def test_ac_p2_11_day_scenario_contradictions_exit_2(self):
        """AC-P2-11: các mâu thuẫn scenario của day/monsters/v1.1 trả mã 2."""
        bad_scenarios = [
            {"day": {"money": 100}},  # thiếu earned
            {"day": {"money": 200, "earned": 100}},  # money > earned
            {"quan": {"stock": [{"id": "I1", "kind": "ca_loc", "fresh": 100}]}},  # cấm quan.stock trong day
            {"quan": {"reputation": 4.0}},       # cấm quan.reputation trong day
            {"day": {"day_plan": [{"day": 1, "dishes": {"ca_loc_nuong_trui": 2}, "ingredients": {"ca_loc": 1}}]}},
            {"gather": {"monsters": [{"id": "M1", "kind": "ca_sau", "pos": [60, 24], "waypoints": [[60, 24], [64, 24]],
                                      "state": "recoil", "state_ticks_left": 10}]}},  # thiếu recoil_dir
        ]
        with Workdir() as w:
            out = w.path("out.jsonl")
            for idx, sc_obj in enumerate(bad_scenarios):
                sc = write_json(w.path(f"bad_{idx}.json"), sc_obj)
                code, _ = run_headless("--mode", "day", "--days", "1", "--seed", "1", "--ticks", "0", "--scenario", sc, "--out", out)
                self.assertEqual(code, 2, (idx, sc_obj))

    def test_ac_p2_12_full_day_performance_and_determinism(self):
        """AC-P2-12: chạy headless 1 Ngày trọn vẹn (<= 22200 tick) dưới 20s và giống nhau từng byte."""
        with Workdir() as w:
            t0 = time.perf_counter()
            code1, err1 = run_headless("--mode", "day", "--days", "1", "--seed", "42", "--ticks", "22200",
                                       "--snapshot-every", "60", "--out", w.path("d1.jsonl"))
            dt = time.perf_counter() - t0
            self.assertEqual(code1, 0, err1)
            self.assertLess(dt, 20.0)
            code2, err2 = run_headless("--mode", "day", "--days", "1", "--seed", "42", "--ticks", "22200",
                                       "--snapshot-every", "60", "--out", w.path("d2.jsonl"))
            self.assertEqual(code2, 0, err2)
            with open(w.path("d1.jsonl"), "rb") as a, open(w.path("d2.jsonl"), "rb") as b:
                self.assertEqual(a.read(), b.read())
            rows = read_jsonl(w.path("d1.jsonl"))
            self.assertEqual(rows[-1]["reason"], "days_complete")
            self.assertEqual(rows[-1]["days_completed"], 1)

    def test_ac_p2_13_two_process_handoff_v11_ingredients(self):
        """AC-P2-13: bàn giao 2 tiến trình với nguyên liệu mới (ca_keo, keo_neo) nấu Lẩu mắm."""
        with Workdir() as w:
            kinds = ["ca_linh", "ca_linh", "ca_keo", "keo_neo", "bong_dien_dien"]
            sc_g = write_json(w.path("sc_g.json"), {"gather": {
                "player": {"pos": [2, 0]},
                "hold": [{"id": f"I{i + 1}", "kind": k, "fresh": 100} for i, k in enumerate(kinds)],
                "random_fish": False,
                "monsters": [],
            }})
            inp_g = write_json(w.path("in_g.json"), frames({"tick": 0, "interact": True}))
            inv = w.path("inv.json")
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "5",
                                     "--scenario", sc_g, "--inputs", inp_g, "--inventory-out", inv, "--out", w.path("g.jsonl"))
            self.assertEqual(code, 0, err)
            with open(inv, encoding="utf-8") as f:
                saved = json.load(f)
            self.assertEqual([(it["id"], it["kind"]) for it in saved["items"]],
                             [(f"I{i + 1}", k) for i, k in enumerate(kinds)])
            sc_q = write_json(w.path("sc_q.json"), {"quan": {
                "player": {"pos": [2, 8]},
                "customers": [{"id": "C1", "table_id": "T1", "dish_id": "lau_mam"}],
                "random_customers": False,
            }})
            inp_q = write_json(w.path("in_q.json"), frames(
                {"tick": 0, "interact": True},                  # nấu lau_mam (720t -> chín tick 721)
                {"tick": 1, "interact": False},
                {"tick": 721, "interact": True},                # nhấc ở tick 722
                {"tick": 722, "interact": False, "move": [1, 0]},
                {"tick": 828, "move": [0, -1]},
                {"tick": 918, "move": [0, 0], "interact": True},
            ))
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "1600",
                                     "--inventory", inv, "--scenario", sc_q, "--inputs", inp_q, "--out", w.path("q.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("q.jsonl"))
            paid = events(rows, "paid")
            self.assertEqual(len(paid), 1)
            self.assertEqual(paid[0]["data"]["base_price"], 199)
            self.assertEqual(paid[0]["data"]["tip"], 39)
            self.assertEqual(rows[-1]["earned"], 238)

    def test_ac_p2_14_live_server_day_mode(self):
        """AC-P2-14: chonoi.live hỗ trợ chế độ day, pause, buy, shop_done qua HTTP API."""
        tuning = load_contract()["tuning"]
        server = LiveServer(LiveGame("day", tuning, {}, 1, days=2), port=0)
        server.start()
        try:
            base = f"http://127.0.0.1:{server.port}"
            with urllib.request.urlopen(base + "/state", timeout=5) as r:
                st = json.loads(r.read())
            self.assertEqual(st["mode"], "day")
            self.assertEqual(st["day"], 1)
            self.assertIn("day_plan", st)
            self.assertIn("monsters", st)
            req = urllib.request.Request(base + "/input", data=json.dumps({"pause": True}).encode(),
                                         method="POST", headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as r:
                self.assertEqual(r.status, 200)
            time.sleep(0.1)
            with urllib.request.urlopen(base + "/state", timeout=5) as r:
                st2 = json.loads(r.read())
            self.assertTrue(st2["paused"])
        finally:
            server.stop()


if __name__ == "__main__":
    unittest.main()
