"""Vòng tick (Contract B, mô hình tick v1.1).

Hỗ trợ `gather`, `quan`, `day`, `pause`/`resumed`, event theo pha/ngày và `days_completed`.
"""

import math

from .ids import IdAllocator
from .inputs import InputPlayer
from .inventory import write_inventory
from .jsonl import JsonlWriter
from .rng import Streams
from .sim.day import DaySim
from .sim.gather import GatherSim
from .sim.quan import QuanSim


def build_sim(mode, tuning, scenario, seed, inventory, days=1):
    streams, ids = Streams(seed), IdAllocator()
    if mode == "gather":
        return GatherSim(tuning, scenario, streams, ids)
    if mode == "quan":
        return QuanSim(tuning, scenario, streams, ids, inventory=inventory)
    return DaySim(tuning, scenario, streams, ids, days=days)


def _common(sim, tick, sim_tick, phase_tick, tuning, state):
    mult = tuning["score"]["reputation_multiplier"]
    return {
        "type": "snapshot",
        "tick": tick,
        "sim_tick": sim_tick,
        "mode": sim.mode,
        "phase": sim.phase,
        "phase_tick": phase_tick,
        "state": state,
        "time_left_ticks": sim.time_left_ticks,
        "money": sim.money,
        "earned": sim.earned,
        "reputation": sim.reputation,
        "score": sim.earned + mult * math.floor(sim.reputation),
    }


class Session:
    """Một lượt chơi: dựng sim, bước từng tick (gồm pause), lấy snapshot / dòng end."""

    def __init__(self, mode, tuning, scenario, seed, inventory=None, days=1):
        self.mode = mode
        self.tuning = tuning
        self.sim = build_sim(mode, tuning, scenario, seed, inventory, days=days)
        self.tick = 0
        self.sim_tick = 0
        self.paused = False

    @property
    def done(self) -> bool:
        return self.sim.done

    def _event_row(self, tick, phase, day, name, data) -> dict:
        row = {"type": "event", "tick": tick, "phase": phase}
        if self.mode == "day":
            row["day"] = day
        row["name"] = name
        row["data"] = data
        return row

    def startup_events(self) -> list:
        if hasattr(self.sim, "startup_events"):
            return [self._event_row(0, ph, d, nm, dt) for nm, dt, ph, d in self.sim.startup_events()]
        return []

    def snapshot(self) -> dict:
        state = "finished" if self.sim.done else ("paused" if self.paused else "playing")
        ptick = getattr(self.sim, "phase_tick", self.sim_tick)
        s = _common(self.sim, self.tick, self.sim_tick, ptick, self.tuning, state)
        s.update(self.sim.snapshot())
        return s

    def step(self, inp) -> list:
        """Chạy một bước với `inp` (chonoi.inputs.InputState); trả các dòng event (tick = k + 1)."""
        out_rows = []
        cur_phase = self.sim.phase
        cur_day = getattr(self.sim, "day", 1)
        if inp.pressed("pause"):
            if not self.paused:
                self.paused = True
                self.tick += 1
                return [self._event_row(self.tick, cur_phase, cur_day, "paused", {})]
            self.paused = False
            out_rows.append(self._event_row(self.tick + 1, cur_phase, cur_day, "resumed", {}))
        elif self.paused:
            self.tick += 1
            return []

        self.tick += 1
        self.sim_tick += 1
        events = self.sim.step(inp)
        for ev in events:
            if len(ev) == 4:
                nm, dt, ph, dy = ev
            else:
                nm, dt = ev
                ph, dy = self.sim.phase, cur_day
            out_rows.append(self._event_row(self.tick, ph, dy, nm, dt))
        return out_rows

    def end_row(self) -> dict:
        sim = self.sim
        ptick = getattr(sim, "phase_tick", self.sim_tick)
        score = _common(sim, self.tick, self.sim_tick, ptick, self.tuning, "")["score"]
        row = {
            "type": "end",
            "ticks": self.tick,
            "sim_tick": self.sim_tick,
            "mode": sim.mode,
            "state": "finished" if sim.done else ("paused" if self.paused else "playing"),
            "reason": sim.reason if sim.done else "tick_limit",
            "money": sim.money,
            "earned": sim.earned,
            "reputation": sim.reputation,
            "score": score,
        }
        if self.mode == "day":
            row["days_completed"] = sim.days_completed
        return row

    def write_inventory_if_done(self, inventory_out):
        """File kho: ghi MỘT lần khi có gather_end; chưa kết thúc thì giữ nguyên file đích."""
        if self.mode == "gather" and self.sim.done and inventory_out:
            write_inventory(inventory_out, self.sim.inventory_items())


def run(mode, tuning, scenario, seed, frames, ticks, out_path, snapshot_every,
        inventory=None, inventory_out=None, days=1):
    sess = Session(mode, tuning, scenario, seed, inventory, days=days)
    player = InputPlayer(frames)
    w = JsonlWriter(out_path)
    try:
        for row in sess.startup_events():
            w.write(row)
        w.write(sess.snapshot())  # tick 0: sau khi dựng scenario, trước mọi input
        last_snapped = 0
        while sess.tick < ticks and not sess.done:
            prev_phase = sess.sim.phase
            prev_day = getattr(sess.sim, "day", 1)
            inp = player.advance(sess.tick)  # bước k đọc input có tick == k
            for row in sess.step(inp):
                w.write(row)
            phase_changed = (sess.sim.phase != prev_phase) or (getattr(sess.sim, "day", 1) != prev_day)
            if sess.tick % snapshot_every == 0 or sess.done or phase_changed:
                w.write(sess.snapshot())
                last_snapped = sess.tick
        if last_snapped != sess.tick:
            w.write(sess.snapshot())
        w.write(sess.end_row())
    finally:
        w.close()
    sess.write_inventory_if_done(inventory_out)
    return sess.sim
