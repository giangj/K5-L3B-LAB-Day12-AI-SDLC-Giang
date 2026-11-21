"""Hợp đồng và đọc/ghi nguyên tử file kho nguyên liệu theo Test Contract v1.2."""

from fractions import Fraction
import json
import math
import os
import tempfile

from chonoi.errors import BadInput
from chonoi.ids import sort_by_id

KINDS_P1 = ("ca_linh", "ca_loc", "bong_dien_dien", "bong_sung")
KINDS_V11 = ("ca_linh", "ca_loc", "ca_keo", "bong_dien_dien", "bong_sung", "keo_neo")
FRESH_SCALE = 240


def snap_fresh(val) -> Fraction:
    """Chuyển độ tươi JSON/số thành Fraction chính xác (hỗ trợ bội số 1/240 và số thập phân bất kỳ)."""
    if isinstance(val, Fraction):
        frac = val
    elif isinstance(val, bool) or not isinstance(val, (int, float)):
        raise BadInput("fresh phải là số hữu hạn trong [0, 100]")
    else:
        fval = float(val)
        if not math.isfinite(fval):
            raise BadInput("fresh phải là số hữu hạn trong [0, 100]")
        scaled = fval * FRESH_SCALE
        nearest = round(scaled)
        if abs(scaled - nearest) <= 1e-9:
            frac = Fraction(nearest, FRESH_SCALE)
        else:
            frac = Fraction(str(val))
    if frac < 0 or frac > 100:
        raise BadInput(f"fresh ngoài miền [0, 100]: {val!r}")
    return frac


def fresh_to_json(val) -> int | float:
    """Chuẩn hóa độ tươi sang int (nếu nguyên) hoặc float để xuất JSONL/file."""
    frac = snap_fresh(val)
    if frac.denominator == 1:
        return int(frac)
    return float(frac)


def serialize_item(item: dict) -> dict:
    """Xuất bản sao chuẩn {id, kind, fresh} (giữ độ chính xác float đầy đủ cho ngưỡng 30)."""
    return {
        "id": item["id"],
        "kind": item["kind"],
        "fresh": fresh_to_json(item["fresh"]),
    }


def validate_item_instances(raw, kinds=KINDS_V11, allow_empty_id: bool = False) -> list[dict]:
    """Kiểm tra mảng cá thể {id, kind, fresh}; trả bản sao chuẩn hóa giữ thứ tự vào."""
    if not isinstance(raw, list):
        raise BadInput("Contract v1.2 yêu cầu kho dạng mảng cá thể {id, kind, fresh}, không nhận kho đếm")
    seen_ids: set[str] = set()
    cleaned: list[dict] = []
    allowed_keys = {"id", "kind", "fresh"}
    for idx, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise BadInput(f"mục kho thứ {idx} phải là object {{id, kind, fresh}}")
        if set(entry.keys()) != allowed_keys:
            raise BadInput(f"mục kho thứ {idx} phải có đúng 3 khóa id, kind, fresh")
        item_id = entry["id"]
        if not isinstance(item_id, str) or (not allow_empty_id and not item_id):
            raise BadInput(f"id cá thể không hợp lệ: {item_id!r}")
        if item_id in seen_ids:
            raise BadInput(f"trùng id cá thể trong kho: {item_id}")
        seen_ids.add(item_id)
        kind = entry["kind"]
        if not isinstance(kind, str) or kind not in kinds:
            raise BadInput(f"nguyên liệu lạ trong kho: {kind!r}")
        fresh_frac = snap_fresh(entry["fresh"])
        cleaned.append({"id": item_id, "kind": kind, "fresh": fresh_to_json(fresh_frac)})
    return cleaned


def validate_items(raw, kinds=KINDS_V11) -> list[dict]:
    """Alias tương thích ngoài cho validate_item_instances ở Contract v1.2."""
    return validate_item_instances(raw, kinds=kinds)


def items_to_counts(items: list[dict]) -> dict[str, int]:
    """Đếm số lượng theo loại từ danh sách cá thể (dùng cho thống kê hoặc hiển thị)."""
    counts: dict[str, int] = {}
    for it in items:
        counts[it["kind"]] = counts.get(it["kind"], 0) + 1
    return dict(sorted(counts.items()))


def hold_to_items(hold: list[dict]) -> list[dict]:
    """Chuyển giỏ cá thể thành danh sách chuẩn hóa sắp theo id_key để xuất kho."""
    serialized = [serialize_item(it) for it in hold]
    return sort_by_id(serialized, key=lambda x: x["id"])


def read_inventory(path: str, kinds=KINDS_V11) -> list[dict]:
    """Đọc và kiểm tra schema file kho v1.2 ({"items": [{id, kind, fresh}, ...]})."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError as exc:
        raise BadInput(f"không thấy file kho: {path}") from exc
    except json.JSONDecodeError as exc:
        raise BadInput(f"file kho không phải JSON hợp lệ: {exc}") from exc

    if not isinstance(data, dict) or set(data.keys()) != {"items"}:
        raise BadInput("file kho phải có đúng khóa gốc 'items'")
    return validate_item_instances(data["items"], kinds=kinds)


def write_inventory(path: str, items: list[dict], kinds=KINDS_V11) -> None:
    """Ghi nguyên tử file kho v1.2 (sắp theo id, file tạm cùng thư mục rồi os.replace)."""
    validated = validate_item_instances(items, kinds=kinds)
    ordered = sort_by_id(validated, key=lambda x: x["id"])
    payload = json.dumps({"items": ordered}, ensure_ascii=False, separators=(",", ":"))
    abs_path = os.path.abspath(path)
    parent = os.path.dirname(abs_path)
    os.makedirs(parent, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".inv_", suffix=".tmp", dir=parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, abs_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
