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
        
        # Start background music
        # IMPORTANT: Change this path to match your exact music file!
        self.bg_music = SoundLoader.load('assets/chapter_music/your_song_name.ogg') 
        if self.bg_music:
            self.bg_music.loop = True
            self.bg_music.play()
        
        # FloatLayout allows overlapping widgets (Background, Characters, Text)
        root = FloatLayout()
        
        # --- 1. BACKGROUND ---
        # Uncomment and change the path when you are ready
        # bg_img = Image(source='assets/backgrounds/castle.jpg', allow_stretch=True, keep_ratio=False, size_hint=(1, 1))
        # root.add_widget(bg_img)
        
        # --- 2. CHARACTERS ---
        # Uncomment and change the paths when you are ready
        # char_layout = BoxLayout(size_hint=(1, 0.6), pos_hint={'center_x': 0.5, 'y': 0.2})
        # char_layout.add_widget(Image(source='assets/sprites/mika.png', allow_stretch=True, keep_ratio=True))
        # root.add_widget(char_layout)
        
        # --- 3. DIALOGUE BOX ---
        # Anchored to the bottom, taking up 35% of the screen
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
        # CRITICAL: Forces the text to wrap to the next line on mobile screens
        self.dialogue_label.bind(size=self.dialogue_label.setter('text_size'))
        
        dialogue_box.add_widget(self.dialogue_label)
        
        # Continue Button
        self.continue_btn = Button(
            text="Continue", 
            size_hint_y=0.2, 
            background_color=(0.2, 0.2, 0.2, 1),
            font_size='18sp'
        )
        
        dialogue_box.add_widget(self.continue_btn)
        
        root.add_widget(dialogue_box)
        self.add_widget(root)

class EchoesApp(App):
    def build(self):
        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(SplashScreen(name='splash'))
        sm.add_widget(GameScreen(name='game'))
        return sm

if __name__ == '__main__':
    EchoesApp().run()
