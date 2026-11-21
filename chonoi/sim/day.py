"""Chế độ Ngày (`day`): vòng lặp gather -> quan -> shop qua 1..5 Ngày (Test Contract v1.1)."""

from .gather import GatherSim
from .quan import QuanSim
from .shop import ShopSim


class DaySim:
    mode = "day"

    def __init__(self, tuning, scenario, streams, ids, days=1):
        self.tuning = tuning
        self.gather_sc = scenario.get("gather", {})
        self.quan_sc = scenario.get("quan", {})
        self.day_sc = scenario.get("day", {})
        self.rng = streams
        self.ids = ids
        self.target_days = int(days)
        self.day = 1
        self.days_completed = 0

        self.money = int(self.day_sc.get("money", 0))
        self.earned = int(self.day_sc.get("earned", 0))
        self.reputation = float(self.day_sc.get("reputation", tuning["quan"]["reputation_initial"]))
        self.upgrades = {k: int(v) for k, v in self.day_sc.get("upgrades", {}).items() if v > 0}
        self.active_upgrades = dict(self.upgrades)

        self._plans = self._build_plans(tuning, self.day_sc)
        self.phase = "gather"
        self.active = self._make_gather()
        self.done = False
        self.reason = None

    @staticmethod
    def _build_plans(tuning, day_sc):
        plans = {}
        for entry in tuning["day_plan"]:
            plans[entry["day"]] = {
                "dishes": dict(entry["dishes"]),
                "ingredients": dict(entry["ingredients"]),
            }
        for entry in day_sc.get("day_plan", []):
            dnum = entry["day"]
            dishes = dict(entry["dishes"])
            if "ingredients" in entry:
                ing = dict(entry["ingredients"])
            else:
                ing = {}
                for did, cnt in dishes.items():
                    for k, q in tuning["menu"][did]["recipe"].items():
                        ing[k] = ing.get(k, 0) + q * cnt
            plans[dnum] = {"dishes": dishes, "ingredients": ing}
        return plans

    def _current_plan(self):
        plan = self._plans[self.day]
        return {"dishes": dict(plan["dishes"]), "ingredients": dict(plan["ingredients"])}

    def _make_gather(self):
        return GatherSim(
            self.tuning,
            self.gather_sc,
            self.rng,
            self.ids,
            day=self.day,
            active_upgrades=self.active_upgrades,
            money=self.money,
            earned=self.earned,
            reputation=self.reputation,
        )

    def _make_quan(self, inventory):
        plan = self._plans[self.day]
        return QuanSim(
            self.tuning,
            self.quan_sc,
            self.rng,
            self.ids,
            inventory=inventory,
            allowed_dishes=set(plan["dishes"].keys()),
            money=self.money,
            earned=self.earned,
            reputation=self.reputation,
        )

    def _make_shop(self, stock):
        return ShopSim(
            self.tuning,
            stock=stock,
            money=self.money,
            earned=self.earned,
            reputation=self.reputation,
            upgrades=self.upgrades,
            active_upgrades=self.active_upgrades,
        )

    @property
    def phase_tick(self) -> int:
        return self.active.phase_tick

    @property
    def time_left_ticks(self) -> int:
        return self.active.time_left_ticks

    def startup_events(self) -> list:
        return [
            ("day_start", {}, "gather", self.day),
            ("day_plan", self._current_plan(), "gather", self.day),
            ("phase_start", {}, "gather", self.day),
        ]

    def snapshot(self) -> dict:
        s = self.active.snapshot()
        s.update({
            "day": self.day,
            "day_plan": self._current_plan(),
            "upgrades": {k: self.upgrades[k] for k in sorted(self.upgrades) if self.upgrades[k] > 0},
            "active_upgrades": {k: self.active_upgrades[k] for k in sorted(self.active_upgrades) if self.active_upgrades[k] > 0},
        })
        return s

    def step(self, inp) -> list:
        cur_phase = self.phase
        cur_day = self.day
        raw_events = self.active.step(inp)
        tagged = [(nm, dt, cur_phase, cur_day) for nm, dt in raw_events]
        if cur_phase == "quan":
            self.money = self.active.money
            self.earned = self.active.earned
            self.reputation = self.active.reputation
        elif cur_phase == "shop":
            self.money = self.active.money
            self.upgrades = dict(self.active.upgrades)

        if self.active.done:
            if cur_phase == "gather":
                inv = self.active.inventory_items()
                self.phase = "quan"
                self.active = self._make_quan(inv)
                tagged.append(("phase_start", {}, "quan", self.day))
            elif cur_phase == "quan":
                self.money = self.active.money
                self.earned = self.active.earned
                self.reputation = self.active.reputation
                leftover = dict(self.active.stock)
                self.phase = "shop"
                self.active = self._make_shop(leftover)
                tagged.append(("phase_start", {}, "shop", self.day))
            elif cur_phase == "shop":
                self.money = self.active.money
                self.upgrades = dict(self.active.upgrades)
                self.days_completed += 1
                if self.days_completed >= self.target_days:
                    self.done = True
                    self.reason = "days_complete"
                else:
                    self.day += 1
                    self.active_upgrades = dict(self.upgrades)
                    self.phase = "gather"
                    self.active = self._make_gather()
                    tagged.append(("day_start", {}, "gather", self.day))
                    tagged.append(("day_plan", self._current_plan(), "gather", self.day))
                    tagged.append(("phase_start", {}, "gather", self.day))
        return tagged
