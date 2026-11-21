"""Buổi sáng — Lặn & Hái (`gather`).

Luật Phase 1 & Phase 2 (Test Contract v1.1):
  - Bơi + chặn mép, dive / surface, oxy dưới nước (-1/tick), hồi trên mặt nước (+oxygen_refill_per_tick).
  - Ngạt (choke, xuyên bất tử và không rơi hàng) và ngất (faint, bỏ giỏ LIFO).
  - Đàn cá tự bơi 1.5 m/s, đổi hướng mỗi fish_turn_ticks, phản xạ mép/góc, sinh thêm tại 360*k.
  - Cá Sấu Năm Chèo (M1 từ Ngày 1, M2 từ Ngày 3): patrol / chase / hit (LIFO floor(hold/2), bất tử 90t, recoil 60t).
  - Interact (bến trước, hái nút mặt nước + mọc lại), Catch (dùng vị trí cá trước khi bơi), hết giờ, xuất kho.
"""

import math

from ..ids import id_key, sort_by_id
from ..inventory import hold_to_items
from .ramp import ramp_velocity

TICK = 60.0
AXES = ("x", "d")


class GatherSim:
    mode = "gather"
    phase = "gather"

    def __init__(self, tuning, scenario, streams, ids, day=1, active_upgrades=None,
                 money=0, earned=0, reputation=None):
        t = tuning["gather"]
        self.tuning = tuning
        self.t = t
        self.day = day
        self.rng = streams
        self.ids = ids
        p = scenario.get("player", {})
        self.pos = [float(c) for c in p.get("pos", t["start_pos"])]
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        self.heading = float(p.get("heading_deg", t["start_heading_deg"]))

        oxy_s, hp_max = self._resolve_upgrade_caps(tuning, active_upgrades)
        self.oxygen_max = int(round(oxy_s * TICK))
        self.hp_max = int(hp_max)
        self.oxygen_ticks = p.get("oxygen_ticks", self.oxygen_max)
        self.hp = p.get("hp", self.hp_max)
        self.zero_oxy_ticks = p.get("zero_oxy_ticks", 0)
        self.invuln_ticks = p.get("invuln_ticks", 0)
        self.catch_cd_ticks = p.get("catch_cd_ticks", 0)
        self.hold = list(scenario.get("hold", []))  # thứ tự nhặt, cuối mảng là mới nhất
        self.time_left_ticks = scenario.get("time_left_ticks", int(round(t["duration_s"] * TICK)))
        self.phase_tick = 0
        self.random_fish = bool(scenario.get("random_fish", True))

        src_nodes = scenario["nodes"] if "nodes" in scenario else t["nodes"]
        self.nodes = [
            {
                "id": n["id"],
                "kind": n["kind"],
                "pos": [float(c) for c in n["pos"]],
                "regrow_ticks": n.get("regrow_ticks", 0),
            }
            for n in src_nodes
        ]
        for n in self.nodes:
            ids.reserve(n["id"])

        self.fish = self._init_fish(scenario, t, ids)
        self.monsters = self._init_monsters(scenario, t, ids, day)

        self.money = money
        self.earned = earned
        self.reputation = tuning["quan"]["reputation_initial"] if reputation is None else reputation
        self.done = False
        self.reason = None

    @staticmethod
    def _resolve_upgrade_caps(tuning, active_upgrades):
        t = tuning["gather"]
        oxy_s = t["oxygen_max_s"]
        hp_max = t["hp_max"]
        ups = active_upgrades or {}
        shop_ups = tuning.get("shop", {}).get("upgrades", {})
        if ups.get("oxygen", 0) > 0:
            for tier in shop_ups.get("oxygen", []):
                if tier["level"] == ups["oxygen"]:
                    oxy_s = tier["oxygen_max_s"]
                    break
        if ups.get("hp", 0) > 0:
            for tier in shop_ups.get("hp", []):
                if tier["level"] == ups["hp"]:
                    hp_max = tier["hp_max"]
                    break
        return oxy_s, hp_max

    def _init_fish(self, scenario, t, ids):
        if "fish" in scenario:
            fish = [
                {
                    "id": f["id"],
                    "kind": f["kind"],
                    "pos": [float(c) for c in f["pos"]],
                    "heading_deg": float(f.get("heading_deg", 0)),
                    "age_ticks": int(f.get("age_ticks", 0)),
                }
                for f in scenario["fish"]
            ]
            for f in fish:
                ids.reserve(f["id"])
            return fish
        if not self.random_fish:
            return []
        fish = []
        occupied = set()
        rng = self.rng.get("fish_spawn")
        species_order = sorted(t["fish_weights"].keys())
        for _ in range(int(t["fish_initial"])):
            pts_by_kind = {
                k: [
                    (float(x), float(d))
                    for x in t["fish_spawn_x"]
                    for d in t["fish_spawn_depths"][k]
                    if (float(x), float(d)) not in occupied
                ]
                for k in species_order
            }
            avail_kinds = [k for k in species_order if pts_by_kind[k]]
            if not avail_kinds:
                break
            weights = [t["fish_weights"][k] for k in avail_kinds]
            kind = rng.choices(avail_kinds, weights=weights, k=1)[0]
            px, pd = rng.choice(pts_by_kind[kind])
            occupied.add((px, pd))
            hdg = rng.uniform(0.0, 360.0)
            fish.append({
                "id": ids.new("F"),
                "kind": kind,
                "pos": [px, pd],
                "heading_deg": hdg,
                "age_ticks": 0,
            })
        return fish

    @staticmethod
    def _init_monsters(scenario, t, ids, day):
        if "monsters" in scenario:
            monsters = [
                {
                    "id": m["id"],
                    "kind": m["kind"],
                    "pos": [float(c) for c in m["pos"]],
                    "waypoints": [[float(c) for c in wp] for wp in m["waypoints"]],
                    "target_idx": int(m.get("target_idx", 1)),
                    "state": m.get("state", "patrol"),
                    "state_ticks_left": int(m.get("state_ticks_left", 0)),
                    "recoil_dir": [float(c) for c in m["recoil_dir"]] if m.get("recoil_dir") is not None else None,
                }
                for m in scenario["monsters"]
            ]
        else:
            monsters = [
                {
                    "id": s["id"],
                    "kind": s["kind"],
                    "pos": [float(c) for c in s["pos"]],
                    "waypoints": [[float(c) for c in wp] for wp in s["waypoints"]],
                    "target_idx": 1,
                    "state": "patrol",
                    "state_ticks_left": 0,
                    "recoil_dir": None,
                }
                for s in t["monsters"]["spawns"]
                if s["from_day"] <= day
            ]
        for m in monsters:
            ids.reserve(m["id"])
        return monsters

    # --- giao diện cho runner -------------------------------------------------
    def inventory_items(self) -> dict:
        return hold_to_items(self.hold)

    def snapshot(self) -> dict:
        return {
            "player": {
                "pos": list(self.pos),
                "vel": list(self.vel),
                "heading_deg": self.heading,
                "oxygen_ticks": self.oxygen_ticks,
                "oxygen_max_ticks": self.oxygen_max,
                "hp": self.hp,
                "hp_max": self.hp_max,
                "zero_oxy_ticks": self.zero_oxy_ticks,
                "invuln_ticks": self.invuln_ticks,
                "catch_cd_ticks": self.catch_cd_ticks,
                "at_surface": self._at_surface(),
            },
            "hold": list(self.hold),
            "hold_count": len(self.hold),
            "hold_capacity": self.t["hold_capacity"],
            "nodes": [
                {
                    "id": n["id"],
                    "pos": list(n["pos"]),
                    "kind": n["kind"],
                    "ready": n["regrow_ticks"] == 0,
                    "regrow_ticks": n["regrow_ticks"],
                }
                for n in sort_by_id(self.nodes)
            ],
            "fish": [
                {
                    "id": f["id"],
                    "pos": list(f["pos"]),
                    "kind": f["kind"],
                    "heading_deg": f["heading_deg"],
                    "age_ticks": f["age_ticks"],
                }
                for f in sort_by_id(self.fish)
            ],
            "monsters": [
                {
                    "id": m["id"],
                    "kind": m["kind"],
                    "pos": list(m["pos"]),
                    "waypoints": [list(wp) for wp in m["waypoints"]],
                    "target_idx": m["target_idx"],
                    "state": m["state"],
                    "state_ticks_left": m["state_ticks_left"],
                    "recoil_dir": list(m["recoil_dir"]) if m["recoil_dir"] is not None else None,
                }
                for m in sort_by_id(self.monsters)
            ],
        }

    # --- một bước ---------------------------------------------------------------
    def step(self, inp):
        events = []
        # 1. đồng hồ, cooldown, bất tử và hồi nút
        self.phase_tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        self.invuln_ticks = max(0, self.invuln_ticks - 1)
        self.catch_cd_ticks = max(0, self.catch_cd_ticks - 1)
        for n in sort_by_id(self.nodes):
            if n["regrow_ticks"] > 0:
                n["regrow_ticks"] -= 1
                if n["regrow_ticks"] == 0:
                    events.append(("node_regrown", {"node_id": n["id"]}))

        # 2. bơi + chặn mép + dive/surface + oxy + ngạt (ngạt xuyên bất tử)
        was_surface = self._at_surface()
        self._move(inp)
        now_surface = self._at_surface()
        if was_surface and not now_surface:
            events.append(("dive", {"pos": list(self.pos)}))
        elif not was_surface and now_surface:
            events.append(("surface", {"pos": list(self.pos)}))

        if now_surface:
            self.oxygen_ticks = min(self.oxygen_max, self.oxygen_ticks + int(self.t["oxygen_refill_per_tick"]))
            self.zero_oxy_ticks = 0
        else:
            prev_oxy = self.oxygen_ticks
            self.oxygen_ticks = max(0, self.oxygen_ticks - 1)
            if prev_oxy > 0 and self.oxygen_ticks == 0:
                events.append(("oxygen_empty", {"oxygen_ticks": 0}))
            if self.oxygen_ticks == 0:
                self.zero_oxy_ticks += 1
                if self.zero_oxy_ticks >= int(self.t["choke_interval_ticks"]):
                    self.zero_oxy_ticks = 0
                    self.hp = max(0, self.hp - 1)
                    events.append(("choke", {"hp": self.hp}))
                    if self.hp <= 0:
                        lost = list(reversed(self.hold))
                        self.hold = []
                        events.append(("faint", {"cause": "choke", "lost": lost, "hp": 0}))
                        self._finish("fainted", events)
                        return events

        # 3. cập nhật thủy quái theo id và xét tối đa 1 hit
        if self._step_monsters(events):
            return events

        # 4. interact: bến trước, rồi hái nút ở mặt nước
        if inp.pressed("interact"):
            if self._in_dock():
                self._finish("docked", events)
                return events
            if now_surface:
                r = self.t["interact_radius"]
                candidates = [n for n in self.nodes if n["regrow_ticks"] == 0 and math.dist(self.pos, n["pos"]) <= r]
                if candidates:
                    node = min(candidates, key=lambda n: (math.dist(self.pos, n["pos"]), id_key(n["id"])))
                    amount = int(self.t["node_yield"])
                    free = int(self.t["hold_capacity"]) - len(self.hold)
                    if free >= amount:
                        self.hold.extend([node["kind"]] * amount)
                        node["regrow_ticks"] = int(round(self.t["regrow_s"] * TICK))
                        events.append(("gather", {"node_id": node["id"], "kind": node["kind"], "amount": amount}))
                    else:
                        events.append(("hold_full", {"action": "gather", "node_id": node["id"], "required": amount, "free": free}))

        # 5. bắt cá (dùng vị trí cá trước khi bơi)
        if inp.pressed("catch") and self.catch_cd_ticks == 0 and not now_surface:
            r = self.t["catch_radius"]
            candidates = [f for f in self.fish if math.dist(self.pos, f["pos"]) <= r]
            if candidates:
                fish = min(candidates, key=lambda f: (math.dist(self.pos, f["pos"]), id_key(f["id"])))
                yld = int(self.t["fish_yield"][fish["kind"]])
                free = int(self.t["hold_capacity"]) - len(self.hold)
                if free >= yld:
                    self.hold.extend([fish["kind"]] * yld)
                    self.fish.remove(fish)
                    self.catch_cd_ticks = int(round(self.t["catch_cooldown_s"] * TICK))
                    events.append(("fish_caught", {"fish_id": fish["id"], "kind": fish["kind"], "yield": yld}))
                else:
                    events.append(("hold_full", {"action": "catch", "fish_id": fish["id"], "required": yld, "free": free}))

        # 6. hết giờ
        if self.time_left_ticks <= 0:
            self._finish("time", events)
            return events

        # 7. còn giờ: cá bơi và sinh thêm theo lịch
        if self.random_fish:
            self._step_fish()
            self._spawn_fish_if_due(events)
        return events

    def _step_monsters(self, events) -> bool:
        m_cfg = self.t["monsters"]
        species_map = m_cfg["species"]
        bx_lo, bx_hi = self.t["bounds"]["x"]
        eligible_hits = []
        for m in sort_by_id(self.monsters):
            sp = species_map[m["kind"]]
            d_lo, d_hi = sp["depths"]
            if m["state"] == "recoil":
                step_d = sp["recoil_dist"] / sp["recoil_ticks"]
                rx, rd = m["recoil_dir"]
                m["pos"][0] = max(bx_lo, min(bx_hi, m["pos"][0] + rx * step_d))
                m["pos"][1] = max(d_lo, min(d_hi, m["pos"][1] + rd * step_d))
                m["state_ticks_left"] -= 1
                if m["state_ticks_left"] <= 0:
                    m["state"] = "patrol"
                    m["state_ticks_left"] = 0
                    m["recoil_dir"] = None
                continue

            player_in_zone = self.pos[1] >= d_lo
            dist_p = math.dist(m["pos"], self.pos)
            if m["state"] == "patrol":
                if player_in_zone and dist_p <= sp["detect_radius"]:
                    m["state"] = "chase"
            elif m["state"] == "chase":
                if not player_in_zone or dist_p > sp["exit_radius"]:
                    m["state"] = "patrol"

            if m["state"] == "chase":
                step_d = sp["chase_speed"] / TICK
                if dist_p <= step_d:
                    m["pos"] = [self.pos[0], self.pos[1]]
                else:
                    m["pos"][0] += (self.pos[0] - m["pos"][0]) / dist_p * step_d
                    m["pos"][1] += (self.pos[1] - m["pos"][1]) / dist_p * step_d
            else:
                wp = m["waypoints"][m["target_idx"]]
                dw = math.dist(m["pos"], wp)
                step_d = sp["patrol_speed"] / TICK
                if dw <= step_d:
                    m["pos"] = [wp[0], wp[1]]
                    m["target_idx"] = 1 - m["target_idx"]
                else:
                    m["pos"][0] += (wp[0] - m["pos"][0]) / dw * step_d
                    m["pos"][1] += (wp[1] - m["pos"][1]) / dw * step_d

            m["pos"][0] = max(bx_lo, min(bx_hi, m["pos"][0]))
            m["pos"][1] = max(d_lo, min(d_hi, m["pos"][1]))

            if self.invuln_ticks == 0 and player_in_zone:
                dh = math.dist(self.pos, m["pos"])
                if dh <= sp["hit_radius"]:
                    eligible_hits.append((dh, id_key(m["id"]), m, sp))

        if eligible_hits:
            _, _, m, sp = min(eligible_hits, key=lambda x: (x[0], x[1]))
            self.hp = max(0, self.hp - 1)
            drop_n = int(math.floor(len(self.hold) * m_cfg["loss_ratio"]))
            lost = []
            for _ in range(drop_n):
                lost.append(self.hold.pop())
            self.invuln_ticks = int(m_cfg["invuln_ticks"])
            dx = m["pos"][0] - self.pos[0]
            dd = m["pos"][1] - self.pos[1]
            norm = math.hypot(dx, dd)
            rdir = [dx / norm, dd / norm] if norm > 0 else [1.0, 0.0]
            m["state"] = "recoil"
            m["state_ticks_left"] = int(sp["recoil_ticks"])
            m["recoil_dir"] = rdir
            events.append(("monster_hit", {
                "monster_id": m["id"],
                "hp": self.hp,
                "lost": lost,
                "pos": list(self.pos),
            }))
            if self.hp <= 0:
                rem_lost = list(reversed(self.hold))
                self.hold = []
                events.append(("faint", {"cause": "monster", "lost": rem_lost, "hp": 0}))
                self._finish("fainted", events)
                return True
        return False

    def _step_fish(self):
        speed = float(self.t["fish_speed"]) / TICK
        turn_ticks = int(self.t["fish_turn_ticks"])
        x_lo, x_hi = self.t["fish_x"]
        rng = self.rng.get("fish_turn")
        for f in sort_by_id(self.fish):
            f["age_ticks"] += 1
            if f["age_ticks"] % turn_ticks == 0:
                f["heading_deg"] = rng.uniform(0.0, 360.0)
            rad = math.radians(f["heading_deg"])
            vx = math.cos(rad) * speed
            vd = math.sin(rad) * speed
            nx = f["pos"][0] + vx
            nd = f["pos"][1] + vd
            d_lo, d_hi = self.t["fish_depths"][f["kind"]]

            if nx <= x_lo and vx < 0:
                nx = x_lo + (x_lo - nx)
                vx = -vx
            elif nx >= x_hi and vx > 0:
                nx = x_hi - (nx - x_hi)
                vx = -vx

            if nd <= d_lo and vd < 0:
                nd = d_lo + (d_lo - nd)
                vd = -vd
            elif nd >= d_hi and vd > 0:
                nd = d_hi - (nd - d_hi)
                vd = -vd

            f["pos"][0] = max(x_lo, min(x_hi, nx))
            f["pos"][1] = max(d_lo, min(d_hi, nd))
            f["heading_deg"] = math.degrees(math.atan2(vd, vx)) % 360.0

    def _spawn_fish_if_due(self, events):
        if self.phase_tick % int(self.t["fish_spawn_ticks"]) != 0:
            return
        if len(self.fish) >= int(self.t["fish_max"]):
            return
        clearance = float(self.t["fish_spawn_clearance"])
        species_order = sorted(self.t["fish_weights"].keys())
        pts_by_kind = {}
        for k in species_order:
            valid = []
            for x in self.t["fish_spawn_x"]:
                for d in self.t["fish_spawn_depths"][k]:
                    pt = (float(x), float(d))
                    if all(math.dist(pt, f["pos"]) > clearance for f in self.fish):
                        valid.append(pt)
            pts_by_kind[k] = valid
        avail_kinds = [k for k in species_order if pts_by_kind[k]]
        if not avail_kinds:
            return
        rng = self.rng.get("fish_spawn")
        weights = [self.t["fish_weights"][k] for k in avail_kinds]
        kind = rng.choices(avail_kinds, weights=weights, k=1)[0]
        px, pd = rng.choice(pts_by_kind[kind])
        hdg = rng.uniform(0.0, 360.0)
        fid = self.ids.new("F")
        self.fish.append({
            "id": fid,
            "kind": kind,
            "pos": [px, pd],
            "heading_deg": hdg,
            "age_ticks": 0,
        })
        events.append(("fish_spawned", {"id": fid, "kind": kind, "pos": [px, pd]}))

    # --- tiện ích ---------------------------------------------------------------
    def _at_surface(self) -> bool:
        return self.pos[1] <= self.t["surface_depth"]

    def _in_dock(self) -> bool:
        return math.dist(self.pos, self.t["dock_pos"]) <= self.t["dock_radius"]

    def _finish(self, reason, events):
        self.done = True
        self.reason = reason
        events.append(("gather_end", {"reason": reason, "inventory": {"items": self.inventory_items()}}))

    def _move(self, inp):
        speed = self.t["swim_speed"]
        mx, md = inp.move
        self.vel = ramp_velocity(self, (mx * speed, md * speed), int(self.t["ramp_max_ticks"]))
        if (mx, md) != (0.0, 0.0):
            self.heading = math.degrees(math.atan2(md, mx)) % 360
        b = self.t["bounds"]
        for i, axis in enumerate(AXES):
            self.pos[i] += self.vel[i] / TICK
            lo, hi = b[axis]
            if self.pos[i] <= lo:
                self.pos[i] = lo
                self.vel[i] = max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i] = hi
                self.vel[i] = min(0.0, self.vel[i])
