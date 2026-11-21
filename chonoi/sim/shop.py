"""Buổi Shop — nâng cấp giữa các Ngày (TICKET-02, Test Contract v1.1).

Xử lý lệnh `buy` trước `shop_done`. Nâng cấp lưu vào `upgrades` ngay nhưng chỉ có hiệu lực từ Ngày kế.
"""


class ShopSim:
    mode = "shop"
    phase = "shop"

    def __init__(self, tuning, stock, money, earned, reputation, upgrades, active_upgrades):
        self.t = tuning["shop"]
        self.stock = {k: int(v) for k, v in stock.items() if v > 0}
        self.money = int(money)
        self.earned = int(earned)
        self.reputation = reputation
        self.upgrades = dict(upgrades)
        self.active_upgrades = dict(active_upgrades)
        self.time_left_ticks = int(self.t["max_ticks"])
        self.phase_tick = 0
        self.done = False
        self.reason = None

    def snapshot(self) -> dict:
        return {
            "stock": {k: self.stock[k] for k in sorted(self.stock) if self.stock[k] > 0},
        }

    def step(self, inp):
        events = []
        self.phase_tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        if inp.buy is not None:
            self._handle_buy(inp.buy, events)
        if inp.pressed("shop_done"):
            self.done = True
            self.reason = "done"
            events.append(("shop_end", {"reason": "done"}))
        elif self.time_left_ticks <= 0:
            self.done = True
            self.reason = "time"
            events.append(("shop_end", {"reason": "time"}))
        return events

    def _handle_buy(self, action, events):
        ups = self.t["upgrades"]
        if action not in ups:
            events.append(("buy_failed", {"action": action, "reason": "unknown"}))
            return
        tiers = ups[action]
        cur = self.upgrades.get(action, 0)
        if cur >= len(tiers):
            events.append(("buy_failed", {"action": action, "reason": "max_level"}))
            return
        tier = tiers[cur]
        price = int(tier["price"])
        if self.money < price:
            events.append(("buy_failed", {"action": action, "reason": "funds"}))
            return
        self.money -= price
        new_level = int(tier["level"])
        self.upgrades[action] = new_level
        events.append(("bought", {
            "upgrade": action,
            "level": new_level,
            "price": price,
            "money": self.money,
        }))
