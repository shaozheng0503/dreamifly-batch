import json
import os
import tempfile
import unittest

import dreamify


class DreamifyParsingTests(unittest.TestCase):
    def test_parse_inline_prompt(self):
        prompt, overrides = dreamify.parse_prompt_line(
            "a cat | model=Z-Image-Turbo | 16:9 | x2 | seed=123 | neg=blurry"
        )
        self.assertEqual(prompt, "a cat")
        self.assertEqual(overrides["model"], "Z-Image-Turbo")
        self.assertEqual(overrides["aspectRatio"], "16:9")
        self.assertEqual(overrides["batch_size"], 2)
        self.assertEqual(overrides["seed"], 123)
        self.assertEqual(overrides["negative_prompt"], "blurry")

    def test_jsonl_prompt_queue(self):
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
            f.write(json.dumps({
                "prompt": "a neon cat",
                "model": "Z-Image-Turbo",
                "aspectRatio": "16:9",
                "batch_size": 2,
            }) + "\n")
            path = f.name
        try:
            _, pending = dreamify.load_prompt_entries(path)
            self.assertEqual(len(pending), 1)
            self.assertIn("model=Z-Image-Turbo", pending[0][1])
            self.assertIn("16:9", pending[0][1])
            self.assertIn("x2", pending[0][1])
        finally:
            os.unlink(path)

    def test_validate_detects_missing_image_for_i2i(self):
        cfg = {"model": "Qwen-Image-Edit", "width": 1024, "height": 1024, "aspectRatio": "1:1", "batch_size": 1}
        cli = {"model": None, "style": None, "aspectRatio": None, "width": None, "height": None, "batch_size": None}
        rows = dreamify.analyze_queue(cfg, cli, pending=[(0, "edit this, add snow | model=Qwen-Image-Edit")])
        self.assertTrue(rows[0]["issues"])

    def test_estimate_groups_by_model(self):
        cfg = {"model": "Z-Image-Turbo", "width": 1024, "height": 1024, "aspectRatio": "1:1", "batch_size": 1}
        cli = {"model": None, "style": None, "aspectRatio": None, "width": None, "height": None, "batch_size": None}
        rows = dreamify.analyze_queue(cfg, cli, pending=[
            (0, "a cat | model=Z-Image-Turbo"),
            (1, "a dog | model=Wai-SDXL-V150"),
        ])
        summary = dreamify.summarize_estimate(rows)
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["by_model"]["Z-Image-Turbo"], 1)
        self.assertEqual(summary["by_model"]["Wai-SDXL-V150"], 1)


if __name__ == "__main__":
    unittest.main()
