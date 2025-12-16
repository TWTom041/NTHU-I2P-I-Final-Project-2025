'''
[TODO HACKATHON 5]
Try to mimic the menu_scene.py or game_scene.py to create this new scene
'''
import pygame as pg

from src.utils import GameSettings
from src.sprites import BackgroundSprite
from src.scenes.scene import Scene
from src.interface.components import Button, OnOffButton, Slider
from src.core.services import scene_manager, sound_manager, input_manager, resource_manager
from typing import override

class SettingScene(Scene):
    # Background Image
    background: BackgroundSprite
    # Buttons
    setting_button: Button
    mute_button: OnOffButton
    volume_slider: Slider
    volume=1.0
    is_mute=False
    
    def __init__(self):
        super().__init__()
        self.background = BackgroundSprite("backgrounds/background_setting.png")

        px, py = GameSettings.SCREEN_WIDTH * 3 // 4, GameSettings.SCREEN_HEIGHT * 1 // 4 - 30
        self.setting_button = Button(
            "UI/button_x.png", "UI/button_x_hover.png",
            px - 50, py, 50, 50, 
            lambda: scene_manager.change_scene("menu")
        )
        self.mute_button = OnOffButton(
            "UI/raw/UI_Flat_ToggleOn03a.png", "UI/raw/UI_Flat_ToggleOff03a.png",
            390, 265, 50, 50,
            self.set_mute, False
        )
        self.volume_slider = Slider(
            "UI/raw/UI_Flat_ToggleOn01a.png", "UI/raw/UI_Flat_ToggleOff01a.png",
            325, 365, 600, 30, self.volume
        )

    def set_mute(self, val):
        self.is_mute = val
    
    @override
    def enter(self) -> None:
        pass

    @override
    def exit(self) -> None:
        pass

    @override
    def update(self, dt: float) -> None:
        if input_manager.key_pressed(pg.K_ESCAPE):
            scene_manager.change_scene("menu")
            return
        self.setting_button.update(dt)
        self.mute_button.update(dt)
        self.volume_slider.update(dt)
        self.volume = self.volume_slider.value
        sound_manager.current_bgm.set_volume(self.volume if not self.is_mute else 0)

    @override
    def draw(self, screen: pg.Surface) -> None:
        self.background.draw(screen)
        self.setting_button.draw(screen)
        screen_w, screen_h = screen.get_size()
        panel_w, panel_h = int(screen_w * 0.55), int(screen_h * 0.45)
        panel_x = screen_w // 2 - panel_w // 2
        panel_y = screen_h // 2 - panel_h // 2
        self._draw_setting_ui(screen, (panel_x, panel_y, panel_w, panel_h))

    def _draw_setting_ui(self, screen: pg.Surface, panel_rect):
        px, py, pw, ph = panel_rect

        # Labels
        label_font = resource_manager.get_font("Minecraft.ttf", 18)
        small_font = resource_manager.get_font("Minecraft.ttf", 14)

        # Mute row
        mute_label = label_font.render("Mute", True, (200, 200, 200))
        screen.blit(mute_label, (px + 40, py + 80))
        self.mute_button.draw(screen)

        # Volume row - draw an accent track behind the slider to make it prettier
        volume_label = label_font.render("Master Volume", True, (200, 200, 200))
        screen.blit(volume_label, (px + 40, py + 140))

        # custom track
        track_x = px + 40
        track_y = py + 180
        track_w = pw - 120
        track_h = 8
        track_rect = pg.Rect(track_x, track_y, track_w, track_h)
        # dark background track
        pg.draw.rect(screen, (80, 80, 80), track_rect, border_radius=8)
        # filled portion
        filled_w = int(track_w * (self.volume_slider.value if hasattr(self.volume_slider, 'value') else self.volume))
        pg.draw.rect(screen, (200, 120, 30), (track_x, track_y, filled_w, track_h), border_radius=8)

        self.volume_slider.draw(screen)

        # small footer hint
        hint = small_font.render("Saved games are stored in /saves - backup recommended", True, (160, 160, 160))
        screen.blit(hint, (px + 40, py + ph - 40))