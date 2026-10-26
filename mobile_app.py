from __future__ import annotations

import json
from pathlib import Path

import main as story
from game_session import GameSession
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView


PALETTE = {
    "background": (0.035, 0.047, 0.063, 1),
    "panel": (0.07, 0.09, 0.12, 1),
    "gold": (0.77, 0.66, 0.47, 1),
    "text": (0.95, 0.92, 0.86, 1),
}


class AndroidNovelApp(App):
    title = f"{story.APP_NAME}: {story.SUBTITLE}"

    def build(self):
        Window.clearcolor = PALETTE["background"]
        self.session = GameSession()
        self.save_path = Path(self.user_data_dir) / "save.json"
        self.progress_path = Path(self.user_data_dir) / "progress.json"
        try:
            progress = json.loads(self.progress_path.read_text(encoding="utf-8"))
            highest_chapter = progress["highest_chapter"]
            if isinstance(highest_chapter, int) and 0 <= highest_chapter < len(story.CHAPTERS):
                self.session.highest_chapter = highest_chapter
        except FileNotFoundError:
            pass
        except (json.JSONDecodeError, KeyError, TypeError, OSError) as error:
            print(f"Could not load chapter progress: {error}")
        self.root_layout = BoxLayout(orientation="vertical", padding=14, spacing=10)
        self.show_home()
        return self.root_layout

    def _label(self, text, size=16, color=None, height=48, halign="left"):
        return Label(
            text=text,
            font_size=size,
            color=color or PALETTE["text"],
            halign=halign,
            valign="middle",
            text_size=(Window.width - 44, None),
            size_hint_y=None,
            height=height,
        )

    def _button(self, text, action, height=52, disabled=False):
        button = Button(
            text=text,
            size_hint_y=None,
            height=height,
            disabled=disabled,
            background_normal="",
            background_color=PALETTE["panel"],
            color=PALETTE["text"],
            halign="center",
            valign="middle",
        )
        button.bind(on_release=lambda _button: action())
        return button

    def _reset_view(self):
        self.root_layout.clear_widgets()

    def show_home(self):
        self._reset_view()
        self.root_layout.add_widget(self._label(story.APP_NAME, 24, PALETTE["gold"], height=72, halign="center"))
        self.root_layout.add_widget(self._label(story.SUBTITLE, 18, height=38, halign="center"))
        if self.save_path.exists():
            self.root_layout.add_widget(self._button("Continue saved game", self.load_game))
        self.root_layout.add_widget(self._button("Start new game", self.start_new_game))
        self.root_layout.add_widget(self._label("Unlocked chapters", 18, PALETTE["gold"]))
        scroll = ScrollView()
        chapter_list = BoxLayout(orientation="vertical", spacing=6, size_hint_y=None)
        chapter_list.bind(minimum_height=chapter_list.setter("height"))
        for index, chapter in enumerate(story.CHAPTERS):
            chapter_list.add_widget(self._button(
                f"{chapter.key} · {chapter.title}",
                lambda chapter_index=index: self.start_chapter(chapter_index),
                height=46,
                disabled=index > self.session.highest_chapter,
            ))
        scroll.add_widget(chapter_list)
        self.root_layout.add_widget(scroll)

    def start_new_game(self):
        self.session.new_game()
        self._persist_progress()
        self.show_story()

    def start_chapter(self, index):
        if self.session.start_chapter(index):
            self._persist_progress()
            self.show_story()

    def _persist_progress(self):
        try:
            self.progress_path.parent.mkdir(parents=True, exist_ok=True)
            self.progress_path.write_text(
                json.dumps({"highest_chapter": self.session.highest_chapter}),
                encoding="utf-8",
            )
        except OSError as error:
            print(f"Could not save chapter progress: {error}")

    def load_game(self):
        try:
            self.session.load_json(self.save_path.read_text(encoding="utf-8"))
            self._persist_progress()
            self.show_story()
        except (OSError, ValueError, KeyError, TypeError) as error:
            self._reset_view()
            self.root_layout.add_widget(self._label(f"Could not load save: {error}", height=90))
            self.root_layout.add_widget(self._button("Back", self.show_home))

    def save_game(self):
        try:
            self.save_path.parent.mkdir(parents=True, exist_ok=True)
            self.save_path.write_text(self.session.save_json(), encoding="utf-8")
            self.show_story("Game saved.")
        except (OSError, ValueError) as error:
            self.show_story(f"Could not save: {error}")

    def show_story(self, notice=""):
        self._reset_view()
        scene = self.session.scene
        if scene is None:
            self.show_home()
            return
        chapter = story.CHAPTER_BY_SCENE[self.session.current_scene]
        header = BoxLayout(size_hint_y=None, height=50, spacing=8)
        header.add_widget(self._button("Menu", self.show_home, height=46))
        header.add_widget(self._label(f"{chapter.key} · {chapter.title}", 16, PALETTE["gold"], height=46))
        header.add_widget(self._button("Save", self.save_game, height=46))
        self.root_layout.add_widget(header)

        backdrop = story.asset_path("assets", "backgrounds", f"{scene.backdrop}.png")
        if backdrop.is_file():
            self.root_layout.add_widget(Image(source=str(backdrop), size_hint_y=0.3, allow_stretch=True, keep_ratio=True))

        cast_row = BoxLayout(size_hint_y=0.38, spacing=6)
        for character in scene.cast:
            name = self._sprite_name(character)
            image_path = story.asset_path("assets", "characters", f"{name}.png")
            if image_path.is_file():
                cast_row.add_widget(Image(source=str(image_path), allow_stretch=True, keep_ratio=True))
        if cast_row.children:
            self.root_layout.add_widget(cast_row)

        line = self.session.active_line
        if line:
            self.root_layout.add_widget(self._label(
                line.speaker.upper().replace("_EVIL", ""),
                16,
                PALETTE["gold"],
                height=38,
            ))
            text_scroll = ScrollView(size_hint_y=0.28)
            text_scroll.add_widget(self._label(
                self.session.current_text(),
                18,
                height=max(110, len(self.session.current_text()) // 2),
            ))
            self.root_layout.add_widget(text_scroll)
        if notice:
            self.root_layout.add_widget(self._label(notice, 14, PALETTE["gold"], height=32))

        if self.session.choices:
            for index, choice in enumerate(self.session.choices):
                self.root_layout.add_widget(self._button(
                    choice.text,
                    lambda choice_index=index: self.choose(choice_index),
                    height=60,
                ))
        else:
            self.root_layout.add_widget(self._button("Continue", self.advance, height=54))

    @staticmethod
    def _sprite_name(character):
        if character == "Mika_Evil":
            return "Mika_Evil"
        for key, name in (
            ("Mika", "Mika"), ("Mallory", "Mallory"), ("King Galvath", "Galvath"),
            ("Lira", "Lira"), ("Gorthak", "Gorthak"), ("Shadow", "shadow"),
        ):
            if character.startswith(key):
                return name
        return character

    def advance(self):
        self.session.advance()
        self._persist_progress()
        self.show_story()

    def choose(self, index):
        self.session.choose(index)
        self._persist_progress()
        self.show_story()
