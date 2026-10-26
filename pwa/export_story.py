from __future__ import annotations

import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PWA_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import main as story

payload = {
    "title": story.APP_NAME,
    "subtitle": story.SUBTITLE,
    "arcs": list(story.ARCS),
    "chapters": [asdict(chapter) for chapter in story.CHAPTERS],
    "scenes": {scene_id: asdict(scene) for scene_id, scene in story.STORY.items()},
}
(PWA_ROOT / "story.json").write_text(
    json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
    encoding="utf-8",
)

for folder in ("backgrounds", "characters"):
    shutil.copytree(ROOT / "assets" / folder, PWA_ROOT / "assets" / folder, dirs_exist_ok=True)
    icon_path = ROOT / "assets" / "game_icon.png"
    icon = Image.open(icon_path).convert("RGBA")
    icon.resize((192, 192), Image.Resampling.LANCZOS).save(PWA_ROOT / "assets" / "icon-192.png")
    icon.save(PWA_ROOT / "assets" / "icon-512.png")
    print("Exported story and image assets for the installable web app.")
