"""Soak headless nhiều Ngày liên tục bằng bot tất định (Contract v1.3)."""

import argparse
import json
import math
import os
import sys
import tempfile
import time

from .contract import load_contract
from .errors import BadInput
from .inputs import BUTTONS_V11, InputState
from .runner import Session


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write(f"lỗi: {message}\n")
        sys.exit(2)


def _dir_to(src, dst) -> tuple[float, float]:
    dx, dy = dst[0] - src[0], dst[1] - src[1]
    dist = math.hypot(dx, dy)
    if dist <= 1e-6:
        return (0.0, 0.0)
    return (dx / dist, dy / dist)


def _bot_input(snap: dict, tuning: dict) -> InputState:
    """Bot tất định điều khiển gather -> quan -> shop dựa hoàn toàn vào snapshot."""
    phase = snap.get("phase")
    btns = set()
    move = (0.0, 0.0)
    buy = None

    if phase == "gather":
        g = tuning["gather"]
        p = snap["player"]
        ppos = p["pos"]
        hold_cnt = snap.get("hold_count", len(snap.get("hold", [])))
        cap = snap.get("hold_capacity", 12)
        need_surface = p["oxygen_ticks"] < p["oxygen_max_ticks"] * 0.4
        dock_pos = g["dock_pos"]
        dock_r = g["dock_radius"]
        ready_nodes = [n for n in snap.get("nodes", []) if n.get("ready")]

        if hold_cnt >= 6 or snap.get("time_left_ticks", 0) <= 1500 or hold_cnt >= cap:
            move = _dir_to(ppos, dock_pos)
            if math.dist(ppos, dock_pos) <= dock_r:
                btns.add("interact")
        elif need_surface:
            move = (0.0, -1.0)
        elif ready_nodes:
            target = min(ready_nodes, key=lambda n: math.dist(ppos, n["pos"]))
            move = _dir_to(ppos, target["pos"])
            if p["at_surface"] and math.dist(ppos, target["pos"]) <= g["interact_radius"]:
                btns.add("interact")
        else:
            fishes = snap.get("fish", [])
            if fishes and hold_cnt <= cap - 3:
                target = min(fishes, key=lambda f: math.dist(ppos, f["pos"]))
                move = _dir_to(ppos, target["pos"])
                if not p["at_surface"] and p["catch_cd_ticks"] == 0 and math.dist(ppos, target["pos"]) <= g["catch_radius"]:
                    btns.add("catch")
            else:
                move = _dir_to(ppos, dock_pos)
                if math.dist(ppos, dock_pos) <= dock_r:
                    btns.add("interact")

    elif phase == "quan":
        q = tuning["quan"]
        ppos = snap["player"]["pos"]
        r = q["interact_radius"]
        hand = snap.get("hand")
        stoves = snap.get("stoves", [])
        tables = {tb["id"]: tb for tb in snap.get("tables", [])}
        custs = snap.get("customers", [])

        if hand is not None:
            cust = next((c for c in custs if c["id"] == hand["order_id"]), None)
            if cust and cust["table_id"] in tables:
                tpos = tables[cust["table_id"]]["pos"]
                move = _dir_to(ppos, tpos)
                if math.dist(ppos, tpos) <= r:
                    btns.add("interact")
        else:
            ready_stoves = [s for s in stoves if s["state"] == "ready"]
            if ready_stoves:
                st = min(ready_stoves, key=lambda s: math.dist(ppos, s["pos"]))
                move = _dir_to(ppos, st["pos"])
                if math.dist(ppos, st["pos"]) <= r:
                    btns.add("interact")
            else:
                has_waiting_res = any(c["state"] == "waiting" and c["order_status"] == "reserved" for c in custs)
                idle_stoves = [s for s in stoves if s["state"] == "idle"]
                if has_waiting_res and idle_stoves:
                    st = min(idle_stoves, key=lambda s: math.dist(ppos, s["pos"]))
                    move = _dir_to(ppos, st["pos"])
                    if math.dist(ppos, st["pos"]) <= r:
                        btns.add("interact")

    elif phase == "shop":
        ups = tuning["shop"]["upgrades"]
        cur = snap.get("upgrades", {})
        money = snap.get("money", 0)
        for uid in ("oxygen", "hp"):
            tiers = ups.get(uid, [])
            lv = cur.get(uid, 0)
            if lv < len(tiers) and money >= tiers[lv]["price"]:
                buy = uid
                break
        if buy is None:
            btns.add("shop_done")

    return InputState(move=move, held=btns, edges=btns, buy=buy)


def _write_json_atomic(path: str, obj: dict) -> None:
    abs_p = os.path.abspath(path)
    parent = os.path.dirname(abs_p)
    os.makedirs(parent, exist_ok=True)
    fd, tmp_p = tempfile.mkstemp(prefix=".soak_", suffix=".tmp", dir=parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp_p, abs_p)
    except Exception:
        if os.path.exists(tmp_p):
            os.remove(tmp_p)
        raise


def main(argv=None) -> int:
    t0 = time.perf_counter()
    p = _Parser(prog="chonoi.soak")
    p.add_argument("--seed", required=True, type=int)
    p.add_argument("--days", required=True, type=int)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    if a.days <= 0:
        sys.stderr.write("đầu vào sai: --days phải > 0\n")
        return 2

    try:
        tuning = load_contract()["tuning"]
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2

    results: list[dict] = []
    crashes = 0
    days_completed = 0
    try:
        sess = Session("day", tuning, {}, a.seed, days=a.days)
        max_ticks = a.days * 25000
        while not sess.done and sess.tick < max_ticks:
            snap = sess.snapshot()
            inp = _bot_input(snap, tuning)
            rows = sess.step(inp)
            for ev in rows:
                if ev.get("name") == "shop_end":
                    end_snap = sess.snapshot()
                    results.append({
                        "day": ev.get("day", len(results) + 1),
                        "earned": sess.sim.earned,
                        "reputation": sess.sim.reputation,
                        "score": end_snap["score"],
                    })
        days_completed = sess.sim.days_completed
    except Exception as exc:
        crashes += 1
        sys.stderr.write(f"soak crash: {exc}\n")

    out_obj = {
        "days": a.days,
        "days_completed": days_completed,
        "crashes": crashes,
        "results": results,
        "duration_s": round(time.perf_counter() - t0, 4),
    }
    _write_json_atomic(a.out, out_obj)
    return 0 if crashes == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
