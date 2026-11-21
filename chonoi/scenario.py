"""Nạp và kiểm scenario (Contract D, v1.2). Hỗ trợ mode gather, quan, day."""

import json
import math

from .errors import BadInput
from .inventory import KINDS_V11, validate_item_instances

GATHER_KEYS = {"player", "hold", "nodes", "fish", "monsters", "random_fish", "time_left_ticks"}
GATHER_PLAYER_KEYS = {"pos", "vel", "heading_deg", "hp", "oxygen_ticks", "zero_oxy_ticks",
                      "invuln_ticks", "catch_cd_ticks"}
NODE_KINDS = ("bong_dien_dien", "bong_sung", "keo_neo")
FISH_KINDS = ("ca_linh", "ca_loc", "ca_keo")
QUAN_PLAYER_KEYS = {"pos", "vel"}
QUAN_KEYS = {"player", "stock", "hand", "stoves", "tables", "customers", "random_customers",
             "reputation", "time_left_ticks"}
NODE_KEYS = {"id", "kind", "pos", "regrow_ticks"}
FISH_KEYS = {"id", "kind", "pos", "heading_deg", "age_ticks"}
MONSTER_KEYS = {"id", "kind", "pos", "waypoints", "target_idx", "state", "state_ticks_left", "recoil_dir"}
MONSTER_STATES = ("patrol", "chase", "recoil")
STOVE_KEYS = {"id", "pos", "state", "dish", "cook_ticks_left", "ready_ticks"}
TABLE_KEYS = {"id", "pos"}
DISH_KEYS = {"order_id", "dish_id", "base_price"}
CUSTOMER_KEYS = {"id", "table_id", "dish_id", "order_tick", "state", "patience_ticks_left",
                 "eat_ticks_left", "order_status", "reserved", "base_price", "tip"}
ORDER_STATUSES = ("reserved", "assigned", "unfulfillable", "served")
STOVE_STATES = ("idle", "cooking", "ready")
CUSTOMER_STATES = ("waiting", "eating")
DAY_KEYS = {"money", "earned", "reputation", "upgrades", "day_plan"}


def _check_ids(name, arr):
    if not isinstance(arr, list):
        raise BadInput(f"{name} phải là mảng")
    seen = set()
    for e in arr:
        if not isinstance(e, dict) or not isinstance(e.get("id"), str) or not e["id"]:
            raise BadInput(f"{name}: mỗi phần tử cần id (chuỗi khác rỗng)")
        if e["id"] in seen:
            raise BadInput(f"{name}: id trùng {e['id']}")
        seen.add(e["id"])


def load_scenario(path, mode: str, tuning: dict) -> dict:
    if path is None:
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được scenario {path}: {e}")
    if not isinstance(data, dict):
        raise BadInput("scenario phải là JSON object")

    if mode == "day":
        if not set(data) <= {"day", "gather", "quan"}:
            raise BadInput("scenario chế độ day chỉ nhận khối 'day', 'gather', 'quan'")
        day_b = data.get("day", {})
        g_b = data.get("gather", {})
        q_b = data.get("quan", {})
        for k, blk in (("day", day_b), ("gather", g_b), ("quan", q_b)):
            if not isinstance(blk, dict):
                raise BadInput(f"khối {k} phải là object")
        oxy_s, hp_max = _validate_day(day_b, tuning)
        _validate_block_keys("gather", g_b, tuning)
        _validate_gather(g_b, tuning, omax_override=oxy_s, hp_max_override=hp_max)
        if "stock" in q_b or "reputation" in q_b:
            raise BadInput("chế độ day cấm khai quan.stock hoặc quan.reputation")
        _validate_block_keys("quan", q_b, tuning)
        _validate_quan(q_b, tuning)
        return {"day": day_b, "gather": g_b, "quan": q_b}

    if not set(data) <= {"gather", "quan"}:
        raise BadInput("scenario chỉ được có khối 'gather' hoặc 'quan'")
    if set(data) - {mode}:
        raise BadInput(f"khối sai mode: chạy --mode {mode} chỉ nhận khối '{mode}'")
    block = data.get(mode, {})
    if not isinstance(block, dict):
        raise BadInput(f"khối {mode} phải là object")
    _validate_block_keys(mode, block, tuning)
    if mode == "gather":
        _validate_gather(block, tuning)
    else:
        _validate_quan(block, tuning)
    return block


def _validate_block_keys(mode, block, tuning):
    allowed = GATHER_KEYS if mode == "gather" else QUAN_KEYS
    extra = set(block) - allowed
    if extra:
        raise BadInput(f"trường lạ/chưa hỗ trợ trong {mode}: {sorted(extra)}")
    dur = int(round(tuning[mode]["duration_s"] * 60))
    if "time_left_ticks" in block:
        t = block["time_left_ticks"]
        if isinstance(t, bool) or not isinstance(t, int) or not (1 <= t <= dur):
            raise BadInput(f"time_left_ticks phải là số nguyên trong [1, {dur}]")


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _nonneg_int(name, v):
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise BadInput(f"{name} phải là số nguyên không âm")


def _pos_int(name, v):
    if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
        raise BadInput(f"{name} phải là số nguyên dương")


def _pos(name, pos, bounds, axes=("x", "d")):
    if not (isinstance(pos, list) and len(pos) == 2 and all(_num(c) for c in pos)):
        raise BadInput(f"{name} phải là [{axes[0]}, {axes[1]}]")
    for c, axis in zip(pos, axes):
        lo, hi = bounds[axis]
        if not (lo <= c <= hi):
            raise BadInput(f"{name} nằm ngoài vùng nước ({axis} ∈ [{lo}, {hi}])")


def _validate_ingredient_counts(raw) -> dict[str, int]:
    if not isinstance(raw, dict):
        raise BadInput("ingredients phải là object ánh xạ {nguyên liệu: số nguyên dương}")
    out = {}
    for k, v in raw.items():
        if k not in KINDS_V11:
            raise BadInput(f"nguyên liệu lạ trong day_plan.ingredients: {k!r}")
        if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
            raise BadInput(f"số lượng {k} phải là số nguyên dương")
        out[k] = v
    return out


def _validate_reserved_ids(name: str, raw) -> list[str]:
    if not isinstance(raw, list):
        raise BadInput(f"{name}.reserved phải là mảng id cá thể (v1.2)")
    seen = set()
    out = []
    for rid in raw:
        if not isinstance(rid, str) or not rid:
            raise BadInput(f"{name}.reserved: mỗi id phải là chuỗi khác rỗng")
        if rid in seen:
            raise BadInput(f"{name}.reserved: trùng id {rid}")
        seen.add(rid)
        out.append(rid)
    return out


def _validate_day(d, tuning):
    extra = set(d) - DAY_KEYS
    if extra:
        raise BadInput(f"trường lạ trong day: {sorted(extra)}")
    if ("money" in d) != ("earned" in d):
        raise BadInput("day: phải khai cả money và earned khi đặt tiền đầu kỳ")
    if "money" in d:
        _nonneg_int("day.money", d["money"])
        _nonneg_int("day.earned", d["earned"])
        if d["money"] > d["earned"]:
            raise BadInput("day: cần 0 <= money <= earned")
    q = tuning["quan"]
    if "reputation" in d:
        rep = d["reputation"]
        if not _num(rep) or not (q["reputation_min"] <= rep <= q["reputation_max"]):
            raise BadInput("day.reputation ngoài miền hợp lệ")
    oxy_s = tuning["gather"]["oxygen_max_s"]
    hp_max = tuning["gather"]["hp_max"]
    shop_ups = tuning["shop"]["upgrades"]
    if "upgrades" in d:
        ups = d["upgrades"]
        if not isinstance(ups, dict):
            raise BadInput("day.upgrades phải là object")
        for k, lvl in ups.items():
            if k not in shop_ups:
                raise BadInput(f"day.upgrades: khóa lạ {k}")
            _nonneg_int(f"day.upgrades.{k}", lvl)
            if lvl > len(shop_ups[k]):
                raise BadInput(f"day.upgrades.{k} vượt cấp tối đa")
            if lvl > 0:
                if k == "oxygen":
                    oxy_s = shop_ups[k][lvl - 1]["oxygen_max_s"]
                elif k == "hp":
                    hp_max = shop_ups[k][lvl - 1]["hp_max"]
    if "day_plan" in d:
        dp = d["day_plan"]
        if not isinstance(dp, list):
            raise BadInput("day.day_plan phải là mảng")
        seen_days = set()
        menu = tuning["menu"]
        for entry in dp:
            if not isinstance(entry, dict):
                raise BadInput("day.day_plan phần tử phải là object")
            dnum = entry.get("day")
            if isinstance(dnum, bool) or not isinstance(dnum, int) or not (1 <= dnum <= 5) or dnum in seen_days:
                raise BadInput(f"day.day_plan.day không hợp lệ hoặc trùng: {dnum!r}")
            seen_days.add(dnum)
            dishes = entry.get("dishes")
            if not isinstance(dishes, dict) or not dishes:
                raise BadInput(f"day.day_plan[day={dnum}].dishes phải là object khác rỗng")
            expected = {}
            for did, cnt in dishes.items():
                if did not in menu:
                    raise BadInput(f"day.day_plan[day={dnum}]: món lạ {did}")
                _pos_int(f"day.day_plan[day={dnum}].dishes.{did}", cnt)
                for ing, qty in menu[did]["recipe"].items():
                    expected[ing] = expected.get(ing, 0) + qty * cnt
            if "ingredients" in entry:
                ing_map = _validate_ingredient_counts(entry["ingredients"])
                if ing_map != expected:
                    raise BadInput(f"day.day_plan[day={dnum}].ingredients không khớp tổng công thức")
    return oxy_s, hp_max


def _validate_gather(b, tuning, omax_override=None, hp_max_override=None):
    g = tuning["gather"]
    bounds = g["bounds"]
    for arr in ("nodes", "fish", "monsters"):
        if arr in b:
            _check_ids(arr, b[arr])
    if "random_fish" in b and not isinstance(b["random_fish"], bool):
        raise BadInput("random_fish phải là boolean")
    if "hold" in b:
        cleaned_hold = validate_item_instances(b["hold"])
        if len(cleaned_hold) > g["hold_capacity"]:
            raise BadInput("hold vượt sức chứa")
        hold_ids = {it["id"] for it in cleaned_hold}
        for arr in ("nodes", "fish", "monsters"):
            for e in b.get(arr, []):
                if e.get("id") in hold_ids:
                    raise BadInput(f"trùng id vật lý giữa hold và {arr}: {e['id']}")
    p = b.get("player", {})
    if not isinstance(p, dict):
        raise BadInput("player phải là object")
    extra = set(p) - GATHER_PLAYER_KEYS
    if extra:
        raise BadInput(f"trường lạ/chưa hỗ trợ trong gather.player: {sorted(extra)}")
    if "pos" in p:
        _pos("player.pos", p["pos"], bounds)
    if "vel" in p and not (isinstance(p["vel"], list) and len(p["vel"]) == 2 and all(_num(c) for c in p["vel"])):
        raise BadInput("player.vel phải là [x, d]")
    if "heading_deg" in p and not _num(p["heading_deg"]):
        raise BadInput("player.heading_deg phải là số")
    for key in ("invuln_ticks", "catch_cd_ticks", "zero_oxy_ticks", "oxygen_ticks", "hp"):
        if key in p:
            _nonneg_int(f"player.{key}", p[key])
    omax = int(round((omax_override if omax_override is not None else g["oxygen_max_s"]) * 60))
    hp_max = hp_max_override if hp_max_override is not None else g["hp_max"]
    if "oxygen_ticks" in p and p["oxygen_ticks"] > omax:
        raise BadInput("player.oxygen_ticks vượt oxy tối đa")
    if "hp" in p and not (1 <= p["hp"] <= hp_max):
        raise BadInput("player.hp phải trong [1, hp_max]")
    if "zero_oxy_ticks" in p:
        pos = p.get("pos", g["start_pos"])
        oxy = p.get("oxygen_ticks", omax)
        if p["zero_oxy_ticks"] > 59:
            raise BadInput("player.zero_oxy_ticks phải trong [0, 59]")
        if p["zero_oxy_ticks"] > 0 and not (oxy == 0 and pos[1] > g["surface_depth"]):
            raise BadInput("player.zero_oxy_ticks > 0 chỉ khi oxy = 0 và đang dưới nước")
    for n in b.get("nodes", []):
        extra_n = set(n) - NODE_KEYS
        if extra_n:
            raise BadInput(f"nodes.{n['id']}: trường lạ {sorted(extra_n)}")
        if n.get("kind") not in NODE_KINDS:
            raise BadInput(f"nodes.{n['id']}: kind phải là một trong {NODE_KINDS}")
        _pos(f"nodes.{n['id']}.pos", n.get("pos"), bounds)
        if n["pos"][1] != 0:
            raise BadInput(f"nodes.{n['id']}: nút hái nằm ở mặt nước (d = 0)")
        if "regrow_ticks" in n:
            _nonneg_int(f"nodes.{n['id']}.regrow_ticks", n["regrow_ticks"])
    for f in b.get("fish", []):
        extra_f = set(f) - FISH_KEYS
        if extra_f:
            raise BadInput(f"fish.{f['id']}: trường lạ {sorted(extra_f)}")
        if f.get("kind") not in FISH_KINDS:
            raise BadInput(f"fish.{f['id']}: kind phải là một trong {FISH_KINDS}")
        _pos(f"fish.{f['id']}.pos", f.get("pos"), bounds)
        if f["pos"][1] <= g["surface_depth"]:
            raise BadInput(f"fish.{f['id']}: đàn cá phải ở dưới nước")
        if "heading_deg" in f and not _num(f["heading_deg"]):
            raise BadInput(f"fish.{f['id']}.heading_deg phải là số")
        if "age_ticks" in f:
            _nonneg_int(f"fish.{f['id']}.age_ticks", f["age_ticks"])

    species_map = g["monsters"]["species"]
    for m in b.get("monsters", []):
        extra_m = set(m) - MONSTER_KEYS
        if extra_m:
            raise BadInput(f"monsters.{m['id']}: trường lạ {sorted(extra_m)}")
        kind = m.get("kind")
        if kind not in species_map:
            raise BadInput(f"monsters.{m['id']}: kind không hợp lệ {kind!r}")
        d_lo, d_hi = species_map[kind]["depths"]
        _pos(f"monsters.{m['id']}.pos", m.get("pos"), bounds)
        if not (d_lo <= m["pos"][1] <= d_hi):
            raise BadInput(f"monsters.{m['id']}.pos nằm ngoài dải độ sâu của loài")
        wps = m.get("waypoints")
        if not isinstance(wps, list) or len(wps) != 2:
            raise BadInput(f"monsters.{m['id']}.waypoints phải có đúng 2 điểm")
        for idx, wp in enumerate(wps):
            _pos(f"monsters.{m['id']}.waypoints[{idx}]", wp, bounds)
            if not (d_lo <= wp[1] <= d_hi):
                raise BadInput(f"monsters.{m['id']}.waypoints[{idx}] ngoài dải độ sâu của loài")
        tidx = m.get("target_idx", 1)
        if isinstance(tidx, bool) or tidx not in (0, 1):
            raise BadInput(f"monsters.{m['id']}.target_idx phải là 0 hoặc 1")
        st = m.get("state", "patrol")
        if st not in MONSTER_STATES:
            raise BadInput(f"monsters.{m['id']}.state không hợp lệ: {st!r}")
        st_left = m.get("state_ticks_left", 0)
        _nonneg_int(f"monsters.{m['id']}.state_ticks_left", st_left)
        rdir = m.get("recoil_dir")
        if st == "recoil":
            if st_left <= 0:
                raise BadInput(f"monsters.{m['id']}: state recoil cần state_ticks_left > 0")
            if (not isinstance(rdir, list) or len(rdir) != 2 or not all(_num(c) and math.isfinite(c) for c in rdir)
                    or abs(math.hypot(rdir[0], rdir[1]) - 1.0) > 1e-3):
                raise BadInput(f"monsters.{m['id']}: recoil_dir phải là vector đơn vị")
        else:
            if st_left != 0 or rdir is not None:
                raise BadInput(f"monsters.{m['id']}: state {st} phải có state_ticks_left=0 và recoil_dir=null")


def _validate_dish_payload(name, dish, menu):
    if not isinstance(dish, dict) or set(dish) != DISH_KEYS:
        raise BadInput(f"{name} phải có đúng các trường {sorted(DISH_KEYS)}")
    if not isinstance(dish["order_id"], str) or not dish["order_id"]:
        raise BadInput(f"{name}.order_id phải là chuỗi khác rỗng")
    if dish["dish_id"] not in menu:
        raise BadInput(f"{name}.dish_id không thuộc menu: {dish['dish_id']!r}")
    _pos_int(f"{name}.base_price", dish["base_price"])


def _validate_quan(b, tuning):
    q = tuning["quan"]
    menu = tuning["menu"]
    qb = q["bounds"]
    for arr in ("stoves", "tables", "customers"):
        if arr in b:
            _check_ids(arr, b[arr])
    if "random_customers" in b and not isinstance(b["random_customers"], bool):
        raise BadInput("quan.random_customers phải là boolean")
    if "reputation" in b:
        rep = b["reputation"]
        if not _num(rep) or not (q["reputation_min"] <= rep <= q["reputation_max"]):
            raise BadInput("quan.reputation ngoài miền hợp lệ")
    if "stock" in b:
        cleaned_stock = validate_item_instances(b["stock"])
        stock_ids = {it["id"] for it in cleaned_stock}
        for arr in ("stoves", "tables", "customers"):
            for e in b.get(arr, []):
                if e.get("id") in stock_ids:
                    raise BadInput(f"trùng id vật lý giữa stock và {arr}: {e['id']}")
    p = b.get("player", {})
    if not isinstance(p, dict) or set(p) - QUAN_PLAYER_KEYS:
        raise BadInput("quan.player chỉ có pos và vel")
    if "pos" in p:
        _pos("player.pos", p["pos"], qb, axes=("x", "z"))
    if "vel" in p and not (isinstance(p["vel"], list) and len(p["vel"]) == 2 and all(_num(c) for c in p["vel"])):
        raise BadInput("player.vel phải là [x, z]")

    known_stoves = {s["id"] for s in q["stoves"]}
    known_tables = {t["id"] for t in q["tables"]}
    active_dishes = []

    for s in b.get("stoves", []):
        if s["id"] not in known_stoves:
            raise BadInput(f"id bếp không tồn tại: {s['id']}")
        extra = set(s) - STOVE_KEYS
        if extra:
            raise BadInput(f"stoves.{s['id']}: trường lạ {sorted(extra)}")
        if "pos" in s:
            _pos(f"stoves.{s['id']}.pos", s["pos"], qb, axes=("x", "z"))
        st = s.get("state", "idle")
        if st not in STOVE_STATES:
            raise BadInput(f"stoves.{s['id']}: state không hợp lệ {st!r}")
        dish = s.get("dish")
        cook_left = s.get("cook_ticks_left", 0)
        ready_ticks = s.get("ready_ticks", 0)
        _nonneg_int(f"stoves.{s['id']}.cook_ticks_left", cook_left)
        _nonneg_int(f"stoves.{s['id']}.ready_ticks", ready_ticks)
        if st == "idle":
            if dish is not None or cook_left != 0 or ready_ticks != 0:
                raise BadInput(f"stoves.{s['id']}: bếp idle không được có món hoặc timer dương")
        elif st == "cooking":
            if dish is None or cook_left <= 0 or ready_ticks != 0:
                raise BadInput(f"stoves.{s['id']}: bếp cooking phải có dish, cook_ticks_left > 0 và ready_ticks == 0")
            _validate_dish_payload(f"stoves.{s['id']}.dish", dish, menu)
            active_dishes.append(dish)
        else:  # ready
            if dish is None or cook_left != 0:
                raise BadInput(f"stoves.{s['id']}: bếp ready phải có dish và cook_ticks_left == 0")
            _validate_dish_payload(f"stoves.{s['id']}.dish", dish, menu)
            active_dishes.append(dish)

    for tb in b.get("tables", []):
        if tb["id"] not in known_tables:
            raise BadInput(f"id bàn không tồn tại: {tb['id']}")
        extra = set(tb) - TABLE_KEYS
        if extra:
            raise BadInput(f"tables.{tb['id']}: trường lạ {sorted(extra)}")
        if "pos" in tb:
            _pos(f"tables.{tb['id']}.pos", tb["pos"], qb, axes=("x", "z"))

    if "hand" in b and b["hand"] is not None:
        _validate_dish_payload("quan.hand", b["hand"], menu)
        active_dishes.append(b["hand"])

    pmax = int(round(q["patience_s"] * 60))
    customers_by_id = {}
    table_ids = []
    seen_reserved_ids: set[str] = set()
    for c in b.get("customers", []):
        extra = set(c) - CUSTOMER_KEYS
        if extra:
            raise BadInput(f"customers.{c['id']}: trường lạ {sorted(extra)}")
        if not isinstance(c.get("table_id"), str) or c["table_id"] not in known_tables:
            raise BadInput(f"customers.{c['id']}: table_id phải là bàn có thật")
        table_ids.append(c["table_id"])
        dish_id = c.get("dish_id")
        if dish_id not in menu:
            raise BadInput(f"customers.{c['id']}: dish_id không thuộc menu")
        _nonneg_int(f"customers.{c['id']}.order_tick", c.get("order_tick", 0))
        state = c.get("state", "waiting")
        if state not in CUSTOMER_STATES:
            raise BadInput(f"customers.{c['id']}: state không hợp lệ {state!r}")
        order_status = c.get("order_status", "served" if state == "eating" else "reserved")
        if order_status not in ORDER_STATUSES:
            raise BadInput(f"customers.{c['id']}: order_status không hợp lệ {order_status!r}")
        if state == "eating":
            if order_status != "served":
                raise BadInput(f"customers.{c['id']}: khách eating phải có order_status == 'served'")
            if "eat_ticks_left" not in c:
                raise BadInput(f"customers.{c['id']}: khách eating thiếu eat_ticks_left")
            _pos_int(f"customers.{c['id']}.eat_ticks_left", c["eat_ticks_left"])
            if "base_price" not in c or "tip" not in c:
                raise BadInput(f"customers.{c['id']}: khách eating phải có base_price và tip")
            _pos_int(f"customers.{c['id']}.base_price", c["base_price"])
            _nonneg_int(f"customers.{c['id']}.tip", c["tip"])
            if "patience_ticks_left" in c:
                _nonneg_int(f"customers.{c['id']}.patience_ticks_left", c["patience_ticks_left"])
                if c["patience_ticks_left"] > pmax:
                    raise BadInput(f"customers.{c['id']}.patience_ticks_left vượt patience tối đa")
            if "reserved" in c and _validate_reserved_ids(f"customers.{c['id']}", c["reserved"]) != []:
                raise BadInput(f"customers.{c['id']}: khách eating không được giữ chỗ nguyên liệu")
        else:  # waiting
            if order_status == "served":
                raise BadInput(f"customers.{c['id']}: khách waiting không được có order_status == 'served'")
            if "eat_ticks_left" in c:
                _nonneg_int(f"customers.{c['id']}.eat_ticks_left", c["eat_ticks_left"])
                if c["eat_ticks_left"] != 0:
                    raise BadInput(f"customers.{c['id']}: khách waiting phải có eat_ticks_left == 0")
            if "patience_ticks_left" in c:
                _pos_int(f"customers.{c['id']}.patience_ticks_left", c["patience_ticks_left"])
                if c["patience_ticks_left"] > pmax:
                    raise BadInput(f"customers.{c['id']}.patience_ticks_left vượt patience tối đa")
            if c.get("base_price") is not None or c.get("tip") is not None:
                raise BadInput(f"customers.{c['id']}: khách waiting không được chốt sẵn base_price/tip")
            if order_status in ("assigned", "unfulfillable"):
                if "reserved" in c and _validate_reserved_ids(f"customers.{c['id']}", c["reserved"]) != []:
                    raise BadInput(f"customers.{c['id']}: đơn {order_status} phải có reserved rỗng")
            elif "reserved" in c:
                res_ids = _validate_reserved_ids(f"customers.{c['id']}", c["reserved"])
                for rid in res_ids:
                    if rid in seen_reserved_ids:
                        raise BadInput(f"cá thể {rid} bị giữ chỗ trùng giữa các đơn")
                    seen_reserved_ids.add(rid)
                need_cnt = sum(menu[dish_id]["recipe"].values())
                if len(res_ids) != need_cnt:
                    raise BadInput(f"customers.{c['id']}: số cá thể giữ chỗ ({len(res_ids)}) khác công thức {dish_id} ({need_cnt})")
        customers_by_id[c["id"]] = (c, state, order_status)

    if len(table_ids) != len(set(table_ids)):
        raise BadInput("hai khách cùng bàn")

    seen_orders = set()
    for dish in active_dishes:
        oid = dish["order_id"]
        if oid in seen_orders:
            raise BadInput(f"bếp và tay giữ trùng đơn {oid}")
        seen_orders.add(oid)
        if oid not in customers_by_id:
            raise BadInput(f"món tham chiếu đơn không tồn tại: {oid}")
        c, state, order_status = customers_by_id[oid]
        if state != "waiting" or order_status != "assigned":
            raise BadInput(f"đơn {oid} có món nhưng khách không ở trạng thái waiting/assigned")
        if c["dish_id"] != dish["dish_id"]:
            raise BadInput(f"món trên bếp/tay ({dish['dish_id']}) không khớp đơn {oid} ({c['dish_id']})")

    for cid, (_, _, order_status) in customers_by_id.items():
        if order_status == "assigned" and cid not in seen_orders:
            raise BadInput(f"đơn assigned {cid} phải có đúng một món ở bếp hoặc trên tay")
