"""Smoke tests for the sandbox beta helper; uses only Python's standard library."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "sandbox_beta" / "floorplan_session.py"
SPEC = importlib.util.spec_from_file_location("floorplan_session", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class SandboxCalibrationTests(unittest.TestCase):
    def test_scale_for_known_dimension(self):
        self.assertAlmostEqual(module.calibration_scale((0, 0), (600, 0), 3000), 5.0)

    def test_pixel_to_mm_y_axis(self):
        self.assertEqual(module.pixel_to_mm((200, 40), (100, 100), 5), {"x": 500.0, "y": 300.0})

    def test_rejects_zero_pixel_length(self):
        with self.assertRaises(ValueError):
            module.calibration_scale((15, 15), (15, 15), 1000)

    def test_calibration_does_not_mutate_input(self):
        draft = {"title": "test", "source_image": "plan.png", "walls": []}
        calibrated = module.apply_calibration(draft, (10, 20), (110, 20), 2000)
        self.assertNotIn("image_mm_per_pixel", draft)
        self.assertEqual(calibrated["image_mm_per_pixel"], 20.0)
        self.assertEqual((calibrated["image_origin_pixel_x"], calibrated["image_origin_pixel_y"]), (10.0, 20.0))

    def test_add_wall_and_room(self):
        project = {
            "title": "test", "source_image": "plan.png", "image_mm_per_pixel": 10.0,
            "image_origin_pixel_x": 0, "image_origin_pixel_y": 100,
            "walls": [], "openings": [], "rooms": [], "symbols": []
        }
        wall = module.add_wall_from_pixels(project, "wall-1", (0, 100), (300, 100), role="interior")
        self.assertEqual(wall["start"], {"x": 0.0, "y": 0.0})
        self.assertEqual(wall["end"], {"x": 3000.0, "y": 0.0})
        room = module.add_room_from_pixels(project, "room-1", "Pokój", [(0, 100), (300, 100), (300, 0), (0, 0)])
        self.assertEqual(len(room["vertices"]), 4)
        with self.assertRaises(ValueError):
            module.add_wall_from_pixels(project, "wall-1", (0, 0), (1, 1))

    def test_initialize_image_session(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = root / "scan.png"
            original.write_bytes(b"test raster bytes")
            result = module.initialize_session(original, root / "workspace")
            project = json.loads(Path(result["project_json"]).read_text(encoding="utf-8"))
            self.assertTrue(Path(result["source_raster"]).is_file())
            self.assertTrue(original.is_file())
            self.assertEqual(project["source_image"], "scan.png")
            self.assertNotIn("image_mm_per_pixel", project)
            self.assertEqual(project["walls"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
