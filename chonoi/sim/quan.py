"""Buổi tối — Mở Quán (`quan`).

Luật Phase 1 (PRD-0 mục E, F — Quán v1.0):
  - Đồng hồ, bếp (nấu -> ready), kiên nhẫn, ăn.
  - Interact tối đa 1 đối tượng theo (khoảng cách, bếp trước bàn, id): nấu đơn reserved cũ nhất,
    nhấc món lên tay trống, giao món đúng order_id tới bàn (tính boa chính xác bằng Decimal).
  - Thanh toán (finished_eating / closing), rời bàn (patience / closing), dọn món/giữ chỗ,
    cộng/trừ uy tín theo tuning, khách mới theo lịch (first_customer_tick, customer_interval_s) và no_dish.
"""

from decimal import Decimal, ROUND_FLOOR
import math

from ..errors import BadInput
from ..ids import id_key, sort_by_id
from ..inventory import validate_items
from .ramp import ramp_velocity

TICK = 60.0


class QuanSim:
    mode = "quan"
    phase = "quan"

    def __init__(self, tuning, scenario, streams, ids, inventory=None):
        t = tuning["quan"]
        self.t = t
        self.menu = tuning["menu"]
        self.rng = streams
        self.ids = ids
        p = scenario.get("player", {})
        self.pos = [float(c) for c in p.get("pos", t["start_pos"])]
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        # kho: --inventory HOẶC scenario.stock (cả hai -> cli đã báo mã 2)
        src_stock = inventory if inventory is not None else scenario.get("stock", {})
        self.stock = {k: int(v) for k, v in src_stock.items() if v > 0}
        self.hand = dict(scenario["hand"]) if scenario.get("hand") is not None else None
        self.time_left_ticks = scenario.get("time_left_ticks", int(round(t["duration_s"] * TICK)))
        self.phase_tick = 0
        self.random_customers = bool(scenario.get("random_customers", True))
        self._rep_dec = Decimal(str(scenario.get("reputation", t["reputation_initial"])))
        self.reputation = float(self._rep_dec)
        self.stoves = [
            {
                "id": s["id"],
                "pos": [float(c) for c in s["pos"]],
                "state": s.get("state", "idle"),
                "dish": dict(s["dish"]) if s.get("dish") is not None else None,
                "cook_ticks_left": s.get("cook_ticks_left", 0),
                "ready_ticks": s.get("ready_ticks", 0),
            }
            for s in self._merge(t["stoves"], scenario.get("stoves", []))
        ]
        self.tables = [
            {"id": tb["id"], "pos": [float(c) for c in tb["pos"]]}
            for tb in self._merge(t["tables"], scenario.get("tables", []))
        ]
        self.customers = self._init_customers(scenario.get("customers", []))
        for e in self.customers:
            ids.reserve(e["id"])
        self.money = 0
        self.earned = 0
        self.shift_earned = 0
        self.done = False
        self.reason = None

    def _init_customers(self, raw_customers):
        pmax = int(round(self.t["patience_s"] * TICK))
        customers = []
        need_reserve = []
        for c in raw_customers:
            state = c.get("state", "waiting")
            order_status = c.get("order_status", "served" if state == "eating" else "reserved")
            res = validate_items(c["reserved"]) if "reserved" in c else None
            cust = {
                "id": c["id"],
                "table_id": c["table_id"],
                "dish_id": c["dish_id"],
                "order_tick": c.get("order_tick", 0),
                "state": state,
                "patience_ticks_left": c.get("patience_ticks_left", 0 if state == "eating" else pmax),
                "eat_ticks_left": c.get("eat_ticks_left", 0),
                "order_status": order_status,
                "reserved": res if res is not None else {},
                "base_price": c.get("base_price"),
                "tip": c.get("tip"),
            }
            customers.append(cust)
            if order_status == "reserved" and res is None:
                need_reserve.append(cust)
        for cust in sorted(need_reserve, key=lambda x: (x["order_tick"], id_key(x["table_id"]))):
            cust["reserved"] = dict(self.menu[cust["dish_id"]]["recipe"])
        total_res = {}
        for cust in customers:
            for k, qty in cust["reserved"].items():
                total_res[k] = total_res.get(k, 0) + qty
        for k, qty in total_res.items():
            if qty > self.stock.get(k, 0):
                raise BadInput(f"giữ chỗ nguyên liệu {k} ({qty}) vượt quá tồn kho ({self.stock.get(k, 0)})")
        return customers

    @staticmethod
    def _merge(defaults, updates):
        by_id = {d["id"]: dict(d) for d in defaults}
        for u in updates:
            if u["id"] not in by_id:
                raise BadInput(f"id bếp/bàn không tồn tại: {u['id']}")
            by_id[u["id"]].update(u)
        return sort_by_id(list(by_id.values()))

    def snapshot(self) -> dict:
        occupied = {c["table_id"]: c["id"] for c in self.customers}
        return {
            "player": {"pos": list(self.pos)},
            "stock": {k: self.stock[k] for k in sorted(self.stock) if self.stock[k] > 0},
            "hand": dict(self.hand) if self.hand is not None else None,
            "stoves": [
                {
                    "id": s["id"],
                    "pos": list(s["pos"]),
                    "state": s["state"],
                    "dish": dict(s["dish"]) if s["dish"] is not None else None,
                    "cook_ticks_left": s["cook_ticks_left"],
                    "ready_ticks": s["ready_ticks"],
                }
                for s in sort_by_id(self.stoves)
            ],
            "tables": [
                {"id": tb["id"], "pos": list(tb["pos"]), "customer_id": occupied.get(tb["id"])}
                for tb in sort_by_id(self.tables)
            ],
            "customers": [
                {
                    "id": c["id"],
                    "table_id": c["table_id"],
                    "dish_id": c["dish_id"],
                    "order_tick": c["order_tick"],
                    "state": c["state"],
                    "patience_ticks_left": c["patience_ticks_left"],
                    "eat_ticks_left": c["eat_ticks_left"],
                    "order_status": c["order_status"],
                    "reserved": {k: c["reserved"][k] for k in sorted(c["reserved"]) if c["reserved"][k] > 0},
                    "base_price": c["base_price"],
                    "tip": c["tip"],
                }
                for c in sort_by_id(self.customers)
            ],
        }

    def step(self, inp):
        events = []
        # 1. Đồng hồ, bếp, kiên nhẫn và ăn (ready_ticks chỉ tăng cho món đã ready ở đầu bước)
        self.phase_tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        for s in self.stoves:
            if s["state"] == "ready":
                s["ready_ticks"] += 1
            elif s["state"] == "cooking":
                s["cook_ticks_left"] = max(0, s["cook_ticks_left"] - 1)
        for c in self.customers:
            if c["state"] == "waiting":
                c["patience_ticks_left"] = max(0, c["patience_ticks_left"] - 1)
            elif c["state"] == "eating":
                c["eat_ticks_left"] = max(0, c["eat_ticks_left"] - 1)

        # 2. Xét bếp theo id: món nấu xong chuyển ready với ready_ticks = 0
        for s in sort_by_id(self.stoves):
            if s["state"] == "cooking" and s["cook_ticks_left"] == 0:
                s["state"] = "ready"
                s["ready_ticks"] = 0
                events.append(("dish_ready", {
                    "stove_id": s["id"],
                    "order_id": s["dish"]["order_id"],
                    "dish_id": s["dish"]["dish_id"],
                }))

        # 3. Di chuyển và tối đa một interact theo (khoảng cách, bếp trước bàn, id)
        self._move(inp)
        if inp.pressed("interact"):
            self._handle_interact(events)

        # 4. Thanh toán / khách bỏ đi / đóng ca
        self._resolve_customers(events)
        if self.time_left_ticks <= 0:
            self.done = True
            self.reason = "time"
            events.append(("quan_end", {
                "reason": "time",
                "money": self.money,
                "earned": self.earned,
                "shift_earned": self.shift_earned,
                "reputation": self.reputation,
            }))
            return events

        # 5. Khách mới theo lịch (first_customer_tick, customer_interval_s)
        if self.random_customers:
            self._spawn_customer_if_due(events)
        return events

    def _handle_interact(self, events):
        r = self.t["interact_radius"]
        candidates = []
        for s in self.stoves:
            d = math.dist(self.pos, s["pos"])
            if d <= r:
                candidates.append((d, 0, id_key(s["id"]), "stove", s))
        for tb in self.tables:
            d = math.dist(self.pos, tb["pos"])
            if d <= r:
                candidates.append((d, 1, id_key(tb["id"]), "table", tb))
        if not candidates:
            return
        _, _, _, kind, obj = min(candidates, key=lambda x: (x[0], x[1], x[2]))
        if kind == "stove":
            if obj["state"] == "idle":
                reserved_custs = [
                    c for c in self.customers if c["state"] == "waiting" and c["order_status"] == "reserved"
                ]
                if not reserved_custs:
                    return
                cust = min(reserved_custs, key=lambda c: (c["order_tick"], id_key(c["table_id"])))
                items_list = []
                for ing in sorted(cust["reserved"]):
                    qty = cust["reserved"][ing]
                    self.stock[ing] = self.stock.get(ing, 0) - qty
                    if self.stock[ing] <= 0:
                        self.stock.pop(ing, None)
                    items_list.extend([ing] * qty)
                cust["reserved"] = {}
                cust["order_status"] = "assigned"
                base_price = int(self.menu[cust["dish_id"]]["price"])
                obj["state"] = "cooking"
                obj["dish"] = {"order_id": cust["id"], "dish_id": cust["dish_id"], "base_price": base_price}
                obj["cook_ticks_left"] = int(round(self.menu[cust["dish_id"]]["cook_s"] * TICK))
                obj["ready_ticks"] = 0
                events.append(("cook_started", {
                    "stove_id": obj["id"],
                    "order_id": cust["id"],
                    "dish_id": cust["dish_id"],
                    "items": items_list,
                    "base_price": base_price,
                }))
            elif obj["state"] == "ready" and self.hand is None:
                dish = obj["dish"]
                self.hand = dict(dish)
                obj["state"] = "idle"
                obj["dish"] = None
                obj["cook_ticks_left"] = 0
                obj["ready_ticks"] = 0
                events.append(("dish_picked", {
                    "stove_id": obj["id"],
                    "order_id": dish["order_id"],
                    "dish_id": dish["dish_id"],
                }))
        else:  # table
            if self.hand is None:
                return
            cust = next((c for c in self.customers if c["table_id"] == obj["id"]), None)
            if cust is None or cust["state"] != "waiting" or cust["id"] != self.hand["order_id"]:
                return
            pmax = int(round(self.t["patience_s"] * TICK))
            qualifies = (
                Decimal(cust["patience_ticks_left"])
                >= Decimal(pmax) * Decimal(str(self.t["tip_min_patience_ratio"]))
            )
            base_price = int(self.hand["base_price"])
            tip = (
                int((Decimal(base_price) * Decimal(str(self.t["tip_rate"]))).to_integral_value(rounding=ROUND_FLOOR))
                if qualifies else 0
            )
            cust["state"] = "eating"
            cust["order_status"] = "served"
            cust["eat_ticks_left"] = int(round(self.t["eat_s"] * TICK))
            cust["base_price"] = base_price
            cust["tip"] = tip
            dish_id = self.hand["dish_id"]
            self.hand = None
            events.append(("served", {
                "order_id": cust["id"],
                "table_id": obj["id"],
                "dish_id": dish_id,
                "patience_ticks_left": cust["patience_ticks_left"],
                "base_price": base_price,
                "tip": tip,
            }))

    def _add_rep(self, delta):
        lo = Decimal(str(self.t["reputation_min"]))
        hi = Decimal(str(self.t["reputation_max"]))
        self._rep_dec = max(lo, min(hi, self._rep_dec + Decimal(str(delta))))
        self.reputation = float(self._rep_dec)

    def _pay_customer(self, cust, reason, events):
        amount = cust["base_price"] + cust["tip"]
        self.money += amount
        self.earned += amount
        self.shift_earned += amount
        if cust["tip"] > 0:
            self._add_rep(self.t["tip_reputation"])
        events.append(("paid", {
            "order_id": cust["id"],
            "table_id": cust["table_id"],
            "base_price": cust["base_price"],
            "tip": cust["tip"],
            "amount": amount,
            "reason": reason,
        }))
        self.customers.remove(cust)

    def _cleanup_customer_order(self, cust):
        cust["reserved"] = {}
        if self.hand is not None and self.hand["order_id"] == cust["id"]:
            self.hand = None
        for s in self.stoves:
            if s["dish"] is not None and s["dish"]["order_id"] == cust["id"]:
                s["state"] = "idle"
                s["dish"] = None
                s["cook_ticks_left"] = 0
                s["ready_ticks"] = 0

    def _resolve_customers(self, events):
        eating_done = sorted(
            [c for c in self.customers if c["state"] == "eating" and c["eat_ticks_left"] == 0],
            key=lambda c: id_key(c["table_id"]),
        )
        for c in eating_done:
            self._pay_customer(c, "finished_eating", events)

        if self.time_left_ticks > 0:
            impatient = sorted(
                [c for c in self.customers if c["state"] == "waiting" and c["patience_ticks_left"] == 0],
                key=lambda c: id_key(c["table_id"]),
            )
            for c in impatient:
                self._add_rep(self.t["left_reputation_delta"])
                self._cleanup_customer_order(c)
                self.customers.remove(c)
                events.append(("customer_left", {
                    "order_id": c["id"],
                    "table_id": c["table_id"],
                    "reason": "patience",
                    "reputation": self.reputation,
                }))
        else:
            still_eating = sorted(
                [c for c in self.customers if c["state"] == "eating"],
                key=lambda c: id_key(c["table_id"]),
            )
            for c in still_eating:
                self._pay_customer(c, "closing", events)
            still_waiting = sorted(
                [c for c in self.customers if c["state"] == "waiting"],
                key=lambda c: id_key(c["table_id"]),
            )
            for c in still_waiting:
                self._cleanup_customer_order(c)
                self.customers.remove(c)
                events.append(("customer_left", {
                    "order_id": c["id"],
                    "table_id": c["table_id"],
                    "reason": "closing",
                    "reputation": self.reputation,
                }))

    def _spawn_customer_if_due(self, events):
        first = int(self.t["first_customer_tick"])
        interval = int(round(self.t["customer_interval_s"] * TICK))
        if self.phase_tick < first or (self.phase_tick - first) % interval != 0:
            return
        occupied = {c["table_id"] for c in self.customers}
        empty_tables = [tb for tb in sort_by_id(self.tables) if tb["id"] not in occupied]
        if not empty_tables:
            return
        avail = dict(self.stock)
        for c in self.customers:
            for ing, qty in c["reserved"].items():
                avail[ing] = avail.get(ing, 0) - qty
        cookable = [
            d for d in sorted(self.menu.keys())
            if all(avail.get(ing, 0) >= qty for ing, qty in self.menu[d]["recipe"].items())
        ]
        if not cookable:
            events.append(("no_dish", {}))
            return
        dish_id = self.rng.get("customer_dish").choice(cookable)
        tb = empty_tables[0]
        cid = self.ids.new("C")
        pmax = int(round(self.t["patience_s"] * TICK))
        self.customers.append({
            "id": cid,
            "table_id": tb["id"],
            "dish_id": dish_id,
            "order_tick": self.phase_tick,
            "state": "waiting",
            "patience_ticks_left": pmax,
            "eat_ticks_left": 0,
            "order_status": "reserved",
            "reserved": dict(self.menu[dish_id]["recipe"]),
            "base_price": None,
            "tip": None,
        })
        events.append(("customer_arrived", {
            "order_id": cid,
            "table_id": tb["id"],
            "dish_id": dish_id,
        }))

    def _move(self, inp):
        speed = self.t["walk_speed"]
        mx, mz = inp.move
        self.vel = ramp_velocity(self, (mx * speed, mz * speed), int(self.t.get("ramp_max_ticks", 6)))
        b = self.t["bounds"]
        for i, axis in enumerate(("x", "z")):
            self.pos[i] += self.vel[i] / TICK
            lo, hi = b[axis]
            if self.pos[i] <= lo:
                self.pos[i], self.vel[i] = lo, max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i], self.vel[i] = hi, min(0.0, self.vel[i])
