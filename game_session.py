"""Platform-neutral story progression shared by the web and Android apps."""

from __future__ import annotations

import json
from typing import Any

import main as story


class GameSession:
    def __init__(self) -> None:
        self.current_scene: str | None = None
        self.line_index = 0
        self.flags = {
            "bond": 0,
            "peace": 0,
            "resolve": 0,
            "family_final": 0,
            "reputation": 0,
        }
        self.highest_chapter = 0
        self.temp_lines: tuple[story.Line, ...] | None = None
        self.temp_index = 0
        self.pending_next_scene: str | None = None

    @property
    def scene(self) -> story.Scene | None:
        return story.STORY.get(self.current_scene) if self.current_scene else None

    @property
    def is_in_story(self) -> bool:
        return self.current_scene is not None

    @property
    def active_line(self) -> story.Line | None:
        scene = self.scene
        if self.temp_lines:
            return self.temp_lines[min(self.temp_index, len(self.temp_lines) - 1)]
        if scene:
            return scene.lines[min(self.line_index, len(scene.lines) - 1)]
        return None

    @property
    def choices(self) -> tuple[story.Choice, ...]:
        scene = self.scene
        if (
            scene
            and not self.temp_lines
            and scene.choices
            and self.line_index >= len(scene.lines) - 1
        ):
            return scene.choices
        return ()

    def current_text(self) -> str:
        line = self.active_line
        if line is None:
            return ""
        text = line.text
        if isinstance(text, str):
            return text
        reputation = self.flags.get("reputation", 0)
        return text[0] if reputation >= 2 else text[2] if reputation <= -2 else text[1]

    def new_game(self) -> None:
        self.current_scene = "summoning"
        self.line_index = 0
        self.flags = {name: 0 for name in self.flags}
        self.highest_chapter = 0
        self.temp_lines = None
        self.temp_index = 0
        self.pending_next_scene = None

    def start_chapter(self, index: int) -> bool:
        if not 0 <= index < len(story.CHAPTERS) or index > self.highest_chapter:
            return False
        self._enter_scene(story.CHAPTERS[index].scene_id)
        return True

    def _enter_scene(self, scene_id: str) -> None:
        if scene_id not in story.STORY:
            raise ValueError(f"Unknown scene: {scene_id}")
        self.current_scene = scene_id
        self.line_index = 0
        chapter_index = next(
            index for index, chapter in enumerate(story.CHAPTERS)
            if chapter.scene_id == scene_id
        )
        self.highest_chapter = max(self.highest_chapter, chapter_index)

    def _next_scene(self, target: str | None) -> None:
        if target == "ending_gate":
            target = story.ending_for(self.flags)
        if target is None:
            self.current_scene = None
            return
        self._enter_scene(target)

    def advance(self) -> None:
        scene = self.scene
        if scene is None:
            return
        if self.temp_lines:
            self.temp_index += 1
            if self.temp_index >= len(self.temp_lines):
                target = self.pending_next_scene
                self.temp_lines = None
                self.temp_index = 0
                self.pending_next_scene = None
                self._next_scene(target)
            return
        if self.choices:
            return
        if self.line_index < len(scene.lines) - 1:
            self.line_index += 1
        elif scene.next_scene is not None:
            self._next_scene(scene.next_scene)
        elif scene.ending:
            self.current_scene = None

    def choose(self, index: int) -> bool:
        choices = self.choices
        if not 0 <= index < len(choices):
            return False
        choice = choices[index]
        for name, value in choice.effects.items():
            self.flags[name] = self.flags.get(name, 0) + value
        if choice.outcome_lines:
            self.temp_lines = choice.outcome_lines
            self.temp_index = 0
            self.pending_next_scene = choice.next_scene
        else:
            self._next_scene(choice.next_scene)
        return True

    def save_json(self) -> str:
        if not self.current_scene or self.temp_lines:
            raise ValueError("Save between dialogue lines in an active scene.")
        data = {
            "version": story.SAVE_VERSION,
            "current_scene": self.current_scene,
            "line_index": self.line_index,
            "flags": self.flags,
            "highest_chapter": self.highest_chapter,
        }
        return json.dumps(data, ensure_ascii=False)

    def load_json(self, contents: str) -> None:
        data: dict[str, Any] = json.loads(contents)
        scene_id = data["current_scene"]
        line_index = data["line_index"]
        flags = data["flags"]
        highest_chapter = data.get("highest_chapter", 0)
        if scene_id not in story.STORY or not isinstance(line_index, int):
            raise ValueError("Invalid save data.")
        if not 0 <= line_index < len(story.STORY[scene_id].lines):
            raise ValueError("Invalid dialogue position in save data.")
        if not isinstance(flags, dict) or any(
            key not in self.flags or not isinstance(value, int)
            for key, value in flags.items()
        ):
            raise ValueError("Invalid story flags in save data.")
        if (
            not isinstance(highest_chapter, int)
            or not 0 <= highest_chapter < len(story.CHAPTERS)
        ):
            raise ValueError("Invalid chapter progress in save data.")
        self.current_scene = scene_id
        self.line_index = line_index
        self.flags = {**{name: 0 for name in self.flags}, **flags}
        scene_chapter = next(
            index for index, chapter in enumerate(story.CHAPTERS)
            if chapter.scene_id == scene_id
        )
        self.highest_chapter = max(highest_chapter, scene_chapter)
        self.temp_lines = None
        self.temp_index = 0
        self.pending_next_scene = None
