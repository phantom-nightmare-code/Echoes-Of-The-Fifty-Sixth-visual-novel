import os
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.image import Image
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.core.window import Window

# Set a dark background color for the app
Window.clearcolor = (0.05, 0.05, 0.05, 1)

class SplashScreen(Screen):
    def __init__(self, **kwargs):
        super(SplashScreen, self).__init__(**kwargs)
        
        # Use a BoxLayout to center the logo
        layout = BoxLayout(orientation='vertical', padding=50)
        
        # Make sure 'logo.png' is in your main folder!
        self.logo = Image(
            source='logo.png', 
            allow_stretch=True, 
            keep_ratio=True,
            size_hint=(1, 1)
        )
        
        layout.add_widget(self.logo)
        self.add_widget(layout)
        
        # Start a timer to switch to the game screen after 3 seconds
        Clock.schedule_once(self.switch_to_game, 3.0)

    def switch_to_game(self, dt):
        # Change to the game screen with a fade effect
        self.manager.current = 'game'

class GameScreen(Screen):
    def __init__(self, **kwargs):
        super(GameScreen, self).__init__(**kwargs)
        
        # ---------------------------------------------------------
        # PASTE YOUR EXISTING GAME UI CODE HERE
        # (e.g., your background image, character sprites, text label)
        # ---------------------------------------------------------
        
        # This is just a placeholder for your actual visual novel layout
        main_layout = BoxLayout(orientation='vertical')
        main_layout.add_widget(Label(text="Game Starts Here!", font_size='30sp'))
        
        # Example of how you would add your visual novel background:
        # main_layout.add_widget(Image(source='background.png', allow_stretch=True, keep_ratio=False))
        
        self.add_widget(main_layout)

class EchoesApp(App):
    def build(self):
        # Create the screen manager
        sm = ScreenManager(transition=FadeTransition())
        
        # Add the screens
        sm.add_widget(SplashScreen(name='splash'))
        sm.add_widget(GameScreen(name='game'))
        
        return sm

if __name__ == '__main__':
    EchoesApp().run()
