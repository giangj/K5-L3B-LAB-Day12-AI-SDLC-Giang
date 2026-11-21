"""Benchmark có render cảnh buổi sáng 1280x720 bằng thư viện chuẩn Python (Contract v1.3)."""

import argparse
import json
import math
import os
import struct
import sys
import tempfile
import time
import zlib

from .contract import load_contract
from .errors import BadInput
from .inputs import InputPlayer
from .runner import Session

WIDTH = 1280
HEIGHT = 720
ROW_STRIDE = WIDTH * 3

KIND_RGB = {
    "ca_linh": (214, 230, 242),
    "ca_loc": (124, 154, 82),
    "ca_keo": (217, 160, 102),
    "bong_dien_dien": (242, 194, 48),
    "bong_sung": (232, 121, 156),
    "keo_neo": (143, 207, 107),
}

# Bảng font bitmap 5x7 tối giản cho HUD trên ảnh render 1280x720
FONT_5X7 = {
    "0": (0x1E, 0x23, 0x25, 0x29, 0x31, 0x21, 0x1E),
    "1": (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x1F),
    "2": (0x1E, 0x21, 0x01, 0x0E, 0x10, 0x20, 0x3F),
    "3": (0x3E, 0x01, 0x01, 0x1E, 0x01, 0x01, 0x3E),
    "4": (0x02, 0x06, 0x0A, 0x12, 0x3F, 0x02, 0x02),
    "5": (0x3F, 0x20, 0x3E, 0x01, 0x01, 0x21, 0x1E),
    "6": (0x0E, 0x10, 0x20, 0x3E, 0x21, 0x21, 0x1E),
    "7": (0x3F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    "8": (0x1E, 0x21, 0x21, 0x1E, 0x21, 0x21, 0x1E),
    "9": (0x1E, 0x21, 0x21, 0x1F, 0x01, 0x02, 0x1C),
    ":": (0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x0C, 0x00),
    "/": (0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x00),
    ".": (0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C),
    "-": (0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00),
    " ": (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00),
    "A": (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "B": (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    "C": (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    "D": (0x1C, 0x12, 0x11, 0x11, 0x11, 0x12, 0x1C),
    "E": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    "F": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    "G": (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
    "H": (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "I": (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "K": (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    "L": (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    "M": (0x11, 0x1B, 0x15, 0x11, 0x11, 0x11, 0x11),
    "N": (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    "O": (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "P": (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    "R": (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    "S": (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    "T": (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    "U": (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "X": (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    "Y": (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
}


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write(f"lỗi: {message}\n")
        sys.exit(2)


def _fill_rect(buf: bytearray, x0: int, y0: int, w: int, h: int, rgb: tuple[int, int, int]) -> None:
    x1 = max(0, x0)
    y1 = max(0, y0)
    x2 = min(WIDTH, x0 + w)
    y2 = min(HEIGHT, y0 + h)
    if x1 >= x2 or y1 >= y2:
        return
    span = bytes(rgb) * (x2 - x1)
    span_len = len(span)
    base = y1 * ROW_STRIDE + x1 * 3
    for _ in range(y1, y2):
        buf[base : base + span_len] = span
        base += ROW_STRIDE


def _fill_circle(buf: bytearray, cx: int, cy: int, rad: int, rgb: tuple[int, int, int]) -> None:
    r2 = rad * rad
    col_b = bytes(rgb)
    for dy in range(-rad, rad + 1):
        py = cy + dy
        if py < 0 or py >= HEIGHT:
            continue
        dx = int(math.isqrt(max(0, r2 - dy * dy)))
        x1 = max(0, cx - dx)
        x2 = min(WIDTH, cx + dx + 1)
        if x1 < x2:
            span = col_b * (x2 - x1)
            off = py * ROW_STRIDE + x1 * 3
            buf[off : off + len(span)] = span


def _stroke_rect(buf: bytearray, x0: int, y0: int, w: int, h: int, t: int, rgb: tuple[int, int, int]) -> None:
    _fill_rect(buf, x0, y0, w, t, rgb)
    _fill_rect(buf, x0, y0 + h - t, w, t, rgb)
    _fill_rect(buf, x0, y0, t, h, rgb)
    _fill_rect(buf, x0 + w - t, y0, t, h, rgb)


def _draw_text(buf: bytearray, msg: str, x: int, y: int, scale: int, rgb: tuple[int, int, int]) -> None:
    cx = x
    for ch in msg.upper():
        rows = FONT_5X7.get(ch)
        if rows:
            for r_idx, mask in enumerate(rows):
                for c_idx in range(6):
                    if mask & (1 << (5 - c_idx)):
                        _fill_rect(buf, cx + c_idx * scale, y + r_idx * scale, scale, scale, rgb)
        cx += 6 * scale


def _build_background() -> bytearray:
    """Tạo sẵn nền bầu trời bình minh & gradient sông nước 1280x720."""
    bg = bytearray(WIDTH * HEIGHT * 3)
    hud_top = 84
    sky_h = 90
    water_top = hud_top + sky_h
    water_bot = HEIGHT - 76

    for y in range(HEIGHT):
        if y < hud_top:
            rgb = (18, 25, 33)
        elif y < water_top:
            t = (y - hud_top) / max(1, sky_h)
            rgb = (int(246 + t), int(178 + 52 * t), int(127 + 69 * t))
        elif y < water_bot:
            t = (y - water_top) / max(1, water_bot - water_top)
            rgb = (int(78 - 68 * t), int(167 - 135 * t), int(198 - 150 * t))
        else:
            rgb = (16, 22, 28)
        buf_row = bytes(rgb) * WIDTH
        off = y * ROW_STRIDE
        bg[off : off + ROW_STRIDE] = buf_row

    # Mặt nước trắng và các đường kẻ độ sâu 5m..30m
    _fill_rect(bg, 0, water_top, WIDTH, 3, (255, 245, 225))
    scale_y = (water_bot - water_top) / 30.0
    for d in range(5, 31, 5):
        dy = int(water_top + d * scale_y)
        _fill_rect(bg, 24, dy, WIDTH - 48, 1, (48, 92, 114))
        _draw_text(bg, f"{d}M", 30, dy - 16, 2, (165, 210, 224))
    return bg


class GatherRenderer:
    """Bộ dựng hình 1280x720 cho cảnh buổi sáng lõi."""

    def __init__(self, tuning: dict):
        self.t = tuning["gather"]
        self.bg = _build_background()
        self.top_bar_h = 84
        self.water_top = 174
        self.water_bot = HEIGHT - 76
        bx_lo, bx_hi = self.t["bounds"]["x"]
        bd_lo, bd_hi = self.t["bounds"]["d"]
        self.pad_x = 32
        self.sx = (WIDTH - 2 * self.pad_x) / max(1.0, bx_hi - bx_lo)
        self.sd = (self.water_bot - self.water_top) / max(1.0, bd_hi - bd_lo)

    def _pt(self, pos) -> tuple[int, int]:
        return (int(self.pad_x + pos[0] * self.sx), int(self.water_top + pos[1] * self.sd))

    def render(self, snap: dict, tick_idx: int) -> bytearray:
        buf = self.bg.copy()

        # Hiệu ứng gợn sóng nhẹ mặc định trên mặt nước
        shimmer = int((tick_idx * 3) % 80)
        for wx in range(shimmer, WIDTH - 60, 120):
            _fill_rect(buf, wx, self.water_top + 6, 36, 2, (196, 232, 245))

        # Bến nhà bè
        dx, dy = self._pt(self.t["dock_pos"])
        _fill_rect(buf, dx - 22, dy - 14, 44, 14, (141, 110, 75))
        _fill_rect(buf, dx - 26, dy - 26, 52, 12, (200, 90, 50))
        _draw_text(buf, "BEN", dx - 18, dy - 42, 2, (83, 49, 24))

        # Nút hái trên mặt nước
        for n in snap.get("nodes", []):
            nx, ny = self._pt(n["pos"])
            col = KIND_RGB.get(n["kind"], (180, 180, 180))
            if not n.get("ready", True):
                col = (col[0] // 2, col[1] // 2, col[2] // 2)
            _fill_circle(buf, nx, ny - 4, 10, col)

        # Đàn cá bơi dưới nước
        for f in snap.get("fish", []):
            fx, fy = self._pt(f["pos"])
            col = KIND_RGB.get(f["kind"], (200, 220, 240))
            _fill_rect(buf, fx - 12, fy - 6, 24, 12, col)
            _fill_rect(buf, fx - 18, fy - 4, 6, 8, col)

        # Cá Sấu Năm Chèo
        p = snap.get("player", {})
        ppos = p.get("pos", [2.0, 0.0])
        detect_r = self.t["monsters"]["species"]["ca_sau"]["detect_radius"]
        danger_near = False
        for m in snap.get("monsters", []):
            mx, my = self._pt(m["pos"])
            if math.hypot(ppos[0] - m["pos"][0], ppos[1] - m["pos"][1]) <= detect_r:
                danger_near = True
            col = (229, 57, 53) if m["state"] == "chase" else ((144, 164, 174) if m["state"] == "recoil" else (126, 87, 194))
            _fill_rect(buf, mx - 20, my - 9, 40, 18, col)
            _fill_rect(buf, mx + 12, my - 5, 5, 4, (255, 214, 0))

        # Út Sen đứng yên tại bến + nón lá
        px, py = self._pt(ppos)
        _fill_circle(buf, px, py, 10, (255, 138, 61))
        _fill_rect(buf, px - 12, py - 14, 24, 5, (245, 215, 150))

        # HUD trên: thời gian, oxy, HP & độ tươi giỏ
        secs_left = math.ceil(snap.get("time_left_ticks", 0) / 60)
        _draw_text(buf, f"DAY {snap.get('day', 1)} {secs_left // 60}:{secs_left % 60:02d}", 20, 26, 3, (246, 239, 226))
        omax = max(1, p.get("oxygen_max_ticks", 1800))
        oxy = p.get("oxygen_ticks", omax)
        _fill_rect(buf, 260, 24, 240, 24, (36, 48, 60))
        _fill_rect(buf, 262, 26, int(236 * oxy / omax), 20, (79, 195, 247))
        _draw_text(buf, f"OXY {math.ceil(oxy / 60)}S", 320, 29, 2, (255, 255, 255))
        _draw_text(buf, f"HP {p.get('hp', 3)}/{p.get('hp_max', 3)}", 530, 29, 3, (255, 107, 129))

        # Ô giỏ & thanh độ tươi bên dưới
        hold = snap.get("hold", [])
        cap = snap.get("hold_capacity", 12)
        _draw_text(buf, f"GIO {len(hold)}/{cap}", 20, HEIGHT - 50, 3, (232, 238, 242))
        for i in range(cap):
            sx0 = 210 + i * 40
            sy0 = HEIGHT - 54
            _fill_rect(buf, sx0, sy0, 32, 32, (48, 56, 66))
            if i < len(hold):
                it = hold[i]
                _fill_rect(buf, sx0 + 3, sy0 + 3, 26, 18, KIND_RGB.get(it["kind"], (200, 200, 200)))
                fr = max(0.0, min(1.0, float(it["fresh"]) / 100.0))
                fcol = (255, 23, 68) if it["fresh"] < 30 else (105, 240, 174)
                _fill_rect(buf, sx0 + 3, sy0 + 24, int(26 * fr), 5, fcol)

        if danger_near:
            _stroke_rect(buf, 3, 3, WIDTH - 6, HEIGHT - 6, 6, (156, 39, 176))
            _draw_text(buf, "THUY QUAI GAN", WIDTH // 2 - 110, 96, 3, (234, 128, 252))
        return buf


def write_rgb_png(path: str, width: int, height: int, rgb: bytearray) -> None:
    """Lưu khung RGB24 ra file PNG chuẩn chỉ bằng zlib & struct."""
    stride = width * 3
    raw = bytearray((stride + 1) * height)
    dst = 0
    src = 0
    for _ in range(height):
        raw[dst] = 0
        raw[dst + 1 : dst + 1 + stride] = rgb[src : src + stride]
        dst += stride + 1
        src += stride

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(raw), 6)) + chunk(b"IEND", b"")
    abs_p = os.path.abspath(path)
    os.makedirs(os.path.dirname(abs_p), exist_ok=True)
    with open(abs_p, "wb") as f:
        f.write(png)


def _write_json_atomic(path: str, obj: dict) -> None:
    abs_p = os.path.abspath(path)
    parent = os.path.dirname(abs_p)
    os.makedirs(parent, exist_ok=True)
    fd, tmp_p = tempfile.mkstemp(prefix=".bench_", suffix=".tmp", dir=parent)
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
    p = _Parser(prog="chonoi.bench")
    p.add_argument("--seed", required=True, type=int)
    p.add_argument("--duration", required=True, type=float)
    p.add_argument("--out", required=True)
    p.add_argument("--warmup", type=float, default=3.0)
    p.add_argument("--preview", default=None)
    a = p.parse_args(argv)
    if a.duration <= 0 or a.warmup < 0:
        sys.stderr.write("đầu vào sai: --duration phải > 0 và --warmup >= 0\n")
        return 2

    try:
        tuning = load_contract()["tuning"]
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2

    renderer = GatherRenderer(tuning)
    idle_inp = InputPlayer([]).advance(0)
    sess = Session("gather", tuning, {}, a.seed)

    # Khung hình đầu tiên -> đo load_ms
    last_buf = renderer.render(sess.snapshot(), 0)
    load_ms = round((time.perf_counter() - t0) * 1000.0, 2)

    tick_idx = 0
    warm_end = time.perf_counter() + a.warmup
    while time.perf_counter() < warm_end:
        if sess.done:
            sess = Session("gather", tuning, {}, a.seed)
        sess.step(idle_inp)
        tick_idx += 1
        last_buf = renderer.render(sess.snapshot(), tick_idx)

    frame_times: list[float] = []
    t_start = time.perf_counter()
    deadline = t_start + a.duration
    while time.perf_counter() < deadline:
        ft0 = time.perf_counter()
        if sess.done:
            sess = Session("gather", tuning, {}, a.seed)
        sess.step(idle_inp)
        tick_idx += 1
        last_buf = renderer.render(sess.snapshot(), tick_idx)
        frame_times.append(time.perf_counter() - ft0)
    measured_s = time.perf_counter() - t_start

    frames = len(frame_times)
    avg_fps = round(frames / measured_s, 2) if measured_s > 0 else 0.0
    slow_k = max(1, math.ceil(0.01 * frames))
    slowest = sorted(frame_times, reverse=True)[:slow_k]
    p1_low_fps = round(1.0 / (sum(slowest) / len(slowest)), 2)

    out_obj = {
        "avg_fps": avg_fps,
        "p1_low_fps": p1_low_fps,
        "frames": frames,
        "measured_s": round(measured_s, 4),
        "load_ms": load_ms,
    }
    _write_json_atomic(a.out, out_obj)
    if a.preview:
        write_rgb_png(a.preview, WIDTH, HEIGHT, last_buf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
