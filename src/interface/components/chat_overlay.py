from __future__ import annotations
import pygame as pg
from typing import Optional, Callable, List, Dict
from .component import UIComponent
from src.core.services import input_manager
from src.utils import Logger

class ChatOverlay(UIComponent):
    """Lightweight chat UI similar to Minecraft: toggle with a key, type, press Enter to send."""
    is_open: bool
    _input_text: str
    _cursor_timer: float
    _cursor_visible: bool
    _just_opened: bool
    _send_callback: Callable[[str], bool] | None
    _get_messages: Callable[[int], list[dict]] | None
    _font_msg: pg.font.Font
    _font_input: pg.font.Font

    def __init__(
        self,
        send_callback: Callable[[str], bool] | None = None,
        get_messages: Callable[[int], list[dict]] | None = None,
        *,
        font_path: str = "assets/fonts/Minecraft.ttf"
    ) -> None:
        self.is_open = False
        self._input_text = ""
        self._cursor_timer = 0.0
        self._cursor_visible = True
        self._just_opened = False
        self._send_callback = send_callback
        self._get_messages = get_messages

        # DONE: Initialize fonts with fallback
        try:
            # size 20 is usually good for chat
            self._font_msg = pg.font.Font(font_path, 20)
            self._font_input = pg.font.Font(font_path, 20)
        except Exception:
            Logger.log(f"ChatOverlay: Could not load {font_path}, using system fallback.")
            self._font_msg = pg.font.SysFont("arial", 20)
            self._font_input = pg.font.SysFont("arial", 20)

    def open(self) -> None:
        if not self.is_open:
            self.is_open = True
            self._cursor_timer = 0.0
            self._cursor_visible = True
            self._just_opened = True

    def close(self) -> None:
        self.is_open = False

    def _handle_typing(self) -> None:
        """
        Handles manual keyboard polling to construct the input string.
        """
        shift = input_manager.key_down(pg.K_LSHIFT) or input_manager.key_down(pg.K_RSHIFT)

        # DONE: Handle Letters (a-z)
        for k in range(pg.K_a, pg.K_z + 1):
            if input_manager.key_pressed(k):
                ch = chr(ord('a') + (k - pg.K_a))
                self._input_text += (ch.upper() if shift else ch)

        # DONE: Handle Numbers (0-9)
        # Note: This does not handle symbols (like !@#) to keep the code simple,
        # but you can add a mapping dictionary if needed.
        for k in range(pg.K_0, pg.K_9 + 1):
            if input_manager.key_pressed(k):
                self._input_text += str(k - pg.K_0)

        # DONE: Handle Space and Backspace
        if input_manager.key_pressed(pg.K_SPACE):
            self._input_text += " "
        elif input_manager.key_pressed(pg.K_BACKSPACE):
            self._input_text = self._input_text[:-1]

        # DONE: Enter to send
        if input_manager.key_pressed(pg.K_RETURN) or input_manager.key_pressed(pg.K_KP_ENTER):
            txt = self._input_text.strip()
            # Check if text exists and callback is valid
            if txt and self._send_callback:
                ok = False
                try:
                    # Execute the callback
                    ok = self._send_callback(txt)
                except Exception as e:
                    Logger.log(f"Chat send error: {e}")
                    ok = False
                
                # If sent successfully, clear text. 
                # (Optional: call self.close() here if you want chat to close on send)
                if ok:
                    self._input_text = ""

    def update(self, dt: float) -> None:
        if not self.is_open:
            return

        # DONE: Close on Escape
        if input_manager.key_pressed(pg.K_ESCAPE):
            self.close()
            return

        # Typing
        if self._just_opened:
            self._just_opened = False
        else:
            self._handle_typing()
            
        # Cursor blink
        self._cursor_timer += dt
        if self._cursor_timer >= 0.5:
            self._cursor_timer = 0.0
            self._cursor_visible = not self._cursor_visible

    def draw(self, screen: pg.Surface) -> None:
        # Always draw recent messages faintly, even when closed
        msgs = self._get_messages(8) if self._get_messages else []
        sw, sh = screen.get_size()
        x = 10
        y = sh - 100
        
        # Draw background for messages
        if msgs:
            container_w = max(100, int((sw - 20) * 0.6))
            bg = pg.Surface((container_w, 90), pg.SRCALPHA)
            bg.fill((0, 0, 0, 90 if self.is_open else 60))
            _ = screen.blit(bg, (x, y))
            
            # Render last messages
            lines = list(msgs)[-8:]
            draw_y = y + 8
            for m in lines:
                sender = str(m.get("from", "System"))
                text = str(m.get("text", ""))
                surf = self._font_msg.render(f"{sender}: {text}", True, (255, 255, 255))
                _ = screen.blit(surf, (x + 10, draw_y))
                draw_y += surf.get_height() + 4
                
        # If not open, skip input field
        if not self.is_open:
            return
            
        # Input box dimensions
        box_h = 28
        box_w = max(100, int((sw - 20) * 0.6))
        box_y = sh - box_h - 6
        
        # Background box
        bg2 = pg.Surface((box_w, box_h), pg.SRCALPHA)
        bg2.fill((0, 0, 0, 160))
        _ = screen.blit(bg2, (x, box_y))
        
        # DONE: Text Rendering
        text_surf = self._font_input.render(self._input_text, True, (255, 255, 255))
        _ = screen.blit(text_surf, (x + 8, box_y + 4))
        
        # Caret (Cursor)
        if self._cursor_visible:
            cx = x + 8 + text_surf.get_width() + 2
            cy = box_y + 6
            pg.draw.rect(screen, (255, 255, 255), pg.Rect(cx, cy, 2, box_h - 12))