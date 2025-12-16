from __future__ import annotations
import pygame as pg

from src.sprites import Sprite
from src.core.services import input_manager
from src.utils import Logger
from typing import Callable, override
from .component import UIComponent

class Button(UIComponent):
    img_button: Sprite
    img_button_default: Sprite
    img_button_hover: Sprite
    hitbox: pg.Rect
    on_click: Callable[[], None] | None

    def __init__(
        self,
        img_path: str, img_hovered_path:str,
        x: int, y: int, width: int, height: int,
        on_click: Callable[[], None] | None = None
    ):
        self.img_button_default = Sprite(img_path, (width, height))
        self.hitbox = pg.Rect(x, y, width, height)
        '''
        [TODO HACKATHON 1]
        Initialize the properties
        
        self.img_button_hover = ...
        self.img_button = ...       --> This is a reference for which image to render
        self.on_click = ...
        '''
        self.img_button_hover = Sprite(img_hovered_path, (width, height))
        self.img_button = self.img_button_default
        self.on_click = on_click


    @override
    def update(self, dt: float) -> None:
        '''
        [TODO HACKATHON 1]
        Check if the mouse cursor is colliding with the button, 
        1. If collide, draw the hover image
        2. If collide & clicked, call the on_click function
        
        if self.hitbox.collidepoint(input_manager.mouse_pos):
            ...
            if input_manager.mouse_pressed(1) and self.on_click is not None:
                ...
        else:
            ...
        '''
        if self.hitbox.collidepoint(input_manager.mouse_pos):
            self.img_button = self.img_button_hover
            if input_manager.mouse_pressed(1) and self.on_click is not None:
                self.on_click()
        else:
            self.img_button = self.img_button_default
        pass
    
    @override
    def draw(self, screen: pg.Surface) -> None:
        '''
        [TODO HACKATHON 1]
        You might want to change this too
        '''
        _ = screen.blit(self.img_button.image, self.hitbox)


class OnOffButton(UIComponent):
    img_button: Sprite
    img_button_on: Sprite
    img_button_hover: Sprite
    hitbox: pg.Rect
    on_click: Callable[[], None] | None
    state: bool

    def __init__(
        self,
        img_path_on: str, img_path_off:str,
        x: int, y: int, width: int, height: int,
        on_click: Callable[[], None] | None = None,
        init_state=True
    ):
        self.img_button_on = Sprite(img_path_on, (width, height))
        self.hitbox = pg.Rect(x, y, width, height)
        self.img_button_off = Sprite(img_path_off, (width, height))
        self.on_click = on_click
        self.state = init_state
        if self.state:
            self.img_button = self.img_button_on
        else:
            self.img_button = self.img_button_off


    @override
    def update(self, dt: float) -> None:
        if self.hitbox.collidepoint(input_manager.mouse_pos) and input_manager.mouse_pressed(1) and self.on_click is not None:
            self.state = not self.state
            self.on_click(self.state)
            if self.state:
                self.img_button = self.img_button_on
            else:
                self.img_button = self.img_button_off
        pass
    
    @override
    def draw(self, screen: pg.Surface) -> None:
        _ = screen.blit(self.img_button.image, self.hitbox)

class Slider(UIComponent):
    img_rail: Sprite
    img_knob: Sprite
    rail_rect: pg.Rect
    knob_rect: pg.Rect

    dragging: bool
    value: float  # Ranges 0..1

    def __init__(
        self,
        rail_img_path: str,
        knob_img_path: str,
        x: int, y: int,
        length: int,
        height: int,
        initial_value: float = 0.5
    ):
        # Clamp initial value
        initial_value = max(0.0, min(1.0, initial_value))

        # Load images
        self.img_rail = Sprite(rail_img_path, (length, height))
        knob_size = self.img_rail.image.get_height()  # knob same height OR override
        self.img_knob = Sprite(knob_img_path, (knob_size, knob_size))

        # Rail hitbox
        self.rail_rect = pg.Rect(x, y, length, height)

        # Knob hitbox
        knob_x = x + int(initial_value * (length - knob_size))
        knob_y = y + (height - knob_size) // 2
        self.knob_rect = pg.Rect(knob_x, knob_y, knob_size, knob_size)

        self.value = initial_value
        self.dragging = False


    @override
    def update(self, dt: float) -> None:
        mouse_pos = input_manager.mouse_pos

        if input_manager.mouse_pressed(1):
            if self.knob_rect.collidepoint(mouse_pos):
                self.dragging = True

        if self.dragging and input_manager.mouse_down(1):
            rail_x = self.rail_rect.x
            rail_length = self.rail_rect.width
            knob_w = self.knob_rect.width

            new_x = mouse_pos[0] - knob_w // 2
            new_x = max(rail_x, min(new_x, rail_x + rail_length - knob_w))

            self.knob_rect.x = new_x
            self.value = (new_x - rail_x) / (rail_length - knob_w)

        if input_manager.mouse_released(1):
            self.dragging = False



    @override
    def draw(self, screen: pg.Surface) -> None:
        # Rail
        screen.blit(self.img_rail.image, self.rail_rect)

        # Knob
        screen.blit(self.img_knob.image, self.knob_rect)



def main():
    import sys
    import os
    
    pg.init()

    WIDTH, HEIGHT = 800, 800
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    pg.display.set_caption("Button Test")
    clock = pg.time.Clock()
    
    bg_color = (0, 0, 0)
    def on_button_click():
        nonlocal bg_color
        if bg_color == (0, 0, 0):
            bg_color = (255, 255, 255)
        else:
            bg_color = (0, 0, 0)
        
    button = Button(
        img_path="UI/button_play.png",
        img_hovered_path="UI/button_play_hover.png",
        x=WIDTH // 2 - 50,
        y=HEIGHT // 2 - 50,
        width=100,
        height=100,
        on_click=on_button_click
    )
    
    running = True
    dt = 0
    
    while running:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
            input_manager.handle_events(event)
        
        dt = clock.tick(60) / 1000.0
        button.update(dt)
        
        input_manager.reset()
        
        _ = screen.fill(bg_color)
        
        button.draw(screen)
        
        pg.display.flip()
    
    pg.quit()


if __name__ == "__main__":
    main()
