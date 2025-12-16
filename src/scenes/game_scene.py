import pygame as pg

from src.scenes.scene import Scene
from src.core import GameManager, OnlineManager
from src.core.services import sound_manager, resource_manager, input_manager
from src.utils import Logger, PositionCamera, GameSettings, Position
from src.interface.components import Button, OnOffButton, Slider, ChatOverlay
from src.sprites import Sprite, Animation 
from typing import override


class GameScene(Scene):
    game_manager: GameManager
    online_manager: OnlineManager | None
    
    # Key: Player ID, Value: Animation object
    remote_players: dict[int, Animation] 
    
    in_setting = False
    in_bag = False
    in_shop = False
    volume = 1.0
    is_mute = False
    shop_npc = None
    shop_tab = "buy"
    bag = {"monsters": [], "items": []}

    # ADDED: Variables for minimap caching
    _cached_minimap_surf: pg.Surface | None = None
    _cached_minimap_path: str | None = None
    _minimap_rect: pg.Rect | None = None
    _minimap_scale: float = 0.1

    def __init__(self):
        super().__init__()
        # Game Manager
        manager = GameManager.load("saves/game0.json")
        if manager is None:
            Logger.error("Failed to load game manager")
            exit(1)
        self.game_manager = manager

        # Online Manager
        if GameSettings.IS_ONLINE:
            self.online_manager = OnlineManager()
            self.online_manager.register()
        else:
            self.online_manager = None
        
        # Initialize dictionary for remote player animations
        self.remote_players = {}

        # Keep original buttons but we'll reposition them dynamically when opening panels
        self.bag_button = Button(
            "UI/button_backpack.png", "UI/button_backpack_hover.png",
            1030, 30, 100, 100,
            lambda *a: self.set_inbag(True)
        )
        self.quit_bag_button = Button(
            "UI/button_x.png", "UI/button_x_hover.png",
            1060, 95, 50, 50,
            lambda *a: self.set_inbag(False)
        )

        self.setting_button = Button(
            "UI/button_setting.png", "UI/button_setting_hover.png",
            1150, 30, 100, 100,
            lambda *a: self.set_insetting(True)
        )
        self.quit_setting_buttom = Button(
            "UI/button_x.png", "UI/button_x_hover.png",
            930, 205, 50, 50,
            lambda *a: self.set_insetting(False)
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
        self.save_button = Button(
            "UI/button_save.png", "UI/button_save_hover.png",
            765, 420, 90, 90,
            lambda *_: self.game_manager.save("saves/game0.json")
        )
        self.load_button = Button(
            "UI/button_load.png", "UI/button_load_hover.png",
            880, 420, 90, 90,
            self.load
        )

        self.quit_shop_button = Button(
            "UI/button_x.png", "UI/button_x_hover.png",
            1060, 95, 50, 50,
            lambda *a: self.set_inshop(False)
        )
        self.shop_buy_tab_btn = Button("UI/button_shop.png", "UI/button_shop_hover.png", 0, 0, 100, 100, lambda *a: self._set_shop_tab("buy"))
        self.shop_sell_tab_btn = Button("UI/button_shop.png", "UI/button_shop_hover.png", 200, 0, 100, 100, lambda *a: self._set_shop_tab("sell"))
        
        self.chat_overlay = ChatOverlay(
            send_callback=self._on_chat_send,
            get_messages=self._get_chat_messages
        )


    def load(self):
        manager = GameManager.load("saves/game0.json")
        if manager is None:
            Logger.error("Failed to load game manager")
            exit(1)
        self.game_manager = manager

    def set_insetting(self, val):
        self.in_setting = val
        if val:
            # reposition setting widgets relative to center panel when opened
            screen_w, screen_h = pg.display.get_surface().get_size()
            panel_w, panel_h = screen_w // 2, screen_h // 2
            cx, cy = screen_w // 2, screen_h // 2
            
            left = cx - panel_w // 2 + 40
            top = cy - panel_h // 2 + 60
            self._set_widget_pos(self.quit_setting_buttom, cx + panel_w // 2 - 60, cy - panel_h // 2 + 20, 40, 40)
            self._set_widget_pos(self.mute_button, left, top, 40, 40)
            self._set_widget_pos(self.volume_slider, left, top + 80, panel_w - 120, 24)
            self._set_widget_pos(self.save_button, left, cy + panel_h // 2 - 90, 100, 40)
            self._set_widget_pos(self.load_button, left + 120, cy + panel_h // 2 - 90, 100, 40)

    def set_inbag(self, val):
        self.in_bag = val
        if self.in_bag:
            self.bag = {"monsters": [], "items": []}
            for monster in self.game_manager.bag._monsters_data:
                monster = monster.copy()
                monster["sprite"] = Sprite(monster["sprite_path"], (80, 80))
                self.bag["monsters"].append(monster)
            for item in self.game_manager.bag._items_data:
                item = item.copy()
                item["sprite"] = Sprite(item["sprite_path"], (80, 80))
                self.bag["items"].append(item)

            # reposition bag close button
            screen_w, screen_h = pg.display.get_surface().get_size()
            panel_w, panel_h = int(screen_w * 0.7), int(screen_h * 0.7)
            cx, cy = screen_w // 2, screen_h // 2
            self._set_widget_pos(self.quit_bag_button, cx + panel_w // 2 - 40, cy - panel_h // 2 + 20, 40, 40)

    def set_mute(self, val):
        self.is_mute = val

    def _set_widget_pos(self, widget, x, y, w=None, h=None):
        try:
            widget.x = x
            widget.y = y
        except Exception:
            pass
        try:
            if hasattr(widget, 'rect') and widget.rect is not None:
                ow, oh = widget.rect.w, widget.rect.h
                nw = w if w is not None else ow
                nh = h if h is not None else oh
                widget.rect = pg.Rect(x, y, nw, nh)
        except Exception:
            pass
        # fallback attributes used in some custom components
        try:
            if w is not None:
                widget.w = w
            if h is not None:
                widget.h = h
        except Exception:
            pass

    def _set_shop_tab(self, tab_name: str):
        self.shop_tab = tab_name

    def set_inshop(self, val, npc=None):
        self.in_shop = val
        if not val:
            self.shop_npc = None
            return
        # open shop for npc
        self.shop_npc = npc
        # build local copies for rendering (sprites)
        self.shop_player_items = []
        self.shop_merchant_items = []

        for it in self.game_manager.bag._items_data:
            item = it.copy()
            item["sprite"] = Sprite(item["sprite_path"], (64, 64))
            self.shop_player_items.append(item)

        if hasattr(npc, "inventory"):
            for it in npc.inventory:
                item = it.copy()
                item["sprite"] = Sprite(item["sprite_path"], (64, 64))
                self.shop_merchant_items.append(item)

        # reposition close/tab buttons relative to panel
        screen_w, screen_h = pg.display.get_surface().get_size()
        panel_w, panel_h = int(screen_w * 0.7), int(screen_h * 0.7)
        cx, cy = screen_w // 2, screen_h // 2
        self._set_widget_pos(self.quit_shop_button, cx + panel_w // 2 - 40, cy - panel_h // 2 + 20, 40, 40)
        # place tabs
        self._set_widget_pos(self.shop_buy_tab_btn, cx - panel_w // 2 + 40, cy - panel_h // 2 + 80, 100, 40)
        self._set_widget_pos(self.shop_sell_tab_btn, cx - panel_w // 2 + 150, cy - panel_h // 2 + 80, 100, 40)


    @override
    def enter(self) -> None:
        sound_manager.play_bgm("RBY 103 Pallet Town.ogg")
        if self.online_manager:
            self.online_manager.start()

    @override
    def exit(self) -> None:
        if self.online_manager:
            self.online_manager.exit()

    @override
    def update(self, dt: float):
        # Check if there is assigned next scene
        self.game_manager.try_switch_map()

        if not self.chat_overlay.is_open and not self.in_setting and not self.in_bag and not self.in_shop:
            if input_manager.key_pressed(pg.K_t):
                self.chat_overlay.open()
                # Clear any movement input so player doesn't keep walking while typing
                if self.game_manager.player:
                    self.game_manager.player.moving = False

        # Update Chat Overlay
        self.chat_overlay.update(dt)

        # Only update Player movement if Chat is NOT open
        if self.game_manager.player and not self.chat_overlay.is_open:
            self.game_manager.player.update(dt)

        for enemy in self.game_manager.current_enemy_trainers:
            enemy.update(dt)

        # Update others
        self.game_manager.bag.update(dt)

        # Update Online Players with orientation logic
        if self.game_manager.player is not None and self.online_manager is not None:
            # Send our data
            _ = self.online_manager.update(
                self.game_manager.player.position.x,
                self.game_manager.player.position.y,
                self.game_manager.current_map.path_name,
                self.game_manager.player.moving,
                self.game_manager.player.animation.cur_row,
            )
            
            # Process received data
            online_data = self.online_manager.get_list_players()
            active_ids = set()

            for p_data in online_data:
                pid = p_data.get("id")
                
                # Only draw players on the same map
                if p_data.get("map") != self.game_manager.current_map.path_name:
                    continue
                
                active_ids.add(pid)
                
                # Create animation for new player
                if pid not in self.remote_players:
                    self.remote_players[pid] = Animation(
                        "character/ow1.png", ["down", "left", "right", "up"], 4,
                        (GameSettings.TILE_SIZE, GameSettings.TILE_SIZE)
                    )
                    # Force initial position
                    self.remote_players[pid].update_pos(Position(p_data["x"], p_data["y"]))
                
                anim = self.remote_players[pid]
                target_x = p_data["x"]
                target_y = p_data["y"]
                
                # Calculate direction based on movement (Delta)
                dx = target_x - anim.rect.x
                dy = target_y - anim.rect.y
                
                # Determine orientation
                if p_data["moving"]:
                    anim.switch(p_data["direction"])
                    anim.update(dt) # Cycle animation frames if moving
                else:
                    anim.accumulator = 0 # Stop animation cycle if standing still
                
                # Update position
                anim.update_pos(Position(target_x, target_y))

            # Remove players who disconnected or changed map
            for old_id in list(self.remote_players.keys()):
                if old_id not in active_ids:
                    del self.remote_players[old_id]

        if self.in_setting:
            # widgets were repositioned when opening panel, just update them now
            self.quit_setting_buttom.update(dt)
            self.mute_button.update(dt)
            self.save_button.update(dt)
            self.load_button.update(dt)
            self.volume_slider.update(dt)
            self.volume = self.volume_slider.value
        elif self.in_bag:
            self.quit_bag_button.update(dt)
        elif self.in_shop:
            # update close button & tabs
            self.quit_shop_button.update(dt)
            self.shop_buy_tab_btn.update(dt)
            self.shop_sell_tab_btn.update(dt)

            # check clicks on merch items
            if input_manager.mouse_pressed(1):
                mp = input_manager.mouse_pos
                for rect, idx in getattr(self, "_shop_merchant_item_rects", []):
                    if rect.collidepoint(mp) and self.shop_tab == "buy":
                        self._buy_item(idx)
                        break
                for rect, idx in getattr(self, "_shop_player_item_rects", []):
                    if rect.collidepoint(mp) and self.shop_tab == "sell":
                        self._sell_item(idx)
                        break
        else:
            self.setting_button.update(dt)
            self.bag_button.update(dt)
            if self.game_manager.player:
                for enemy in self.game_manager.current_enemy_trainers:
                    if hasattr(enemy, "is_merchant") and enemy.is_merchant:
                        # distance check
                        player_pos = self.game_manager.player.position
                        if player_pos.distance_to(enemy.position) < GameSettings.TILE_SIZE * 1.4:
                            # show exclamation handled by merchant.detected
                            if input_manager.key_pressed(pg.K_SPACE):
                                self.set_inshop(True, enemy)
                                break
                            # click to open (optional)
                            if input_manager.mouse_pressed(1):
                                # compute sprite rect in world -> screen to detect click on NPC
                                # simple: check enemy.animation.rect collides with mouse pos transformed by camera
                                cam = self.game_manager.player.camera
                                npc_rect = cam.transform_rect(enemy.animation.rect)
                                if npc_rect.collidepoint(input_manager.mouse_pos):
                                    self.set_inshop(True, enemy)
                                    break
        sound_manager.current_bgm.set_volume(self.volume if not self.is_mute else 0)
    
    @override
    def draw(self, screen: pg.Surface):
        # draw map + entities (unchanged)
        if self.game_manager.player:
            camera = self.game_manager.player.camera + PositionCamera(
                self.game_manager.player.animation.rect.width // 2, self.game_manager.player.animation.rect.height // 2
            )
            self.game_manager.current_map.draw(screen, camera)
            self.game_manager.player.draw(screen, camera)
        else:
            camera = PositionCamera(0, 0)
            self.game_manager.current_map.draw(screen, camera)
        for enemy in self.game_manager.current_enemy_trainers:
            enemy.draw(screen, camera)

        # draw bag UI elements (the in-game floating bag, not the bag panel)
        self.game_manager.bag.draw(screen)

        # Draw remote players using their animations
        if self.online_manager and self.game_manager.player:
            for anim in self.remote_players.values():
                anim.draw(screen, camera)

        # ADDED: Draw Minimap (Top Right)
        if self.game_manager.player:
            self._draw_minimap(screen, camera)

        # top-level UI buttons when no panel is open
        if not (self.in_setting or self.in_bag or self.in_shop):
            self.setting_button.draw(screen)
            self.bag_button.draw(screen)
        
        self.chat_overlay.draw(screen)

        # dim background and draw modern rounded panel when a UI is open
        if self.in_setting or self.in_bag or self.in_shop:
            screen_w, screen_h = screen.get_size()
            # dim background
            dark = pg.Surface((screen_w, screen_h), pg.SRCALPHA)
            dark.fill((0, 0, 0, 160))
            screen.blit(dark, (0, 0))

            # central panel size (responsive)
            if self.in_setting:
                panel_w, panel_h = int(screen_w * 0.55), int(screen_h * 0.45)
            else:
                # both bag and shop use the larger panel size
                panel_w, panel_h = int(screen_w * 0.75), int(screen_h * 0.75)
            panel_x = screen_w // 2 - panel_w // 2
            panel_y = screen_h // 2 - panel_h // 2

            # draw shadow
            shadow_surf = pg.Surface((panel_w, panel_h), pg.SRCALPHA)
            pg.draw.rect(shadow_surf, (0, 0, 0, 120), shadow_surf.get_rect(), border_radius=22)
            screen.blit(shadow_surf, (panel_x + 10, panel_y + 10))

            # draw panel
            panel_surf = pg.Surface((panel_w, panel_h), pg.SRCALPHA)
            pg.draw.rect(panel_surf, (18, 18, 18, 230), panel_surf.get_rect(), border_radius=18)
            # subtle inner border
            inner = panel_surf.get_rect().inflate(-4, -4)
            pg.draw.rect(panel_surf, (255, 255, 255, 6), inner, border_radius=16)
            screen.blit(panel_surf, (panel_x, panel_y))

            # header bar
            header_h = 64
            header_rect = pg.Rect(panel_x, panel_y, panel_w, header_h)
            pg.draw.rect(screen, (200, 120, 30), header_rect, border_radius=14)

            # title
            title_font = resource_manager.get_font("Minecraft.ttf", 28)
            if self.in_setting:
                title_text = title_font.render("Settings", True, (10, 10, 10))
            elif self.in_bag:
                title_text = title_font.render("Bag", True, (10, 10, 10))
            else:  # shop
                title_text = title_font.render("Shop", True, (10, 10, 10))
            screen.blit(title_text, (panel_x + 20, panel_y + header_h // 2 - title_text.get_height() // 2))

            # small subtitle on header (like page label)
            sub_font = resource_manager.get_font("Minecraft.ttf", 14)
            subtitle = sub_font.render("Press X or click the close icon to exit", True, (15, 15, 15))
            screen.blit(subtitle, (panel_x + 20, panel_y + header_h - 22))

            # draw the appropriate UI inside the panel
            if self.in_setting:
                self._draw_setting_ui(screen, (panel_x, panel_y, panel_w, panel_h))
            elif self.in_bag:
                self._draw_bag_ui(screen, (panel_x, panel_y, panel_w, panel_h))
            else:
                # shop
                self._draw_shop_ui(screen, (panel_x, panel_y, panel_w, panel_h))

    # --- ADDED: Minimap Drawing Logic ---
    def _draw_minimap(self, screen: pg.Surface, camera: PositionCamera):
        cur_map = self.game_manager.current_map
        
        # 1. Update cached minimap surface if the map has changed
        if self._cached_minimap_path != cur_map.path_name:
            self._cached_minimap_path = cur_map.path_name
            
            # Constants for minimap size
            MAX_MINIMAP_W = 200
            
            # Calculate scale to fit width
            raw_w = cur_map.pixel_width
            raw_h = cur_map.pixel_height
            
            self._minimap_scale = MAX_MINIMAP_W / raw_w
            new_w = int(raw_w * self._minimap_scale)
            new_h = int(raw_h * self._minimap_scale)
            
            # Create scaled version of the map
            self._cached_minimap_surf = pg.transform.scale(cur_map.surface, (new_w, new_h))
            
            # CHANGED: Position minimap at top LEFT
            # Old (Right): self._minimap_rect = pg.Rect(screen.get_width() - new_w - 20, 20, new_w, new_h)
            self._minimap_rect = pg.Rect(20, 20, new_w, new_h)

        if self._cached_minimap_surf and self._minimap_rect:
            # ... rest of the drawing logic remains the same ...
            
            # 2. Draw Minimap Background/Border
            pg.draw.rect(screen, (20, 20, 20), self._minimap_rect.inflate(4, 4))
            pg.draw.rect(screen, (200, 200, 200), self._minimap_rect.inflate(4, 4), 2)
            
            # Blit the map
            screen.blit(self._cached_minimap_surf, self._minimap_rect)
            
            # 3. Draw Player Position
            player = self.game_manager.player
            px = player.position.x
            py = player.position.y
            
            mini_px = self._minimap_rect.x + (px * self._minimap_scale)
            mini_py = self._minimap_rect.y + (py * self._minimap_scale)
            
            pg.draw.circle(screen, (255, 0, 0), (int(mini_px), int(mini_py)), 3)
            
            # 4. Draw Camera View Region
            cam_x = camera.x
            cam_y = camera.y
            view_w = screen.get_width()
            view_h = screen.get_height()
            
            rect_x = self._minimap_rect.x + (cam_x * self._minimap_scale)
            rect_y = self._minimap_rect.y + (cam_y * self._minimap_scale)
            rect_w = view_w * self._minimap_scale
            rect_h = view_h * self._minimap_scale
            
            view_rect = pg.Rect(rect_x, rect_y, rect_w, rect_h)
            
            # Clip view rect to minimap bounds
            view_rect = view_rect.clip(self._minimap_rect)
            
            pg.draw.rect(screen, (255, 255, 255), view_rect, 1)

    def _draw_setting_ui(self, screen: pg.Surface, panel_rect):
        px, py, pw, ph = panel_rect
        # draw close button
        self.quit_setting_buttom.draw(screen)

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

        # draw slider thumb (centered to match underlying slider behavior)
        # we still draw the slider widget so it remains interactive (it was repositioned in set_insetting)
        self.volume_slider.draw(screen)

        # Save / Load buttons
        self.save_button.draw(screen)
        self.load_button.draw(screen)

        # small footer hint
        hint = small_font.render("Saved games are stored in /saves - backup recommended", True, (160, 160, 160))
        screen.blit(hint, (px + 40, py + ph - 40))

    def _draw_bag_ui(self, screen: pg.Surface, panel_rect):
        px, py, pw, ph = panel_rect

        title_font = resource_manager.get_font("Minecraft.ttf", 20)
        label_font = resource_manager.get_font("Minecraft.ttf", 16)

        # layout monsters on the left, items on the right in scrollable-looking panels
        left_w = int(pw * 0.55)
        right_w = pw - left_w - 32
        left_rect = pg.Rect(px + 16, py + 80, left_w, ph - 120)
        right_rect = pg.Rect(px + 24 + left_w, py + 80, right_w, ph - 120)

        # left panel background
        left_surf = pg.Surface((left_rect.w, left_rect.h), pg.SRCALPHA)
        pg.draw.rect(left_surf, (30, 30, 36, 220), left_surf.get_rect(), border_radius=12)
        screen.blit(left_surf, (left_rect.x, left_rect.y))
        # right panel background
        right_surf = pg.Surface((right_rect.w, right_rect.h), pg.SRCALPHA)
        pg.draw.rect(right_surf, (28, 28, 34, 200), right_surf.get_rect(), border_radius=12)
        screen.blit(right_surf, (right_rect.x, right_rect.y))

        mx = left_rect.x + 12
        my = left_rect.y + 12
        card_h = 92
        for monster in self.bag["monsters"]:
            card_rect = pg.Rect(mx, my, left_rect.w - 24, card_h)
            card_surf = pg.Surface((card_rect.w, card_rect.h), pg.SRCALPHA)
            pg.draw.rect(card_surf, (42, 42, 48, 230), card_surf.get_rect(), border_radius=10)
            # small border
            pg.draw.rect(card_surf, (255, 255, 255, 10), card_surf.get_rect(), 1, border_radius=10)
            # sprite area
            sprite_area = pg.Rect(8, 8, 76, 76)
            # draw sprite
            if monster.get("sprite"):
                card_surf.blit(monster["sprite"].image, (sprite_area.x + 4, sprite_area.y + 4))
            # name and stats
            name_text = title_font.render(monster.get("name", "?"), True, (200, 220, 255))
            hp_text = label_font.render(f"HP: {monster.get('hp', 0)}/{monster.get('max_hp', 0)}", True, (180, 255, 200))
            lvl_text = label_font.render(f"Lvl {monster.get('level', 1)}", True, (255, 220, 140))
            card_surf.blit(name_text, (sprite_area.right + 12, 12))
            card_surf.blit(hp_text, (sprite_area.right + 12, 12 + name_text.get_height() + 6))
            card_surf.blit(lvl_text, (sprite_area.right + 12, 12 + name_text.get_height() + hp_text.get_height() + 10))

            screen.blit(card_surf, (card_rect.x, card_rect.y))
            my += card_h + 12

        # items grid on right
        ix = right_rect.x + 12
        iy = right_rect.y + 12
        col_w = 88
        col_h = 88
        per_row = max(1, right_rect.w // (col_w + 12))
        count = 0
        for item in self.bag["items"]:
            cell_x = ix + (count % per_row) * (col_w + 12)
            cell_y = iy + (count // per_row) * (col_h + 18)
            cell_rect = pg.Rect(cell_x, cell_y, col_w, col_h)
            cell_surf = pg.Surface((cell_rect.w, cell_rect.h), pg.SRCALPHA)
            pg.draw.rect(cell_surf, (36, 36, 42, 220), cell_surf.get_rect(), border_radius=10)

            if item.get("sprite"):
                spr = item["sprite"].image
                sw, sh = spr.get_size()
                sx = (col_w - sw) // 2
                sy = (col_h - sh) // 2
                cell_surf.blit(spr, (sx, sy))

            badge = resource_manager.get_font("Minecraft.ttf", 14).render(str(item.get("count", 1)), True, (240, 240, 240))
            screen.blit(cell_surf, (cell_rect.x, cell_rect.y))

            badge_bg = pg.Surface((28, 18), pg.SRCALPHA)
            pg.draw.rect(badge_bg, (200, 80, 30, 220), badge_bg.get_rect(), border_radius=6)
            badge_pos = (cell_rect.x + cell_rect.w - 28 - 6, cell_rect.y + 6)
            screen.blit(badge_bg, badge_pos)
            screen.blit(badge, (badge_pos[0] + 6, badge_pos[1] + 1))

            count += 1

        self.quit_bag_button.draw(screen)
        summary = resource_manager.get_font("Minecraft.ttf", 14).render(
            f"Monsters: {len(self.bag['monsters'])}   Items: {len(self.bag['items'])}", True, (200, 200, 200)
        )
        screen.blit(summary, (px + 24, py + ph - 36))

    def _get_coins_index_and_item(self):
        for idx, it in enumerate(self.game_manager.bag._items_data):
            if it.get("name") == "Coins":
                return idx, it
        return None, None

    def _get_coins_count(self):
        _, it = self._get_coins_index_and_item()
        return it.get("count", 0) if it else 0

    def _change_coins(self, delta: int):
        idx, it = self._get_coins_index_and_item()
        if it is None:
            # create coins if missing
            new_coins = {"name": "Coins", "count": max(0, delta), "sprite_path": "ingame_ui/coin.png"}
            self.game_manager.bag._items_data.append(new_coins)
        else:
            it["count"] = max(0, it.get("count", 0) + delta)
            # if coins drop to 0, keep the item but count 0 (or you can remove it)

    def _buy_item(self, merchant_index: int):
        # defensive bounds
        if merchant_index < 0 or merchant_index >= len(self.shop_merchant_items):
            return
        item = self.shop_merchant_items[merchant_index]
        price = int(item.get("price", 0))
        if price <= 0:
            return
        # check stock (if merchant provides a 'count' field)
        if item.get("count", None) is not None and item.get("count", 0) <= 0:
            # out of stock
            return
        coins = self._get_coins_count()
        if coins < price:
            # not enough coins
            return
        # subtract coins
        self._change_coins(-price)

        # give item to player (ensure we add a fresh dict for player's bag, do not share references with merchant)
        for d in self.game_manager.bag._items_data:
            if d["name"] == item["name"]:
                d["count"] = d.get("count", 0) + 1
                break
        else:
            new_item = {"name": item["name"], "count": 1, "sprite_path": item.get("sprite_path"), "price": item.get("price")}
            self.game_manager.bag._items_data.append(new_item)

        # keep shop player's display in sync (shop_player_items)
        for d in self.shop_player_items:
            if d["name"] == item["name"]:
                d["count"] = d.get("count", 0) + 1
                break
        else:
            new_item_display = {"name": item["name"], "count": 1, "sprite_path": item.get("sprite_path"), "price": item.get("price"), "sprite": Sprite(item.get("sprite_path"), (64, 64))}
            self.shop_player_items.append(new_item_display)

        # decrement merchant stock and underlying NPC inventory when applicable
        if item.get("count", None) is not None:
            item["count"] = max(0, item.get("count", 0) - 1)
            if self.shop_npc and hasattr(self.shop_npc, "inventory"):
                for idx, it in enumerate(self.shop_npc.inventory):
                    if it.get("name") == item.get("name"):
                        it["count"] = max(0, it.get("count", 0) - 1)
                        if it["count"] <= 0:
                            self.shop_npc.inventory.pop(idx)
                        break
            # remove from merchant list if sold out (UI will be rebuilt next frame)
            if item["count"] <= 0:
                self.shop_merchant_items.pop(merchant_index)

    def _sell_item(self, player_index: int):
        # selling uses player's displayed items. We'll remove from game_manager bag
        if player_index < 0 or player_index >= len(self.shop_player_items):
            return
        player_item = self.shop_player_items[player_index]
        sell_price = int(player_item.get("price", 0) // 2) if player_item.get("price") else 1
        # remove first matching item from bag._items_data
        for idx, it in enumerate(self.game_manager.bag._items_data):
            if it.get("name") == player_item.get("name"):
                it["count"] -= 1
                if it["count"] <= 0:
                    self.game_manager.bag._items_data.pop(idx)
                break
        # grant coins
        self._change_coins(sell_price)
        # update displayed list
        for idx, it in enumerate(self.shop_player_items):
            if it.get("name") == player_item.get("name"):
                it["count"] -= 1
                if it["count"] <= 0:
                    self.shop_player_items.pop(idx)
                break

        # Optionally add sold item to merchant stock so player can 'sell' to merchant
        # update underlying npc.inventory and shop_merchant_items
        if self.shop_npc and hasattr(self.shop_npc, "inventory"):
            for d in self.shop_npc.inventory:
                if d.get("name") == player_item.get("name"):
                    d["count"] = d.get("count", 0) + 1
                    break
            else:
                self.shop_npc.inventory.append({"name": player_item["name"], "count": 1, "sprite_path": player_item.get("sprite_path"), "price": player_item.get("price")})

        for d in self.shop_merchant_items:
            if d.get("name") == player_item.get("name"):
                d["count"] = d.get("count", 0) + 1
                break
        else:
            new_it = {"name": player_item["name"], "count": 1, "sprite_path": player_item.get("sprite_path"), "price": player_item.get("price"), "sprite": Sprite(player_item.get("sprite_path"), (64, 64))}
            self.shop_merchant_items.append(new_it)

    def _draw_shop_ui(self, screen: pg.Surface, panel_rect):
        px, py, pw, ph = panel_rect
        title_font = resource_manager.get_font("Minecraft.ttf", 20)
        label_font = resource_manager.get_font("Minecraft.ttf", 16)
        small_font = resource_manager.get_font("Minecraft.ttf", 14)

        # draw close & tabs
        self.quit_shop_button.draw(screen)
        self.shop_buy_tab_btn.draw(screen)
        self.shop_sell_tab_btn.draw(screen)

        # draw tabs style label
        title = title_font.render("Shop - Buy" if self.shop_tab == "buy" else "Shop - Sell", True, (230, 230, 230))
        screen.blit(title, (px + 20, py + 20))

        # layout: left = player items (sell), right = merchant items (buy)
        left_w = int(pw * 0.52)
        right_w = pw - left_w - 32
        left_rect = pg.Rect(px + 16, py + 60, left_w, ph - 100)
        right_rect = pg.Rect(px + 24 + left_w, py + 60, right_w, ph - 100)

        # backgrounds
        left_surf = pg.Surface((left_rect.w, left_rect.h), pg.SRCALPHA)
        pg.draw.rect(left_surf, (30, 30, 36, 220), left_surf.get_rect(), border_radius=12)
        screen.blit(left_surf, (left_rect.x, left_rect.y))

        right_surf = pg.Surface((right_rect.w, right_rect.h), pg.SRCALPHA)
        pg.draw.rect(right_surf, (28, 28, 34, 200), right_surf.get_rect(), border_radius=12)
        screen.blit(right_surf, (right_rect.x, right_rect.y))

        # draw player items (for selling)
        mx = left_rect.x + 12
        my = left_rect.y + 12
        card_h = 80
        self._shop_player_item_rects = []
        for i, monster in enumerate(self.shop_player_items):
            card_rect = pg.Rect(mx, my, left_rect.w - 24, card_h)
            card_surf = pg.Surface((card_rect.w, card_rect.h), pg.SRCALPHA)
            pg.draw.rect(card_surf, (42, 42, 48, 230), card_surf.get_rect(), border_radius=10)
            # icon
            if monster.get("sprite"):
                card_surf.blit(monster["sprite"].image, (8 + 4, 8 + 4))
            # name/qty
            name_text = label_font.render(monster.get("name", "?"), True, (200, 220, 255))
            screen.blit(card_surf, (card_rect.x, card_rect.y))
            screen.blit(name_text, (card_rect.x + 88, card_rect.y + 12))
            # sell price (use half of merchant price if present or fallback)
            sell_price = monster.get("price", None)
            if sell_price is None:
                sell_text = label_font.render("Sell: ? ", True, (200, 200, 200))
            else:
                sell_text = label_font.render(f"Sell: {int(sell_price//2)}", True, (200, 200, 200))
            screen.blit(sell_text, (card_rect.x + 88, card_rect.y + 40))

            # draw a small "Sell" clickable area
            sell_btn_rect = pg.Rect(card_rect.right - 80, card_rect.y + 16, 64, 32)
            pg.draw.rect(screen, (200, 80, 30), sell_btn_rect, border_radius=6)
            sell_lbl = small_font.render("Sell", True, (255, 255, 255))
            screen.blit(sell_lbl, (sell_btn_rect.x + 12, sell_btn_rect.y + 6))

            self._shop_player_item_rects.append((sell_btn_rect, i))
            my += card_h + 10

        # draw merchant items (for buying) and show stock counts
        ix = right_rect.x + 12
        iy = right_rect.y + 12
        col_h = 76
        self._shop_merchant_item_rects = []
        for i, item in enumerate(self.shop_merchant_items):
            card_rect = pg.Rect(ix, iy + i * (col_h + 8), right_rect.w - 24, col_h)
            card_surf = pg.Surface((card_rect.w, card_rect.h), pg.SRCALPHA)
            pg.draw.rect(card_surf, (42, 42, 48, 230), card_surf.get_rect(), border_radius=10)
            if item.get("sprite"):
                card_surf.blit(item["sprite"].image, (8 + 4, 8 + 4))
            screen.blit(card_surf, (card_rect.x, card_rect.y))

            name_text = label_font.render(item.get("name", "?"), True, (200, 220, 255))
            price_text = label_font.render(f"Price: {item.get('price', '?')}", True, (200, 200, 200))
            screen.blit(name_text, (card_rect.x + 88, card_rect.y + 10))
            screen.blit(price_text, (card_rect.x + 88, card_rect.y + 36))

            # stock display (if merchant provides 'count')
            stock_val = item.get("count", None)
            if stock_val is None:
                stock_text = label_font.render("Stock: ∞", True, (180, 180, 180))
            else:
                stock_text = label_font.render(f"Stock: {stock_val}", True, (180, 180, 180))
            screen.blit(stock_text, (card_rect.x + 88, card_rect.y + 56))

            # player's owned count (mimic bag badge)
            player_count = 0
            for it in self.game_manager.bag._items_data:
                if it.get("name") == item.get("name"):
                    player_count = it.get("count", 0)
                    break
            badge = resource_manager.get_font("Minecraft.ttf", 14).render(str(player_count), True, (240, 240, 240))
            badge_bg = pg.Surface((28, 18), pg.SRCALPHA)
            pg.draw.rect(badge_bg, (200, 80, 30, 220), badge_bg.get_rect(), border_radius=6)
            # place badge left of buy button
            buy_btn_rect = pg.Rect(card_rect.right - 80, card_rect.y + 18, 64, 32)
            badge_pos = (buy_btn_rect.x - 34, card_rect.y + 6)
            screen.blit(badge_bg, badge_pos)
            screen.blit(badge, (badge_pos[0] + 6, badge_pos[1] + 1))

            buy_btn_rect = pg.Rect(card_rect.right - 80, card_rect.y + 18, 64, 32)
            # if out of stock, show greyed "Sold" button
            if stock_val is not None and stock_val <= 0:
                pg.draw.rect(screen, (120, 120, 120), buy_btn_rect, border_radius=6)
                sold_lbl = small_font.render("Sold", True, (220, 220, 220))
                screen.blit(sold_lbl, (buy_btn_rect.x + 12, buy_btn_rect.y + 6))
            else:
                pg.draw.rect(screen, (40, 160, 40), buy_btn_rect, border_radius=6)
                buy_lbl = small_font.render("Buy", True, (255, 255, 255))
                screen.blit(buy_lbl, (buy_btn_rect.x + 18, buy_btn_rect.y + 6))
                # only clickable if in stock
                self._shop_merchant_item_rects.append((buy_btn_rect, i))

        # footer: show coins
        coins = self._get_coins_count()
        coin_text = label_font.render(f"Coins: {coins}", True, (220, 220, 180))
        screen.blit(coin_text, (px + 24, py + ph - 36))
    
    def _on_chat_send(self, msg: str) -> bool:
        """Called when user presses Enter in ChatOverlay."""
        if self.online_manager:
            # Assuming online_manager has a method to send chat
            # You might need to add `send_chat` to your OnlineManager class
            try:
                self.online_manager.send_chat(msg) 
                return True
            except AttributeError:
                Logger.error("OnlineManager missing 'send_chat' method")
        return False

    def _get_chat_messages(self, limit: int) -> list[dict]:
        """Called by ChatOverlay to get recent messages."""
        if self.online_manager:
            # Assuming online_manager stores messages in a list
            # You might need to add `get_chat_history` to your OnlineManager class
            try:
                return self.online_manager.get_chat_history(limit)
            except AttributeError:
                return []
        return []