"""Nạp và kiểm scenario (Contract D). Trả về dict của đúng khối theo mode.

KHUNG: kiểm cú pháp, id trùng, bộ đếm âm, khoang vượt sức chứa, trường lạ.
TODO(nhóm): bổ sung kiểm mâu thuẫn mức luật mà nhóm cần (khách giữ chỗ quá kho, đơn assigned
phải có đúng một món, khách eating thiếu giá/tip...) — xem PRD-0 mục D và 'Mâu thuẫn -> mã 2'.
"""

import json

from .errors import BadInput
from .inventory import KINDS_P1, validate_items

GATHER_KEYS = {"player", "hold", "nodes", "fish", "random_fish", "time_left_ticks"}
GATHER_PLAYER_KEYS = {"pos", "vel", "heading_deg", "hp", "oxygen_ticks", "zero_oxy_ticks",
                      "invuln_ticks", "catch_cd_ticks"}
NODE_KINDS = ("bong_dien_dien", "bong_sung")
FISH_KINDS = ("ca_linh", "ca_loc")
QUAN_PLAYER_KEYS = {"pos", "vel"}
QUAN_KEYS = {"player", "stock", "hand", "stoves", "tables", "customers", "random_customers",
             "reputation", "time_left_ticks"}
NODE_KEYS = {"id", "kind", "pos", "regrow_ticks"}
FISH_KEYS = {"id", "kind", "pos", "heading_deg"}
STOVE_KEYS = {"id", "pos", "state", "dish", "cook_ticks_left", "ready_ticks"}
TABLE_KEYS = {"id", "pos"}
DISH_KEYS = {"order_id", "dish_id", "base_price"}
CUSTOMER_KEYS = {"id", "table_id", "dish_id", "order_tick", "state", "patience_ticks_left",
                 "eat_ticks_left", "order_status", "reserved", "base_price", "tip"}
ORDER_STATUSES = ("reserved", "assigned", "unfulfillable", "served")
STOVE_STATES = ("idle", "cooking", "ready")
CUSTOMER_STATES = ("waiting", "eating")


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
    if not isinstance(data, dict) or not set(data) <= {"gather", "quan"}:
        raise BadInput("scenario chỉ được có khối 'gather' hoặc 'quan'")
    if set(data) - {mode}:
        raise BadInput(f"khối sai mode: chạy --mode {mode} chỉ nhận khối '{mode}'")
    block = data.get(mode, {})
    if not isinstance(block, dict):
        raise BadInput(f"khối {mode} phải là object")
    allowed = GATHER_KEYS if mode == "gather" else QUAN_KEYS
    extra = set(block) - allowed
    if extra:
        raise BadInput(f"trường lạ/chưa hỗ trợ trong {mode}: {sorted(extra)}")
    dur = int(round(tuning[mode]["duration_s"] * 60))
    if "time_left_ticks" in block:
        t = block["time_left_ticks"]
        if isinstance(t, bool) or not isinstance(t, int) or not (1 <= t <= dur):
            raise BadInput(f"time_left_ticks phải là số nguyên trong [1, {dur}]")
    if mode == "gather":
        _validate_gather(block, tuning)
    else:
        _validate_quan(block, tuning)
    return block


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _nonneg_int(name, v):
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise BadInput(f"{name} phải là số nguyên không âm")


def _pos(name, pos, bounds, axes=("x", "d")):
    if not (isinstance(pos, list) and len(pos) == 2 and all(_num(c) for c in pos)):
        raise BadInput(f"{name} phải là [{axes[0]}, {axes[1]}]")
    for c, axis in zip(pos, axes):
        lo, hi = bounds[axis]
        if not (lo <= c <= hi):
            raise BadInput(f"{name} nằm ngoài vùng nước ({axis} ∈ [{lo}, {hi}])")


def _validate_gather(b, tuning):
    g = tuning["gather"]
    bounds = g["bounds"]
    for arr in ("nodes", "fish"):
        if arr in b:
            _check_ids(arr, b[arr])
    if "random_fish" in b and not isinstance(b["random_fish"], bool):
        raise BadInput("random_fish phải là boolean")
    if "hold" in b:
        h = b["hold"]
        if not isinstance(h, list) or any(k not in KINDS_P1 for k in h):
            raise BadInput("hold phải là mảng id nguyên liệu hợp lệ")
        if len(h) > g["hold_capacity"]:
            raise BadInput("hold vượt sức chứa")
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
    omax = int(round(g["oxygen_max_s"] * 60))
    if "oxygen_ticks" in p and p["oxygen_ticks"] > omax:
        raise BadInput("player.oxygen_ticks vượt oxy tối đa")
    if "hp" in p and not (1 <= p["hp"] <= g["hp_max"]):
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


def _pos_int(name, v):
    if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
        raise BadInput(f"{name} phải là số nguyên dương")


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
        validate_items(b["stock"])
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
            if "reserved" in c and validate_items(c["reserved"]) != {}:
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
                if "reserved" in c and validate_items(c["reserved"]) != {}:
                    raise BadInput(f"customers.{c['id']}: đơn {order_status} phải có reserved rỗng")
            elif "reserved" in c:
                res = validate_items(c["reserved"])
                if res != menu[dish_id]["recipe"]:
                    raise BadInput(f"customers.{c['id']}: giữ chỗ khác công thức của {dish_id}")
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
