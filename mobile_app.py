import os
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.image import Image
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.audio import SoundLoader

# Set a dark background color for the app
Window.clearcolor = (0.05, 0.05, 0.05, 1)


class SplashScreen(Screen):
    def __init__(self, **kwargs):
        super(SplashScreen, self).__init__(**kwargs)

        layout = FloatLayout()

        # Displays your logo.png for 3 seconds
        self.logo = Image(
            source='logo.png',
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(0.8, 0.8),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )

        layout.add_widget(self.logo)
        self.add_widget(layout)

        # Wait 3 seconds, then switch to the game screen
        Clock.schedule_once(self.switch_to_game, 3.0)

    def switch_to_game(self, dt):
        self.manager.current = 'game'


class GameScreen(Screen):
    def __init__(self, **kwargs):
        super(GameScreen, self).__init__(**kwargs)

        # --- MUSIC & STORY STATE ---
        self.current_music = None
        self.current_chapter = 1  # Start at Chapter 1

        # Play the initial music track (safe)
        self.play_music(self.current_chapter)

        # --- LAYOUT ---
        root = FloatLayout()

        # --- DIALOGUE BOX ---
        dialogue_box = BoxLayout(
            orientation='vertical',
            size_hint=(1, 0.35),
            pos_hint={'x': 0, 'y': 0},
            padding=15,
            spacing=10
        )

        self.dialogue_label = Label(
            text="NARRATION\n\nInstead of a towering, armored warrior, a young woman stands in the center of the circle. She is wearing a simple, black-and-white maid's uniform, holding a feather duster like a sword. Her name is Mika Amanogawa.",
            halign='left',
            valign='top',
            size_hint_y=0.8,
            font_size='16sp'
        )
        # Forces the text to wrap to the next line on mobile screens
        self.dialogue_label.bind(size=self.dialogue_label.setter('text_size'))

        dialogue_box.add_widget(self.dialogue_label)

        # --- CONTINUE BUTTON ---
        self.continue_btn = Button(
            text="Continue",
            size_hint_y=0.2,
            background_color=(0.2, 0.2, 0.2, 1),
            font_size='18sp'
        )

        # When clicked, trigger the next_chapter function
        self.continue_btn.bind(on_release=self.next_chapter)

        dialogue_box.add_widget(self.continue_btn)

        root.add_widget(dialogue_box)
        self.add_widget(root)

    def next_chapter(self, instance):
        # Check if we have reached the last chapter
        if self.current_chapter < 34:
            self.current_chapter += 1
            self.play_music(self.current_chapter)
            print(f"Advanced to Chapter {self.current_chapter}")

            # Optional: Update the text on screen to show progress
            self.dialogue_label.text = (
                f"NARRATION\n\nYou have advanced to Chapter {self.current_chapter}."
                "\n\n(Music has automatically changed to the next track)."
            )
        else:
            print("You have reached the end of Chapter 34!")

    def play_music(self, chapter_number):
        """Crash-safe chapter music loading (WAV-first for Android stability)."""
        # 1. Stop and unload currently playing music to save phone RAM
        if self.current_music:
            try:
                self.current_music.stop()
                self.current_music.unload()
            except Exception as e:
                print(f"Audio stop error: {e}")
            self.current_music = None

        # 2. Format chapter number (e.g., 1 becomes "01", 34 becomes "34")
        chapter_str = f"{chapter_number:02d}"

        # 3. Prefer .wav (more reliable on Android), fall back to .mp3
        base_path = os.path.join('assets', 'chapter_music')
        candidates = [
            os.path.join(base_path, f'chapter_{chapter_str}.wav'),
            os.path.join(base_path, f'chapter_{chapter_str}.mp3'),
        ]
        final_path = next((p for p in candidates if os.path.exists(p)), None)

        if not final_path:
            print(f"No music file found for chapter {chapter_number}")
            return

        # 4. Load and play (wrapped in try/except)
        try:
            self.current_music = SoundLoader.load(final_path)
            if self.current_music:
                self.current_music.loop = True
                self.current_music.play()
                print(f"Now playing: {final_path}")
            else:
                print(f"SoundLoader returned None for {final_path}")
        except Exception as e:
            print(f"Audio load error for {final_path}: {e}")
            self.current_music = None


class EchoesApp(App):
    def build(self):
        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(SplashScreen(name='splash'))
        sm.add_widget(GameScreen(name='game'))
        return sm


if __name__ == '__main__':
    EchoesApp().run()
