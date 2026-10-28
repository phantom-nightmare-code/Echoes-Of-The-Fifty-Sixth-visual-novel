import os
import sys
import re
import random
import math
import struct
import wave
import json
import datetime
import traceback

# --- ANDROID PATH FIX ---
# This forces Android to have valid paths before main.py loads, preventing the TypeError
if os.name == "posix":
    if not os.environ.get("XDG_DATA_HOME"):
        os.environ["XDG_DATA_HOME"] = os.path.abspath(".")
    if not os.environ.get("HOME"):
        os.environ["HOME"] = os.path.abspath(".")
# ------------------------

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.audio import SoundLoader
from kivy.core.image import Image as CoreImage
from kivy.graphics import Color, Rectangle, Ellipse, Line
from kivy.animation import Animation

# Import logic from main.py safely
try:
    from main import STORY, ending_for, resolve_text, CHAPTER_MUSIC, CHAPTER_BY_SCENE, CHAPTERS
except Exception as e:
    print("CRITICAL ERROR IMPORTING main.py:")
    traceback.print_exc()
    STORY = {}
    CHAPTER_MUSIC = {}
    CHAPTER_BY_SCENE = {}
    CHAPTERS = []
    def ending_for(flags): return "summoning"
    def resolve_text(text, flags): return str(text)

if not CHAPTER_MUSIC: CHAPTER_MUSIC = {}
if not CHAPTER_BY_SCENE: CHAPTER_BY_SCENE = {}

Window.clearcolor = (0.02, 0.02, 0.05, 1)

# Helper to safely get the save directory
def get_data_dir():
    try:
        app = App.get_running_app()
        d = app.user_data_dir if app else None
    except Exception:
        d = None
    if not d:
        d = os.path.abspath(".")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    return d

def find_asset(filename):
    if not filename: return None
    paths = [str(filename), os.path.join('assets', str(filename)), os.path.join('assets', 'images', str(filename))]
    for p in paths:
        try:
            if os.path.exists(p): return p
        except Exception:
            pass
    return None

# ---------------------------------------------------------
# 1. 8-BIT VOICE GENERATOR
# ---------------------------------------------------------
class EightBitVoice:
    def __init__(self, cache_dir):
        self.cache_dir = cache_dir if cache_dir else "."
        try: os.makedirs(self.cache_dir, exist_ok=True)
        except Exception: self.cache_dir = "."
        self.sounds = {}
        self.freqs = {
            "Mika": 600, "Mika Amanogawa": 600, "Mallory": 500, "Mallory Valerius": 500,
            "Lira": 550, "Lira Vanguard": 550, "King Galvath": 200, "King Galvath Valerius": 200,
            "Gorthak": 150, "Gorthak Stonefist": 150, "Shadow": 100, "Narration": 350, "Mika_Evil": 1400
        }

    def get_sound(self, speaker):
        if speaker in self.sounds: return self.sounds[speaker]
        freq = self.freqs.get(speaker, 400)
        try:
            filename = os.path.join(self.cache_dir, f"blip_{freq}.wav")
            if not os.path.exists(filename):
                sample_rate = 22050
                n_samples = int(sample_rate * 0.03)
                with wave.open(filename, 'w') as f:
                    f.setnchannels(1); f.setsampwidth(2); f.setframerate(sample_rate)
                    for i in range(n_samples):
                        val = 1.0 if math.sin(2 * math.pi * freq * (i/sample_rate)) > 0 else -1.0
                        progress = i / n_samples
                        env = 1.0 if progress < 0.8 else (1.0 - progress) * 5.0
                        f.writeframesraw(struct.pack('<h', int(val * env * 6000)))
            sound = SoundLoader.load(filename)
            if sound: self.sounds[speaker] = sound
            return sound
        except Exception: return None

    def play(self, speaker):
        sound = self.get_sound(speaker)
        if sound:
            try:
                sound.volume = App.get_running_app().voice_vol
                sound.play()
            except Exception: pass

# ---------------------------------------------------------
# 2. SAVE / LOAD SCREEN
# ---------------------------------------------------------
class SaveLoadScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mode = "load"
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        with self.layout.canvas.before:
            Color(0.05, 0.05, 0.1, 1)
            self.rect = Rectangle(size=self.layout.size, pos=self.layout.pos)
        self.layout.bind(size=lambda i, v: setattr(self.rect, 'size', v), pos=lambda i, v: setattr(self.rect, 'pos', v))

        self.title_label = Label(text="LOAD GAME", font_size='28sp', bold=True, size_hint_y=0.15, color=(0.8, 0.7, 0.5, 1))
        self.layout.add_widget(self.title_label)
        
        self.slots_layout = BoxLayout(orientation='vertical', spacing=10, size_hint_y=0.7)
        self.layout.add_widget(self.slots_layout)
        
        btn_back = Button(text="BACK", size_hint_y=0.15, background_color=(0.2, 0.25, 0.3, 1), font_size='18sp')
        btn_back.bind(on_release=lambda x: setattr(self.manager, 'current', 'menu' if self.mode == 'load' else 'game'))
        self.layout.add_widget(btn_back)
        self.add_widget(self.layout)

    def on_pre_enter(self, *args):
        self.title_label.text = "SAVE GAME" if self.mode == "save" else "LOAD GAME"
        self.update_slots()

    def update_slots(self):
        self.slots_layout.clear_widgets()
        for i in range(1, 4):
            try:
                path = os.path.join(get_data_dir(), f"save_{i}.json")
            except Exception:
                path = f"save_{i}.json"
                
            text = f"Slot {i}: Empty"
            color = (0.15, 0.15, 0.2, 1)
            
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f: data = json.load(f)
                    text = f"Slot {i}: {data.get('preview_title', 'Unknown')}\n{data.get('timestamp', '')}"
                    color = (0.2, 0.3, 0.4, 1)
                except Exception: text = f"Slot {i}: Corrupted"
            
            btn = Button(text=text, size_hint_y=None, height=80, background_color=color, font_size='16sp')
            btn.bind(on_release=lambda instance, slot=i: self.handle_slot(slot))
            self.slots_layout.add_widget(btn)

    def handle_slot(self, slot):
        path = os.path.join(get_data_dir(), f"save_{slot}.json")
        if self.mode == "save":
            self.manager.get_screen('game').save_game(slot)
            self.manager.current = 'game'
        elif os.path.exists(path):
            self.manager.get_screen('game').load_game(slot)
            self.manager.current = 'game'

# ---------------------------------------------------------
# 3. SPLASH, MAIN MENU, SETTINGS, CHAPTERS
# ---------------------------------------------------------
class SplashScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = FloatLayout()
        logo_path = find_asset('logo.png')
        if logo_path:
            logo = Image(source=logo_path, allow_stretch=True, keep_ratio=True, size_hint=(0.8, 0.8), pos_hint={'center_x': 0.5, 'center_y': 0.5})
            layout.add_widget(logo)
        else:
            lbl = Label(text="ECHOES OF THE FIFTY SIX WORLDS", font_size='24sp', bold=True, pos_hint={'center_x': 0.5, 'center_y': 0.5})
            layout.add_widget(lbl)
        self.add_widget(layout)
        Clock.schedule_once(self.go_to_menu, 3.0)

    def go_to_menu(self, dt):
        self.manager.current = 'menu'

class MainMenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = FloatLayout()
        
        with layout.canvas.before:
            Color(0.02, 0.02, 0.04, 1)
            self.bg = Rectangle(size=layout.size, pos=layout.pos)
            Color(0.65, 0.55, 0.35, 1)
            self.ring1 = Line(circle=(Window.width/2, Window.height*0.65, Window.height*0.3), width=1)
            self.ring2 = Line(circle=(Window.width/2, Window.height*0.65, Window.height*0.35), width=1, dash_offset=10, dash_length=5)
            self.line_h = Line(points=[Window.width*0.2, Window.height*0.65, Window.width*0.8, Window.height*0.65], width=1)
            self.line_v = Line(points=[Window.width/2, Window.height*0.3, Window.width/2, Window.height*1.0], width=1)

        layout.bind(size=self._update_canvas, pos=self._update_canvas)

        t1 = Label(text="ECHOES OF THE", font_size='18sp', color=(0.65, 0.55, 0.35, 1), pos_hint={'center_x': 0.5, 'center_y': 0.75})
        t2 = Label(text="FIFTY SIX WORLDS", font_size='42sp', bold=True, color=(0.95, 0.9, 0.8, 1), pos_hint={'center_x': 0.5, 'center_y': 0.68})
        t3 = Label(text="REQUIEM OF THE MAID", font_size='14sp', color=(0.65, 0.55, 0.35, 1), pos_hint={'center_x': 0.5, 'center_y': 0.62})
        layout.add_widget(t1); layout.add_widget(t2); layout.add_widget(t3)

        box = BoxLayout(orientation='vertical', size_hint=(0.5, 0.45), pos_hint={'center_x': 0.5, 'center_y': 0.3}, spacing=5)
        
        buttons = [
            ("START NEW STORY", self.start_game),
            ("CONTINUE", self.open_load),
            ("CHAPTER SELECT", lambda x: setattr(self.manager, 'current', 'chapters')),
            ("SOUNDTRACK", lambda x: setattr(self.manager, 'current', 'soundtrack')),
            ("SETTINGS", lambda x: setattr(self.manager, 'current', 'settings')),
            ("CREDITS", lambda x: setattr(self.manager, 'current', 'credits')),
            ("QUIT", App.get_running_app().stop)
        ]

        for text, action in buttons:
            btn = Button(text=text, background_color=(0.05, 0.08, 0.1, 1), font_size='16sp', size_hint_y=None, height=45)
            btn.bind(on_release=action)
            with btn.canvas.before:
                Color(0.65, 0.55, 0.35, 1)
                btn.border = Line(rectangle=(btn.x, btn.y, btn.width, btn.height), width=1)
            btn.bind(pos=lambda i, v: setattr(btn.border, 'rectangle', (i.x, i.y, i.width, i.height)),
                     size=lambda i, v: setattr(btn.border, 'rectangle', (i.x, i.y, i.width, i.height)))
            box.add_widget(btn)

        layout.add_widget(box)
        self.add_widget(layout)

    def _update_canvas(self, instance, value):
        self.bg.size = instance.size
        self.ring1.circle = (instance.width/2, instance.height*0.65, instance.height*0.3)
        self.ring2.circle = (instance.width/2, instance.height*0.65, instance.height*0.35)
        self.line_h.points = [instance.width*0.2, instance.height*0.65, instance.width*0.8, instance.height*0.65]
        self.line_v.points = [instance.width/2, instance.height*0.3, instance.width/2, instance.height*1.0]

    def on_enter(self):
        try: App.get_running_app().play_menu_music()
        except Exception: pass

    def start_game(self, instance):
        self.manager.current = 'game'
        self.manager.get_screen('game').reset_game()

    def open_load(self, instance):
        self.manager.get_screen('saveload').mode = 'load'
        self.manager.current = 'saveload'

class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = FloatLayout()
        layout.add_widget(Label(text="AUDIO SETTINGS", font_size='28sp', bold=True, color=(0.8, 0.7, 0.5, 1), pos_hint={'center_x': 0.5, 'center_y': 0.8}))
        
        layout.add_widget(Label(text="Music Volume", font_size='18sp', pos_hint={'center_x': 0.5, 'center_y': 0.6}))
        s1 = Slider(min=0, max=1, value=App.get_running_app().music_vol, pos_hint={'center_x': 0.5, 'center_y': 0.55}, size_hint_x=0.7)
        s1.bind(value=self.set_music_vol)
        layout.add_widget(s1)
        
        layout.add_widget(Label(text="Voice Volume", font_size='18sp', pos_hint={'center_x': 0.5, 'center_y': 0.45}))
        s2 = Slider(min=0, max=1, value=App.get_running_app().voice_vol, pos_hint={'center_x': 0.5, 'center_y': 0.4}, size_hint_x=0.7)
        s2.bind(value=self.set_voice_vol)
        layout.add_widget(s2)
        
        btn_back = Button(text="BACK", size_hint=(0.4, 0.1), pos_hint={'center_x': 0.5, 'center_y': 0.2}, background_color=(0.2, 0.25, 0.3, 1))
        btn_back.bind(on_release=lambda x: setattr(self.manager, 'current', 'menu'))
        layout.add_widget(btn_back)
        self.add_widget(layout)

    def set_music_vol(self, instance, value): App.get_running_app().set_music_volume(value)
    def set_voice_vol(self, instance, value): App.get_running_app().voice_vol = value

class ChapterSelectScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        layout.add_widget(Label(text="CHAPTER SELECT", font_size='24sp', bold=True, color=(0.8, 0.7, 0.5, 1), size_hint_y=0.1))
        
        scroll = ScrollView(size_hint_y=0.8)
        btn_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5)
        btn_layout.bind(minimum_height=btn_layout.setter('height'))
        
        for i, chap in enumerate(CHAPTERS):
            btn = Button(text=f"Chapter {chap.key}: {chap.title}", size_hint_y=None, height=50, background_color=(0.15, 0.15, 0.2, 1))
            btn.bind(on_release=lambda instance, idx=i: self.jump_to_chapter(idx))
            btn_layout.add_widget(btn)
            
        scroll.add_widget(btn_layout)
        layout.add_widget(scroll)
        
        btn_back = Button(text="BACK", size_hint_y=0.1, background_color=(0.2, 0.25, 0.3, 1))
        btn_back.bind(on_release=lambda x: setattr(self.manager, 'current', 'menu'))
        layout.add_widget(btn_back)
        self.add_widget(layout)

    def jump_to_chapter(self, index):
        game = self.manager.get_screen('game')
        game.reset_game()
        game.load_scene(CHAPTERS[index].scene_id)
        self.manager.current = 'game'

class SoundtrackScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=5)
        layout.add_widget(Label(text="SOUNDTRACK", font_size='24sp', bold=True, color=(0.8, 0.7, 0.5, 1), size_hint_y=0.1))
        
        scroll = ScrollView(size_hint_y=0.8)
        btn_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5)
        btn_layout.bind(minimum_height=btn_layout.setter('height'))
        
        for i, chap in enumerate(CHAPTERS):
            btn = Button(text=f"{chap.key} - {chap.title}", size_hint_y=None, height=40, background_color=(0.15, 0.15, 0.2, 1), font_size='14sp')
            btn.bind(on_release=lambda instance, idx=i: self.play_track(idx))
            btn_layout.add_widget(btn)
            
        scroll.add_widget(btn_layout)
        layout.add_widget(scroll)
        
        btn_back = Button(text="BACK", size_hint_y=0.1, background_color=(0.2, 0.25, 0.3, 1))
        btn_back.bind(on_release=lambda x: setattr(self.manager, 'current', 'menu'))
        layout.add_widget(btn_back)
        self.add_widget(layout)

    def play_track(self, index):
        try:
            track_path = CHAPTER_MUSIC.get(CHAPTERS[index].scene_id)
            if track_path:
                path_str = str(track_path).replace('.mp3', '.wav')
                if not os.path.exists(path_str) and os.path.exists(str(track_path)): path_str = str(track_path)
                App.get_running_app().play_music(path_str)
        except Exception: pass

class CreditsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = FloatLayout()
        layout.add_widget(Label(text="CREDITS", font_size='24sp', bold=True, color=(0.8, 0.7, 0.5, 1), pos_hint={'center_x': 0.5, 'center_y': 0.8}))
        layout.add_widget(Label(text="Story & Visual Novel\nPhantom Nightmare Developer", font_size='18sp', pos_hint={'center_x': 0.5, 'center_y': 0.6}, halign='center'))
        layout.add_widget(Label(text="Music\nPhantom Nightmare Developer", font_size='18sp', pos_hint={'center_x': 0.5, 'center_y': 0.4}, halign='center'))
        
        btn_back = Button(text="BACK", size_hint=(0.4, 0.1), pos_hint={'center_x': 0.5, 'center_y': 0.2}, background_color=(0.2, 0.25, 0.3, 1))
        btn_back.bind(on_release=lambda x: setattr(self.manager, 'current', 'menu'))
        layout.add_widget(btn_back)
        self.add_widget(layout)

# ---------------------------------------------------------
# 4. PARTICLE SYSTEM
# ---------------------------------------------------------
class ParticleSystem(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.particles = []
        self.particle_color = (1, 1, 1, 1)
        Clock.schedule_interval(self.update_particles, 1/60.0)

    def set_backdrop(self, backdrop):
        self.particles = []
        self.canvas.clear()
        if backdrop in ('winter', 'battle'): self.particle_color = (1, 1, 1, 1) if backdrop == 'winter' else (1, 0.6, 0, 1)
        elif backdrop == 'archive': self.particle_color = (0.8, 0.7, 0.5, 1)
        elif backdrop == 'garden': self.particle_color = (0.5, 1, 0.5, 1)
        else: return 

        for _ in range(50):
            self.particles.append({
                'x': random.random(), 'y': random.random(), 'dx': random.uniform(-0.01, 0.01),
                'dy': random.uniform(-0.02, -0.005) if backdrop != 'garden' else random.uniform(-0.01, 0.01),
                'size': random.uniform(0.005, 0.015)
            })

    def update_particles(self, dt):
        if not self.particles: return
        self.canvas.clear()
        with self.canvas:
            Color(*self.particle_color)
            for p in self.particles:
                p['x'] += p['dx']; p['y'] += p['dy']
                if p['y'] < 0: p['y'] = 1
                if p['y'] > 1: p['y'] = 0
                if p['x'] < 0: p['x'] = 1
                if p['x'] > 1: p['x'] = 0
                Ellipse(pos=(p['x'] * self.width, p['y'] * self.height), size=(p['size'] * self.width,)*2)

# ---------------------------------------------------------
# 5. GAME SCREEN
# ---------------------------------------------------------
class GameScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.voice = EightBitVoice(get_data_dir())
        
        self.full_text = ""; self.typing_idx = 0; self.typing_event = None; self.is_typing = False
        self.current_speaker = ""; self.auto_mode = False; self.skip_mode = False
        self.shake_event = None

        self.layout = FloatLayout()
        self.bg_image = Image(source='', allow_stretch=True, keep_ratio=False, size_hint=(1, 1))
        self.layout.add_widget(self.bg_image)
        self.particles = ParticleSystem(size_hint=(1, 1))
        self.layout.add_widget(self.particles)
        self.char_layer = FloatLayout(size_hint=(1, 1))
        self.layout.add_widget(self.char_layer)

        self.top_bar = BoxLayout(size_hint=(1, 0.07), pos_hint={'top': 1}, spacing=2, padding=5)
        with self.top_bar.canvas.before:
            Color(0.02, 0.03, 0.04, 0.95)
            self.top_rect = Rectangle(size=self.top_bar.size, pos=self.top_bar.pos)
        self.top_bar.bind(size=lambda i, v: setattr(self.top_rect, 'size', v), pos=lambda i, v: setattr(self.top_rect, 'pos', v))
        
        for text, action in [
            ("CHAPTERS", lambda x: setattr(self.manager, 'current', 'chapters')),
            ("AUTO", self.toggle_auto),
            ("SKIP", self.toggle_skip),
            ("LOG", lambda x: None),
            ("SETTINGS", lambda x: setattr(self.manager, 'current', 'settings')),
            ("SAVE", self.open_save),
            ("RESET", self.confirm_reset),
            ("MENU", lambda x: setattr(self.manager, 'current', 'menu'))
        ]:
            btn = Button(text=text, font_size='11sp', background_color=(0.05, 0.08, 0.1, 1), color=(0.85, 0.8, 0.7, 1))
            btn.bind(on_release=action)
            with btn.canvas.before:
                Color(0.65, 0.55, 0.35, 1)
                btn.border = Line(rectangle=(btn.x, btn.y, btn.width, btn.height), width=1)
            btn.bind(pos=lambda i, v, b=btn: setattr(b.border, 'rectangle', (i.x, i.y, i.width, i.height)),
                     size=lambda i, v, b=btn: setattr(b.border, 'rectangle', (i.x, i.y, i.width, i.height)))
            self.top_bar.add_widget(btn)
        self.layout.add_widget(self.top_bar)

        self.dialog_box = BoxLayout(orientation='vertical', size_hint=(1, 0.4), pos_hint={'y': 0}, padding=[20, 15], spacing=5)
        with self.dialog_box.canvas.before:
            Color(0.02, 0.03, 0.04, 0.95)
            self.dialog_rect = Rectangle(size=self.dialog_box.size, pos=self.dialog_box.pos)
            Color(0.65, 0.55, 0.35, 1)
            self.dialog_border = Line(rectangle=(self.dialog_box.x, self.dialog_box.y, self.dialog_box.width, self.dialog_box.height), width=2)
        self.dialog_box.bind(size=lambda i, v: (setattr(self.dialog_rect, 'size', v), setattr(self.dialog_border, 'rectangle', (i.x, i.y, i.width, i.height))), 
                             pos=lambda i, v: (setattr(self.dialog_rect, 'pos', v), setattr(self.dialog_border, 'rectangle', (i.x, i.y, i.width, i.height))))

        self.speaker_label = Label(text="", size_hint_y=0.15, font_size='18sp', bold=True, color=(0.85, 0.74, 0.51, 1), halign='left', valign='middle')
        self.speaker_label.bind(size=self.speaker_label.setter('text_size'))
        self.dialog_box.add_widget(self.speaker_label)

        self.scroll = ScrollView(size_hint_y=0.7)
        self.text_label = Label(text="", font_size='20sp', halign='left', valign='top', size_hint_y=None, line_height=1.2, markup=True, color=(0.95, 0.93, 0.9, 1))
        self.text_label.bind(width=lambda *x: self.text_label.setter('text_size')(self.text_label, (self.text_label.width, None)))
        self.text_label.bind(texture_size=self.text_label.setter('size'))
        self.scroll.add_widget(self.text_label)
        self.dialog_box.add_widget(self.scroll)

        self.continue_btn = Button(text="CONTINUE >", size_hint_y=0.15, background_color=(0.05, 0.08, 0.1, 1), font_size='16sp', color=(0.85, 0.8, 0.7, 1))
        with self.continue_btn.canvas.before:
            Color(0.65, 0.55, 0.35, 1)
            self.cont_border = Line(rectangle=(self.continue_btn.x, self.continue_btn.y, self.continue_btn.width, self.continue_btn.height), width=1)
        self.continue_btn.bind(pos=lambda i, v: setattr(self.cont_border, 'rectangle', (i.x, i.y, i.width, i.height)),
                               size=lambda i, v: setattr(self.cont_border, 'rectangle', (i.x, i.y, i.width, i.height)))
        self.continue_btn.bind(on_release=self.advance)
        self.dialog_box.add_widget(self.continue_btn)

        self.choice_layout = BoxLayout(orientation='vertical', size_hint=(1, 0.4), pos_hint={'y': 0}, spacing=10, padding=20)
        with self.choice_layout.canvas.before:
            Color(0.02, 0.03, 0.04, 0.95)
            self.choice_rect = Rectangle(size=self.choice_layout.size, pos=self.choice_layout.pos)
        self.choice_layout.bind(size=lambda i, v: setattr(self.choice_rect, 'size', v), pos=lambda i, v: setattr(self.choice_rect, 'pos', v))

        self.layout.add_widget(self.dialog_box)
        self.layout.add_widget(self.choice_layout)
        self.add_widget(self.layout)

    def open_save(self, instance):
        if self.temp_lines: return
        self.manager.get_screen('saveload').mode = 'save'
        self.manager.current = 'saveload'
        
    def confirm_reset(self, instance):
        App.get_running_app().root.current = 'menu'

    def save_game(self, slot):
        if self.temp_lines: return
        try:
            path = os.path.join(get_data_dir(), f"save_{slot}.json")
            chapter = CHAPTER_BY_SCENE.get(self.scene_id)
            title = f"Chapter {chapter.key} - {chapter.title}" if chapter else self.scene_id
            
            data = {
                "current_scene": self.scene_id, "line_index": self.line_index, "flags": self.flags,
                "preview_title": title, "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2)
        except Exception as e: print(f"Save fail: {e}")

    def load_game(self, slot):
        try:
            path = os.path.join(get_data_dir(), f"save_{slot}.json")
            with open(path, 'r', encoding='utf-8') as f: data = json.load(f)
            self.scene_id = data["current_scene"]
            self.line_index = data["line_index"]
            self.flags = data["flags"]
            self.temp_lines = None; self.temp_index = 0; self.pending_next_scene = None
            self.auto_mode = False; self.skip_mode = False
            self.update_ui()
        except Exception as e: print(f"Load fail: {e}")

    def reset_game(self):
        self.scene_id = "summoning"
        self.line_index = 0
        self.flags = {"bond": 0, "peace": 0, "resolve": 0, "family_final": 0, "reputation": 0}
        self.temp_lines = None; self.temp_index = 0; self.pending_next_scene = None
        self.auto_mode = False; self.skip_mode = False
        self.load_scene(self.scene_id)

    def toggle_auto(self, instance):
        self.auto_mode = not self.auto_mode
        self.skip_mode = False
        instance.background_color = (0.1, 0.4, 0.1, 1) if self.auto_mode else (0.05, 0.08, 0.1, 1)
        if self.auto_mode and not self.is_typing: Clock.schedule_once(lambda dt: self.advance(None), 1.0)

    def toggle_skip(self, instance):
        self.skip_mode = not self.skip_mode
        self.auto_mode = False
        instance.background_color = (0.4, 0.1, 0.1, 1) if self.skip_mode else (0.05, 0.08, 0.1, 1)
        if self.skip_mode:
            if self.is_typing: self.skip_typing()
            else: self.advance(None)

    def load_scene(self, scene_id):
        self.scene_id = scene_id
        self.line_index = 0
        self.temp_lines = None; self.temp_index = 0
        self.update_ui()

    def next_scene(self, target):
        if target == "ending_gate": target = ending_for(self.flags)
        self.load_scene(target)

    def update_characters(self, cast):
        self.char_layer.clear_widgets()
        if not cast: return
        n = len(cast)
        positions = [0.5] if n == 1 else [0.25, 0.75] if n == 2 else [0.15, 0.5, 0.85] if n == 3 else [0.15, 0.38, 0.62, 0.85]
        filename_map = {"Mika": "Mika", "Mika Amanogawa": "Mika", "Mallory": "Mallory", "Mallory Valerius": "Mallory", "King Galvath": "Galvath", "King Galvath Valerius": "Galvath", "Lira": "Lira", "Lira Vanguard": "Lira", "Gorthak": "Gorthak", "Gorthak Stonefist": "Gorthak", "Vane": "Vane", "Vane Blackwood": "Vane", "Shadow": "shadow", "Mika_Evil": "Mika_Evil"}

        for i, name in enumerate(cast):
            base_name = filename_map.get(name, name)
            expression = ""
            if name in ("Mika", "Mika Amanogawa") and self.scene_id in {"grief", "sacrifice", "jealousy", "confrontation", "winter_vigil", "final_battle"}: expression = "_sad"
            elif name in ("Mika", "Mika Amanogawa") and self.scene_id in {"ending_home", "ending_peace", "reconciliation", "trio", "garden", "return"}: expression = "_happy"
            elif name in ("Mallory", "Mallory Valerius") and self.scene_id in {"grief", "lira_maid", "sacrifice"}: expression = "_sad"

            img_path = find_asset(f'characters/{base_name}{expression}.png') or find_asset(f'characters/{base_name}.png')
            if not img_path: continue

            try:
                core_img = CoreImage(img_path)
                aspect_ratio = core_img.size[0] / core_img.size[1]
                target_height = self.char_layer.height * 0.85
                target_width = target_height * aspect_ratio
                char = Image(source=img_path, size_hint=(None, None), size=(target_width, target_height), pos_hint={'center_x': positions[i], 'y': -0.05})
                self.char_layer.add_widget(char)
            except Exception: pass

    def parse_lively_text(self, text):
        self.do_shake = "[shake]" in text
        text = text.replace("[shake]", "").replace("[/shake]", "")
        text = re.sub(r'\[color=(.*?)\]', r'[color=\1]', text)
        return text

    def start_typing(self, speaker, text):
        self.current_speaker = speaker
        self.full_text = self.parse_lively_text(text)
        self.typing_idx = 0
        self.text_label.text = ""
        self.is_typing = True
        
        if self.shake_event: self.shake_event.cancel()
        self.text_label.pos_hint = {'x': 0, 'y': 0}
        
        if self.do_shake:
            self.shake_event = Clock.schedule_interval(self._do_shake, 0.05)

        if self.typing_event: self.typing_event.cancel()
        self.typing_event = Clock.schedule_interval(self._type_char, 0.03)

    def _do_shake(self, dt):
        dx = random.randint(-2, 2)
        dy = random.randint(-2, 2)
        self.text_label.pos_hint = {'x': dx * 0.001, 'y': dy * 0.001}

    def _type_char(self, dt):
        if self.typing_idx < len(self.full_text):
            if self.full_text[self.typing_idx] == "[":
                end_bracket = self.full_text.find("]", self.typing_idx)
                if end_bracket != -1:
                    self.typing_idx = end_bracket + 1
            
            self.typing_idx += 1
            self.text_label.text = self.full_text[:self.typing_idx]
            
            if self.typing_idx % 2 == 0: self.voice.play(self.current_speaker)
        else:
            self.is_typing = False
            self.typing_event.cancel()
            if self.auto_mode: Clock.schedule_once(lambda dt: self.advance(None), 2.0)

    def skip_typing(self):
        if self.is_typing:
            self.is_typing = False
            self.typing_event.cancel()
            if self.shake_event: self.shake_event.cancel()
            self.text_label.pos_hint = {'x': 0, 'y': 0}
            self.text_label.text = self.full_text
            if self.auto_mode: Clock.schedule_once(lambda dt: self.advance(None), 1.0)
            return True
        return False

    def update_ui(self):
        if not STORY or self.scene_id not in STORY: return
        scene = STORY[self.scene_id]
        
        bg_path = find_asset(f'backgrounds/{scene.backdrop}.png')
        self.bg_image.source = bg_path if bg_path else ''
        self.particles.set_backdrop(scene.backdrop)
        
        try: App.get_running_app().play_chapter_music(self.scene_id)
        except Exception: pass
            
        self.update_characters(scene.cast)

        if self.temp_lines: line = self.temp_lines[self.temp_index]
        else: line = scene.lines[self.line_index]

        self.speaker_label.text = line.speaker.upper().replace("_EVIL", "")
        raw_text = resolve_text(line.text, self.flags)
        
        ready_for_choice = bool(scene.choices) and not self.temp_lines and self.line_index == len(scene.lines) - 1

        if ready_for_choice:
            self.is_typing = False
            if self.typing_event: self.typing_event.cancel()
            self.dialog_box.opacity = 0; self.dialog_box.disabled = True
            self.choice_layout.clear_widgets()
            for i, choice in enumerate(scene.choices):
                btn = Button(text=f"{i+1}. {choice.text}", size_hint_y=None, height=70, background_color=(0.15, 0.15, 0.2, 1), font_size='16sp')
                with btn.canvas.before:
                    Color(0.65, 0.55, 0.35, 1)
                    border = Line(rectangle=(btn.x, btn.y, btn.width, btn.height), width=1)
                btn.bind(pos=lambda j, v, b=border: setattr(b, 'rectangle', (j.x, j.y, j.width, j.height)),
                         size=lambda j, v, b=border: setattr(b, 'rectangle', (j.x, j.y, j.width, j.height)))
                btn.bind(on_release=lambda instance, idx=i: self.choose(idx))
                self.choice_layout.add_widget(btn)
        else:
            self.dialog_box.opacity = 1; self.dialog_box.disabled = False
            self.choice_layout.clear_widgets()
            
            if self.temp_lines and self.temp_index == len(self.temp_lines) - 1: self.continue_btn.text = "CONTINUE >>"
            elif scene.ending and self.line_index == len(scene.lines) - 1 and not self.temp_lines: self.continue_btn.text = "MAIN MENU"
            else: self.continue_btn.text = "CONTINUE >"

            self.start_typing(line.speaker, raw_text)

    def advance(self, instance):
        if self.skip_typing(): return
        if not STORY or self.scene_id not in STORY: return
        scene = STORY[self.scene_id]

        if self.temp_lines:
            self.temp_index += 1
            if self.temp_index >= len(self.temp_lines):
                target = self.pending_next_scene
                self.temp_lines = None; self.temp_index = 0; self.pending_next_scene = None
                if target: self.next_scene(target)
                else: self.manager.current = 'menu'
            else: self.update_ui()
            return

        if self.line_index < len(scene.lines) - 1:
            self.line_index += 1
            self.update_ui()
        elif scene.next_scene is not None:
            self.next_scene(scene.next_scene)
        elif scene.ending:
            App.get_running_app().play_menu_music()
            self.manager.current = 'menu'

    def choose(self, index):
        if not STORY or self.scene_id not in STORY: return
        scene = STORY[self.scene_id]
        choice = scene.choices[index]
        for name, value in choice.effects.items(): self.flags[name] += value

        if choice.outcome_lines:
            self.temp_lines = choice.outcome_lines; self.temp_index = 0
            self.pending_next_scene = choice.next_scene
            self.update_ui()
        else: self.next_scene(choice.next_scene)

# ---------------------------------------------------------
# 6. APP LAUNCHER
# ---------------------------------------------------------
class EchoesApp(App):
    music_vol = 0.5
    voice_vol = 0.5
    current_bgm = None
    current_bgm_path = ""

    def build(self):
        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(SplashScreen(name='splash'))
        sm.add_widget(MainMenuScreen(name='menu'))
        sm.add_widget(SettingsScreen(name='settings'))
        sm.add_widget(ChapterSelectScreen(name='chapters'))
        sm.add_widget(SoundtrackScreen(name='soundtrack'))
        sm.add_widget(CreditsScreen(name='credits'))
        sm.add_widget(SaveLoadScreen(name='saveload'))
        sm.add_widget(GameScreen(name='game'))
        return sm

    def play_menu_music(self):
        track = find_asset('menu_bgm.mp3') or find_asset('menu_bgm.wav')
        if track: self.play_music(track)

    def play_chapter_music(self, scene_id):
        try:
            track_path = CHAPTER_MUSIC.get(scene_id)
            if track_path:
                path_str = str(track_path).replace('.mp3', '.wav')
                if not os.path.exists(path_str) and os.path.exists(str(track_path)): path_str = str(track_path)
                if os.path.exists(path_str): self.play_music(path_str)
        except Exception: pass

    def play_music(self, path_str):
        if not path_str or not isinstance(path_str, str): return
        if self.current_bgm_path == path_str and self.current_bgm and self.current_bgm.state == 'play': return
        
        if self.current_bgm:
            try: self.current_bgm.stop(); self.current_bgm.unload()
            except Exception: pass

        try:
            self.current_bgm = SoundLoader.load(path_str)
            if self.current_bgm:
                self.current_bgm.volume = self.music_vol
                self.current_bgm.loop = True
                self.current_bgm.play()
                self.current_bgm_path = path_str
        except Exception: pass

    def set_music_volume(self, vol):
        self.music_vol = vol
        if self.current_bgm:
            try: self.current_bgm.volume = vol
            except Exception: pass

if __name__ == '__main__':
    EchoesApp().run()
