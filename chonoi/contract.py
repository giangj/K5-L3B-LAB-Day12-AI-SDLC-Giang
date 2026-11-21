"""Đọc game.contract.json và kiểm dải hợp lệ của tuning (Test Contract v1.1)."""

import json
import os

from .errors import BadInput
from .inventory import KINDS_V11

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game.contract.json")

NODE_KINDS_V11 = ("bong_dien_dien", "bong_sung", "keo_neo")
FISH_KINDS_V11 = ("ca_linh", "ca_loc", "ca_keo")


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _between(name, v, lo, hi):
    if not _num(v) or not (lo <= v <= hi):
        raise BadInput(f"tuning.{name} phải trong [{lo}, {hi}], đang là {v!r}")


def load_contract(path=DEFAULT_PATH) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            c = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được {path}: {e}")
    validate_tuning(c.get("tuning"))
    return c


def _int_between(name, v, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int) or not (lo <= v <= hi):
        raise BadInput(f"tuning.{name} phải là số nguyên trong [{lo}, {hi}], đang là {v!r}")


def _pos_in(name, pos, bounds, keys):
    if not isinstance(pos, list) or len(pos) != 2 or not all(_num(c) for c in pos):
        raise BadInput(f"tuning.{name} phải là [số, số]")
    for c, k in zip(pos, keys):
        lo, hi = bounds[k]
        if not (lo <= c <= hi):
            raise BadInput(f"tuning.{name} nằm ngoài vùng {k} ∈ [{lo}, {hi}]")


def _bounds(name, b, keys):
    if not isinstance(b, dict) or set(b) != set(keys):
        raise BadInput(f"tuning.{name}.bounds phải có đúng khóa {list(keys)}")
    for k in keys:
        v = b[k]
        if not (isinstance(v, list) and len(v) == 2 and all(_num(c) for c in v) and v[0] == 0 and v[1] > 0):
            raise BadInput(f"tuning.{name}.bounds.{k} phải là [0, số dương]")


def _range_pair(name, r, lo_min, hi_max):
    if not (isinstance(r, list) and len(r) == 2 and all(_num(c) for c in r) and lo_min <= r[0] < r[1] <= hi_max):
        raise BadInput(f"tuning.{name} phải là [min, max] hợp lệ trong [{lo_min}, {hi_max}]")


def _validate_gather(g):
    """Dải hợp lệ gather v1.1 theo Test Contract."""
    _between("gather.duration_s", g.get("duration_s"), 60, 600)
    _bounds("gather", g.get("bounds"), ("x", "d"))
    b = g["bounds"]
    _between("gather.dock_radius", g.get("dock_radius"), 0.5, 5)
    _between("gather.interact_radius", g.get("interact_radius"), 0.5, 5)
    _between("gather.catch_radius", g.get("catch_radius"), 0.5, 5)
    _between("gather.swim_speed", g.get("swim_speed"), 1, 10)
    _between("gather.catch_cooldown_s", g.get("catch_cooldown_s"), 0, 10)
    _between("gather.oxygen_max_s", g.get("oxygen_max_s"), 10, 120)
    _int_between("gather.ramp_max_ticks", g.get("ramp_max_ticks"), 0, 6)
    _int_between("gather.hold_capacity", g.get("hold_capacity"), 4, 30)
    _int_between("gather.hp_max", g.get("hp_max"), 1, 99)
    _int_between("gather.oxygen_refill_per_tick", g.get("oxygen_refill_per_tick"), 1, 10_000)
    _int_between("gather.choke_interval_ticks", g.get("choke_interval_ticks"), 1, 10_000)
    _int_between("gather.node_yield", g.get("node_yield"), 1, 12)
    _between("gather.regrow_s", g.get("regrow_s"), 0.1, 600)
    _between("gather.surface_depth", g.get("surface_depth"), 0, 5)
    _pos_in("gather.dock_pos", g.get("dock_pos"), b, ("x", "d"))
    _pos_in("gather.start_pos", g.get("start_pos"), b, ("x", "d"))
    if not _num(g.get("start_heading_deg")):
        raise BadInput("tuning.gather.start_heading_deg phải là số")

    fy = g.get("fish_yield")
    if not isinstance(fy, dict) or set(fy) != set(FISH_KINDS_V11):
        raise BadInput(f"tuning.gather.fish_yield phải có đủ {FISH_KINDS_V11}")
    for k, v in fy.items():
        _int_between(f"gather.fish_yield.{k}", v, 1, g["hold_capacity"])

    nodes = g.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise BadInput("tuning.gather.nodes phải là mảng không rỗng")
    seen, kinds = set(), set()
    for n in nodes:
        if not isinstance(n, dict) or not isinstance(n.get("id"), str) or n["id"] in seen:
            raise BadInput("tuning.gather.nodes: mỗi nút cần id duy nhất")
        seen.add(n["id"])
        if n.get("kind") not in NODE_KINDS_V11:
            raise BadInput(f"tuning.gather.nodes.{n['id']}: kind phải thuộc {NODE_KINDS_V11}")
        kinds.add(n["kind"])
        _pos_in(f"gather.nodes.{n['id']}.pos", n.get("pos"), b, ("x", "d"))
        if n["pos"][1] != 0:
            raise BadInput(f"tuning.gather.nodes.{n['id']}: nút hái nằm ở mặt nước (d = 0)")
    if kinds != set(NODE_KINDS_V11):
        raise BadInput(f"tuning.gather.nodes phải có đủ 3 loại {NODE_KINDS_V11}")

    _int_between("gather.fish_max", g.get("fish_max"), 1, 100)
    _int_between("gather.fish_initial", g.get("fish_initial"), 1, g["fish_max"])
    _between("gather.fish_speed", g.get("fish_speed"), 0.1, 10)
    _int_between("gather.fish_turn_ticks", g.get("fish_turn_ticks"), 1, 10_000)
    _int_between("gather.fish_spawn_ticks", g.get("fish_spawn_ticks"), 1, 10_000)
    _between("gather.fish_spawn_clearance", g.get("fish_spawn_clearance"), 0, 20)
    _range_pair("gather.fish_x", g.get("fish_x"), b["x"][0], b["x"][1])

    fdepths = g.get("fish_depths")
    fsdepths = g.get("fish_spawn_depths")
    fweights = g.get("fish_weights")
    if not isinstance(fdepths, dict) or set(fdepths) != set(FISH_KINDS_V11):
        raise BadInput("tuning.gather.fish_depths phải có đủ 3 loài cá")
    if not isinstance(fsdepths, dict) or set(fsdepths) != set(FISH_KINDS_V11):
        raise BadInput("tuning.gather.fish_spawn_depths phải có đủ 3 loài cá")
    if not isinstance(fweights, dict) or set(fweights) != set(FISH_KINDS_V11):
        raise BadInput("tuning.gather.fish_weights phải có đủ 3 loài cá")
    for k in FISH_KINDS_V11:
        _range_pair(f"gather.fish_depths.{k}", fdepths[k], g["surface_depth"], b["d"][1])
        if not isinstance(fsdepths[k], list) or not fsdepths[k] or not all(
            _num(d) and g["surface_depth"] < d <= b["d"][1] for d in fsdepths[k]
        ):
            raise BadInput(f"tuning.gather.fish_spawn_depths.{k} phải là danh sách độ sâu dưới nước")
        if not _num(fweights[k]) or fweights[k] <= 0:
            raise BadInput(f"tuning.gather.fish_weights.{k} phải > 0")
    fsx = g.get("fish_spawn_x")
    if not isinstance(fsx, list) or not fsx or not all(_num(x) and b["x"][0] <= x <= b["x"][1] for x in fsx):
        raise BadInput("tuning.gather.fish_spawn_x phải là danh sách tọa độ x hợp lệ")

    monsters = g.get("monsters")
    if not isinstance(monsters, dict):
        raise BadInput("tuning.gather.monsters phải là object")
    _int_between("gather.monsters.invuln_ticks", monsters.get("invuln_ticks"), 0, 10_000)
    _between("gather.monsters.loss_ratio", monsters.get("loss_ratio"), 0, 1)
    species = monsters.get("species")
    if not isinstance(species, dict) or "ca_sau" not in species:
        raise BadInput("tuning.gather.monsters.species phải có ca_sau")
    for sp_id, sp in species.items():
        if not isinstance(sp, dict):
            raise BadInput(f"tuning.gather.monsters.species.{sp_id} phải là object")
        _between(f"gather.monsters.species.{sp_id}.patrol_speed", sp.get("patrol_speed"), 0.1, 10)
        _between(f"gather.monsters.species.{sp_id}.chase_speed", sp.get("chase_speed"), 0.1, 15)
        _between(f"gather.monsters.species.{sp_id}.detect_radius", sp.get("detect_radius"), 0.5, 50)
        _between(f"gather.monsters.species.{sp_id}.exit_radius", sp.get("exit_radius"), sp["detect_radius"], 100)
        _range_pair(f"gather.monsters.species.{sp_id}.depths", sp.get("depths"), g["surface_depth"], b["d"][1])
        _between(f"gather.monsters.species.{sp_id}.hit_radius", sp.get("hit_radius"), 0.1, 10)
        _int_between(f"gather.monsters.species.{sp_id}.recoil_ticks", sp.get("recoil_ticks"), 1, 10_000)
        _between(f"gather.monsters.species.{sp_id}.recoil_dist", sp.get("recoil_dist"), 0, 20)
    spawns = monsters.get("spawns")
    if not isinstance(spawns, list) or not spawns:
        raise BadInput("tuning.gather.monsters.spawns phải là mảng không rỗng")
    seen = set()
    for m in spawns:
        if not isinstance(m, dict) or not isinstance(m.get("id"), str) or m["id"] in seen:
            raise BadInput("tuning.gather.monsters.spawns: mỗi con cần id duy nhất")
        seen.add(m["id"])
        if m.get("kind") not in species:
            raise BadInput(f"tuning.gather.monsters.spawns.{m['id']}: kind không thuộc species")
        _pos_in(f"gather.monsters.spawns.{m['id']}.pos", m.get("pos"), b, ("x", "d"))
        wps = m.get("waypoints")
        if not isinstance(wps, list) or len(wps) != 2:
            raise BadInput(f"tuning.gather.monsters.spawns.{m['id']}.waypoints phải có 2 điểm")
        for idx, wp in enumerate(wps):
            _pos_in(f"gather.monsters.spawns.{m['id']}.waypoints[{idx}]", wp, b, ("x", "d"))
        _int_between(f"gather.monsters.spawns.{m['id']}.from_day", m.get("from_day"), 1, 5)


def _validate_quan_and_menu(q, menu):
    _between("quan.duration_s", q.get("duration_s"), 60, 600)
    _bounds("quan", q.get("bounds"), ("x", "z"))
    qb = q["bounds"]
    _between("quan.patience_s", q.get("patience_s"), 20, 180)
    _between("quan.walk_speed", q.get("walk_speed"), 1, 10)
    _between("quan.interact_radius", q.get("interact_radius"), 0.5, 5)
    _int_between("quan.ramp_max_ticks", q.get("ramp_max_ticks", 6), 0, 6)
    _between("quan.eat_s", q.get("eat_s"), 0.1, 600)
    _between("quan.customer_interval_s", q.get("customer_interval_s"), 0.1, 600)
    _int_between("quan.first_customer_tick", q.get("first_customer_tick"), 1, int(q["duration_s"] * 60) - 1)
    for arr_name in ("stoves", "tables"):
        arr = q.get(arr_name)
        if not isinstance(arr, list) or not arr:
            raise BadInput(f"tuning.quan.{arr_name} phải là mảng không rỗng")
        seen = set()
        for e in arr:
            if not isinstance(e, dict) or not isinstance(e.get("id"), str) or e["id"] in seen:
                raise BadInput(f"tuning.quan.{arr_name}: mỗi phần tử cần id duy nhất")
            seen.add(e["id"])
            _pos_in(f"quan.{arr_name}.{e['id']}.pos", e.get("pos"), qb, ("x", "z"))
    if not (_num(q.get("tip_rate")) and q["tip_rate"] > 0 and _num(q.get("left_reputation_delta"))
            and q["left_reputation_delta"] < 0):
        raise BadInput("tip_rate phải > 0 và left_reputation_delta phải < 0")
    ratio = q.get("tip_min_patience_ratio")
    if not (_num(ratio) and 0 < ratio <= 1):
        raise BadInput("quan.tip_min_patience_ratio phải thuộc (0, 1]")
    if not (_num(q.get("tip_reputation")) and q["tip_reputation"] > 0):
        raise BadInput("quan.tip_reputation phải > 0")
    if q.get("burn_s") is not None:
        raise BadInput("burn_s phải là null trong lõi")
    for dish_id, d in menu.items():
        price, cook, rec = d.get("price"), d.get("cook_s"), d.get("recipe")
        if isinstance(price, bool) or not isinstance(price, int) or price <= 0 or not _num(cook) or cook <= 0:
            raise BadInput(f"menu.{dish_id}: price (nguyên) và cook_s phải > 0")
        if not isinstance(rec, dict) or not rec:
            raise BadInput(f"menu.{dish_id}.recipe phải là map nguyên liệu khác rỗng")
        for ing, qty in rec.items():
            if ing not in KINDS_V11 or isinstance(qty, bool) or not isinstance(qty, int) or qty <= 0:
                raise BadInput(f"menu.{dish_id}.recipe.{ing} không hợp lệ")


def _validate_day_plan_and_shop(dp, shop, menu):
    if not isinstance(dp, list) or len(dp) != 5:
        raise BadInput("tuning.day_plan phải là mảng 5 ngày")
    for idx, entry in enumerate(dp, 1):
        if not isinstance(entry, dict) or entry.get("day") != idx:
            raise BadInput(f"tuning.day_plan[{idx - 1}].day phải là {idx}")
        dishes = entry.get("dishes")
        ingredients = entry.get("ingredients")
        if not isinstance(dishes, dict) or not dishes or not isinstance(ingredients, dict):
            raise BadInput(f"tuning.day_plan[{idx - 1}] thiếu dishes/ingredients")
        expected = {}
        for did, cnt in dishes.items():
            if did not in menu or isinstance(cnt, bool) or not isinstance(cnt, int) or cnt <= 0:
                raise BadInput(f"tuning.day_plan[{idx - 1}].dishes.{did} không hợp lệ")
            for ing, qty in menu[did]["recipe"].items():
                expected[ing] = expected.get(ing, 0) + qty * cnt
        if ingredients != expected:
            raise BadInput(f"tuning.day_plan[{idx - 1}].ingredients không khớp tổng công thức")

    if not isinstance(shop, dict):
        raise BadInput("tuning.shop phải là object")
    _int_between("shop.max_ticks", shop.get("max_ticks"), 1, 100_000)
    ups = shop.get("upgrades")
    if not isinstance(ups, dict) or not {"oxygen", "hp"} <= set(ups):
        raise BadInput("tuning.shop.upgrades phải có oxygen và hp")
    for uid in ("oxygen", "hp"):
        tiers = ups[uid]
        if not isinstance(tiers, list) or not tiers:
            raise BadInput(f"tuning.shop.upgrades.{uid} phải là mảng không rỗng")
        for lvl, item in enumerate(tiers, 1):
            if not isinstance(item, dict) or item.get("level") != lvl:
                raise BadInput(f"tuning.shop.upgrades.{uid}[{lvl - 1}].level phải là {lvl}")
            _int_between(f"shop.upgrades.{uid}[{lvl - 1}].price", item.get("price"), 1, 1_000_000)
            key = "oxygen_max_s" if uid == "oxygen" else "hp_max"
            if not _num(item.get(key)) or item[key] <= 0:
                raise BadInput(f"tuning.shop.upgrades.{uid}[{lvl - 1}].{key} phải > 0")


def validate_tuning(t):
    if not isinstance(t, dict):
        raise BadInput("thiếu khối tuning")
    g, q, menu = t.get("gather"), t.get("quan"), t.get("menu")
    dp, shop = t.get("day_plan"), t.get("shop")
    if not isinstance(g, dict) or not isinstance(q, dict) or not isinstance(menu, dict):
        raise BadInput("tuning phải có gather, quan, menu")
    _validate_gather(g)
    _validate_quan_and_menu(q, menu)
    _validate_day_plan_and_shop(dp, shop, menu)
