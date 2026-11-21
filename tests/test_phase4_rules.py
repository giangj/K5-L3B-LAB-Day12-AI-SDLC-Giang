"""Bộ kiểm thử chấp nhận (Acceptance Criteria) cho Phase 4 — Contract v1.3 & Release v1.0.0.

Kiểm tra:
- AC-P4-01: Contract v1.3 schema (contract_version: "1.3", bench_cmd, soak_cmd)
- AC-P4-02: bench_cmd CLI (exit code 2 khi thiếu tham số, tạo bench.json đủ 5 trường, đạt ngưỡng fps/load)
- AC-P4-03: soak_cmd CLI (exit code 2 khi thiếu tham số, hoàn tất nhiều ngày không crash, tất định theo seed)
- AC-P4-04: Cảnh báo dễ nhận biết (3 cảnh báo chữ + biểu tượng) và chế độ tương phản cao trong UI
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

from chonoi import CONTRACT_VERSION
from chonoi.contract import load_contract
from chonoi.errors import BadInput


class TestPhase4Rules(unittest.TestCase):
    def test_ac_p4_01_contract_v13_schema(self):
        """AC-P4-01: Contract v1.3 khai đúng contract_version: '1.3', bench_cmd và soak_cmd."""
        self.assertEqual(CONTRACT_VERSION, "1.3")
        raw = load_contract("game.contract.json")
        self.assertEqual(raw.get("contract_version"), "1.3")
        self.assertIn("bench_cmd", raw)
        self.assertIn("soak_cmd", raw)
        self.assertTrue(isinstance(raw["bench_cmd"], str) and len(raw["bench_cmd"]) > 0)
        self.assertTrue(isinstance(raw["soak_cmd"], str) and len(raw["soak_cmd"]) > 0)

    def test_ac_p4_02_bench_cmd_cli_and_metrics(self):
        """AC-P4-02: bench_cmd CLI bắt buộc các cờ, xuất đủ 5 trường JSON và thỏa ngưỡng."""
        # 1. Gọi thiếu tham số -> exit 2
        cmd_fail = [sys.executable, "-m", "chonoi.bench", "--seed", "42"]
        res_fail = subprocess.run(cmd_fail, capture_output=True, text=True)
        self.assertEqual(res_fail.returncode, 2, f"Expected exit 2 on missing args, got {res_fail.returncode}")

        # 2. Chạy bench ngắn (0.5s duration, 0.1s warmup) để test CLI & schema
        with tempfile.TemporaryDirectory() as td:
            out_json = os.path.join(td, "bench.json")
            cmd_ok = [
                sys.executable,
                "-m",
                "chonoi.bench",
                "--seed",
                "42",
                "--duration",
                "0.5",
                "--warmup",
                "0.1",
                "--out",
                out_json,
            ]
            res_ok = subprocess.run(cmd_ok, capture_output=True, text=True)
            self.assertEqual(res_ok.returncode, 0, f"bench failed: {res_ok.stderr}")
            self.assertTrue(os.path.exists(out_json))

            with open(out_json, encoding="utf-8") as f:
                data = json.load(f)

            # 5 trường bắt buộc theo đặc tả Contract v1.3
            for key in ("avg_fps", "p1_low_fps", "frames", "measured_s", "load_ms"):
                self.assertIn(key, data, f"Missing required field {key} in bench.json")
                self.assertIsInstance(data[key], (int, float))

            # Ngưỡng hiệu năng
            self.assertGreaterEqual(data["avg_fps"], 60.0, f"avg_fps {data['avg_fps']} < 60")
            self.assertGreaterEqual(data["p1_low_fps"], 30.0, f"p1_low_fps {data['p1_low_fps']} < 30")
            self.assertLessEqual(data["load_ms"], 10000.0, f"load_ms {data['load_ms']} > 10000")
            self.assertGreater(data["frames"], 0)

    def test_ac_p4_03_soak_cmd_cli_and_multiday_determinism(self):
        """AC-P4-03: soak_cmd CLI bắt buộc cờ, chạy multi-day không crash và tất định."""
        # 1. Thiếu tham số -> exit 2
        cmd_fail = [sys.executable, "-m", "chonoi.soak", "--seed", "7"]
        res_fail = subprocess.run(cmd_fail, capture_output=True, text=True)
        self.assertEqual(res_fail.returncode, 2, f"Expected exit 2 on missing args, got {res_fail.returncode}")

        # 2. Chạy soak 2 ngày hai lần cùng seed 7 -> kết quả khớp 100%
        with tempfile.TemporaryDirectory() as td:
            out1 = os.path.join(td, "soak1.json")
            out2 = os.path.join(td, "soak2.json")
            cmd = [sys.executable, "-m", "chonoi.soak", "--seed", "7", "--days", "2"]

            res1 = subprocess.run(cmd + ["--out", out1], capture_output=True, text=True)
            self.assertEqual(res1.returncode, 0, f"soak1 failed: {res1.stderr}")

            res2 = subprocess.run(cmd + ["--out", out2], capture_output=True, text=True)
            self.assertEqual(res2.returncode, 0, f"soak2 failed: {res2.stderr}")

            with open(out1, encoding="utf-8") as f:
                d1 = json.load(f)
            with open(out2, encoding="utf-8") as f:
                d2 = json.load(f)

            for key in ("days", "days_completed", "crashes", "results", "duration_s"):
                self.assertIn(key, d1)

            self.assertEqual(d1["days"], 2)
            self.assertEqual(d1["days_completed"], 2)
            self.assertEqual(d1["crashes"], 0)
            self.assertEqual(len(d1["results"]), 2)

            # Tất định giữa hai lần chạy
            self.assertEqual(d1["results"], d2["results"])

    def test_ac_p4_04_accessible_warnings_and_high_contrast(self):
        """AC-P4-04: Web UI có đủ 3 cảnh báo bằng chữ/biểu tượng và hỗ trợ chế độ tương phản cao."""
        html_path = os.path.join("chonoi", "web", "index.html")
        self.assertTrue(os.path.exists(html_path))
        with open(html_path, encoding="utf-8") as f:
            html = f.read()

        # 1. Cảnh báo thủy quái gần (chữ + biểu tượng)
        self.assertTrue(
            "THỦY QUÁI GẦN" in html or "Thủy quái" in html,
            "Missing monster near warning text",
        )
        self.assertIn("⚠", html, "Missing warning icon ⚠")

        # 2. Cảnh báo oxy sắp hết
        self.assertTrue(
            "OXY SẮP HẾT" in html or "HẾT HƠI" in html,
            "Missing low oxygen warning text",
        )

        # 3. Cảnh báo khách sắp giận
        self.assertTrue(
            "KHÁCH SẮP GIẬN" in html or "SẮP GIẬN" in html,
            "Missing customer angry warning text",
        )

        # 4. Chế độ tương phản cao (High Contrast)
        self.assertIn("high-contrast", html)
        self.assertIn("Tương phản cao", html)
        # Phím tắt H
        self.assertTrue('"h"' in html or "'h'" in html)


if __name__ == "__main__":
    unittest.main()
