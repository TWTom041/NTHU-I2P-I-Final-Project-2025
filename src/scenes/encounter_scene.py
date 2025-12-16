import random
from typing import Optional, List, Dict
from copy import deepcopy

import pygame as pg

from src.sprites import BackgroundSprite, Sprite
from src.scenes.scene import Scene
from src.interface.components import Button
from src.core.services import scene_manager, sound_manager, input_manager, resource_manager
from src.utils.definition import Position, Monster
from src.data.bag import Bag


class EncounterScene(Scene):
    background: BackgroundSprite

    battle_button: Button
    item_button: Button
    switch_button: Button
    run_button: Button
    catch_button: Button

    dialog_box: pg.Surface

    player_monster: Dict
    enemy_monster: Dict

    load_cycle_counter: int
    max_load_cycle = 30

    def __init__(self) -> None:
        super().__init__()

        self.background = BackgroundSprite("backgrounds/background2.png")

        self.battle_button = Button(
            "UI/button_battle.png", "UI/button_battle_hover.png",
            640, 510, 150, 90,
            self.battle_action
        )
        self.item_button = Button(
            "UI/button_item.png", "UI/button_item_hover.png",
            840, 510, 150, 90,
            self.item_action
        )
        self.switch_button = Button(
            "UI/button_switch.png", "UI/button_switch_hover.png",
            640, 610, 150, 90,
            self.switch_action
        )
        self.run_button = Button(
            "UI/button_run.png", "UI/button_run_hover.png",
            840, 610, 150, 90,
            self.run_action
        )
        # New catch button
        self.catch_button = Button(
            "UI/button_catch.png", "UI/button_catch_hover.png",
            1040, 510, 150, 90,
            self.catch_action
        )

        # dialog box
        self.dialog_box = pg.Surface((1000, 300))
        self.dialog_box.fill((180, 80, 0))

        # placeholders for monsters (dicts with monster + sprite)
        self.player_monster = {}
        self.enemy_monster = {}

        # event queue
        # event dict fields:
        #   show_dialog: bool
        #   show_interaction: bool
        #   dialog_text: str
        #   actions: List[str] (optional)
        #   await_input: bool  (internal control to wait for SPACE after action)
        #   end: bool (if True, popping this event will trigger exiting the scene)
        self.event_chain: List[Dict] = []

        self.load_cycle_counter = 0

    def _enqueue_event(self, dialog_text: str = "", show_interaction: bool = False,
                       actions: Optional[List[str]] = None, end: bool = False, await_input : bool = False) -> None:
        if actions is None:
            actions = []
        self.event_chain.append({
            "show_dialog": True,
            "show_interaction": show_interaction,
            "dialog_text": dialog_text,
            "actions": actions,
            "await_input": await_input,
            "end": end,
        })

    def battle_action(self) -> None:
        if not self.event_chain:
            self._enqueue_event("You strike!", show_interaction=False, actions=["player_attack", "enemy_attack", "refill"])
            return
        current = self.event_chain[0]
        if current.get("show_interaction", False):
            current["show_interaction"] = False
            current["actions"] = ["player_attack", "enemy_attack", "refill"]
            current["dialog_text"] = ""
            current["await_input"] = False

    def item_action(self) -> None:
        """TODO: Implement item"""
        if not self.event_chain:
            self._enqueue_event("You use an item.", show_interaction=False, actions=["use_item", "refill"])
            return
        current = self.event_chain[0]
        if current.get("show_interaction", False):
            current["show_interaction"] = False
            current["actions"] = ["use_item", "refill"]
            current["dialog_text"] = ""
            current["await_input"] = False

    def switch_action(self) -> None:
        """TODO: Implement actual swapping"""
        if not self.event_chain:
            self._enqueue_event("You switch monsters (placeholder).", show_interaction=False, actions=["switch_monster", "refill"])
            return
        current = self.event_chain[0]
        if current.get("show_interaction", False):
            current["show_interaction"] = False
            current["actions"] = ["switch_monster", "refill"]
            current["dialog_text"] = ""
            current["await_input"] = False

    def run_action(self) -> None:
        """Run away: stop bgm and return to game scene."""
        try:
            sound_manager.stop_bgm()
        except Exception:
            pass
        scene_manager.change_scene("game")

    def catch_action(self) -> None:
        """Player attempts to catch the wild monster."""
        if not self.event_chain:
            # initial
            self._enqueue_event("You throw a Ball!", show_interaction=False, actions=["attempt_catch", "refill"])
            return
        current = self.event_chain[0]
        if current.get("show_interaction", False):
            current["show_interaction"] = False
            current["actions"] = ["attempt_catch", "refill"]
            current["dialog_text"] = ""
            current["await_input"] = False

    def enter(self) -> None:
        try:
            sound_manager.play_bgm("RBY 110 Battle! (Wild Pokemon).ogg")
        except Exception:
            pass

        self.load_cycle_counter = 0

        _enemy_sprite = f"menu_sprites/menusprite{random.randint(1, 16)}.png"
        enemy_monster: Monster = {
            "name": "Wild Fiend",
            "hp": 80,
            "max_hp": 80,
            "level": 5,
            "sprite_path": _enemy_sprite
        }
        enemy_sprite = Sprite(enemy_monster["sprite_path"], (200, 200))
        enemy_sprite.update_pos(Position(950, 100))
        self.enemy_monster = {"monster": enemy_monster, "sprite": enemy_sprite}

        self.player_bag: Bag = scene_manager._scenes["game"].game_manager.bag
        player_mon: Monster = self.player_bag._monsters_data[0]
        player_sprite = Sprite(player_mon["sprite_path"], (200, 200))
        player_sprite.update_pos(Position(100, 250))
        self.player_monster = {"monster": player_mon, "sprite": player_sprite}

        self.event_chain = []
        self._enqueue_event("A wild monster appears!", show_interaction=False)
        self._enqueue_event("Get ready!", show_interaction=False)
        self._enqueue_event("What will you do?", show_interaction=True)

    def exit(self) -> None:
        """Cleanup when leaving the scene."""
        try:
            sound_manager.stop_bgm()
        except Exception:
            pass

    def _handle_action(self, action: str) -> None:
        if not self.event_chain:
            return

        current = self.event_chain[0]

        pm = self.player_monster.get("monster") if self.player_monster else None
        em = self.enemy_monster.get("monster") if self.enemy_monster else None

        if em is None:
            if action == "attempt_catch":
                current["dialog_text"] = "There's nothing to catch!"
                current["await_input"] = True
                return
            if action == "enemy_attack":
                current["dialog_text"] = "The foe is gone."
                current["await_input"] = True
                return
            if action == "player_attack":
                current["dialog_text"] = "No target to attack."
                current["await_input"] = True
                return
            if action == "refill":
                current["dialog_text"] = current.get("dialog_text", "") + " Round ends."
                current["await_input"] = True
                # If encounter ended already, go back to game (or re-open interaction)
                if not current.get("end", False):
                    self._enqueue_event("Choose your next action.", show_interaction=True)
                return
        
        # If there's no player monster (shouldn't normally happen)
        if pm is None and action in ("player_attack", "use_item", "switch_monster"):
            current["dialog_text"] = "You have no active monster to do that."
            current["await_input"] = True
            return

        pm_hp = pm.get("hp", 0) if pm else 0
        pm_max = pm.get("max_hp", pm_hp) if pm else pm_hp
        em_hp = em.get("hp", 0) if em else 0
        em_max = em.get("max_hp", em_hp) if em else em_hp

        if action == "player_attack":
            base_attack = max(1, pm.get("level", 1) * 2)
            dmg = max(1, base_attack + random.randint(-2, 2))
            em["hp"] = max(0, em_hp - dmg)
            current["dialog_text"] = f"{pm['name']} attacks! {em['name']} loses {dmg} HP."
            current["await_input"] = True
            if em["hp"] == 0:
                current["dialog_text"] += f" {em['name']} fainted!"
                self.enemy_monster = None

                self._enqueue_event("You won the battle!", show_interaction=False)
                self._enqueue_event("Press SPACE to continue.", show_interaction=False, end=True)
            return

        if action == "enemy_attack":
            if em is None or em.get("hp", 0) <= 0:
                current["dialog_text"] = f"The foe can't attack — it's already down."
                current["await_input"] = True
                return

            base_attack = max(1, em.get("level", 1) * 2)
            dmg = max(1, base_attack + random.randint(-2, 2))
            pm["hp"] = max(0, pm_hp - dmg)
            current["dialog_text"] = f"{em['name']} hits back! {pm['name']} loses {dmg} HP."
            current["await_input"] = True
            if pm["hp"] == 0:
                current["dialog_text"] += f" {pm['name']} fainted!"
                self._enqueue_event("You lost the battle...", show_interaction=False)
                self._enqueue_event("Press SPACE to continue.", show_interaction=False, end=True)
            else:
                flee_chance = 0.05 + (em.get("hp", 0) / max(1, em.get("max_hp", 1))) * 0.10
                if random.random() < flee_chance:
                    self._enqueue_event(f"{em['name']} ran away!", show_interaction=False, end=True)
            return

        if action == "refill":
            current["dialog_text"] = current.get("dialog_text", "") + " Round ends."
            current["await_input"] = True
            if not current.get("end", False):
                self._enqueue_event("Choose your next action.", show_interaction=True)
            return

        if action == "use_item":
            heal_amount = 20
            new_hp = min(pm.get("max_hp", pm.get("hp", 0)), pm.get("hp", 0) + heal_amount)
            healed = new_hp - pm.get("hp", 0)
            pm["hp"] = new_hp
            current["dialog_text"] = f"You used a potion! {pm['name']} healed {healed} HP."
            current["await_input"] = True
            return

        if action == "switch_monster":
            current["dialog_text"] = "You attempt to switch monsters — placeholder (no change)."
            current["await_input"] = True
            return

        if action == "attempt_catch":
            # Calculate catch probability
            em_hp = em.get("hp", 0)
            em_max = em.get("max_hp", 1)
            hp_ratio = em_hp / max(1, em_max)
            hp_ratio = max(0.0, min(1.0, hp_ratio))

            base_min = 0.05
            scale = 0.80
            catch_prob = base_min + (1.0 - hp_ratio) * scale
            catch_prob = max(0.01, min(0.99, catch_prob))

            roll = random.random()
            if roll < catch_prob:
                # success: add a copy of the monster to player's bag retaining stats
                caught_mon = deepcopy(em)
                caught_entry = {
                    "name": caught_mon.get("name"),
                    "hp": caught_mon.get("hp"),
                    "max_hp": caught_mon.get("max_hp"),
                    "level": caught_mon.get("level"),
                    "sprite_path": caught_mon.get("sprite_path")
                }
                try:
                    self.player_bag._monsters_data.append(caught_entry)
                except Exception:
                    # Fallback if Bag API differs; try a hypothetical add_monster
                    try:
                        self.player_bag.add_monster(caught_entry)  # type: ignore
                    except Exception:
                        current["dialog_text"] = "Caught it — but couldn't add to bag due to Bag API mismatch."
                        current["await_input"] = True
                        # make this the final event so popping returns to game
                        current["end"] = True
                        # ensure there are no leftover events after this one
                        self.event_chain = [current]
                        # hide enemy sprite safely
                        self.enemy_monster = None
                        return

                current["dialog_text"] = f"Great! You caught {em.get('name')}!"
                current["await_input"] = True
                current["end"] = True
                self.event_chain = [current]
                self.enemy_monster = None
                return
            else:
                current["dialog_text"] = f"The ball failed to catch {em.get('name')}!"
                current["await_input"] = True
                run_chance = 0.3 + hp_ratio * 0.45
                if random.random() < run_chance:
                    self._enqueue_event(f"{em.get('name')} ran away!", show_interaction=False, end=True, await_input=True)
                else:
                    self._enqueue_event("", show_interaction=False, actions=["enemy_attack", "refill"])
            return

        current["dialog_text"] = f"(Unknown action: {action})"
        current["await_input"] = True

    def update(self, dt: float) -> None:
        if self.load_cycle_counter < self.max_load_cycle:
            self.load_cycle_counter += 1
            return

        if not self.event_chain:
            self.exit()
            scene_manager.change_scene("game")
            return

        current = self.event_chain[0]

        if current.get("await_input", False):
            if input_manager.key_pressed(pg.K_SPACE):
                current["await_input"] = False
                if not current.get("actions") and not current.get("show_interaction", False):
                    popped = self.event_chain.pop(0)
                    if popped.get("end", False):
                        self.exit()
                        scene_manager.change_scene("game")
                        return
            return

        if current.get("actions"):
            action = current["actions"].pop(0)
            self._handle_action(action)
            return

        if current.get("show_interaction", False):
            self.battle_button.update(dt)
            self.switch_button.update(dt)
            self.item_button.update(dt)
            self.run_button.update(dt)
            self.catch_button.update(dt)

        if input_manager.key_pressed(pg.K_SPACE) and not current.get("show_interaction", False) and not current.get("await_input", False):
            popped = self.event_chain.pop(0)
            if popped.get("end", False):
                self.exit()
                scene_manager.change_scene("game")
                return

    def _draw_hp_bar(self, screen: pg.Surface, x: int, y: int, w: int, h: int, current: int, maximum: int) -> None:
        pg.draw.rect(screen, (0, 0, 0), (x - 2, y - 2, w + 4, h + 4))
        pg.draw.rect(screen, (80, 80, 80), (x, y, w, h))
        ratio = 0.0
        if maximum > 0:
            ratio = max(0.0, min(1.0, current / maximum))
        inner_w = int(w * ratio)
        pg.draw.rect(screen, (0, 200, 0), (x, y, inner_w, h))

    def draw(self, screen: pg.Surface) -> None:
        self.background.draw(screen)

        if self.load_cycle_counter < self.max_load_cycle:
            opacity = self.load_cycle_counter / self.max_load_cycle
            if self.player_monster:
                self.player_monster["sprite"].draw(screen, opacity=opacity)
            if self.enemy_monster:
                self.enemy_monster["sprite"].draw(screen, opacity=opacity)
            return

        if self.player_monster:
            self.player_monster["sprite"].draw(screen)
        if self.enemy_monster:
            # only draw if there's an enemy
            if self.enemy_monster:
                self.enemy_monster["sprite"].draw(screen)

        if self.player_monster and self.enemy_monster:
            pm = self.player_monster["monster"]
            em = self.enemy_monster["monster"]

            self._draw_hp_bar(screen, 120, 220, 200, 18, pm.get("hp", 0), pm.get("max_hp", 1))
            font = resource_manager.get_font("Minecraft.ttf", 20)
            screen.blit(font.render(f"{pm.get('name', '')} {pm.get('hp', 0)}/{pm.get('max_hp', 0)}", True, (255, 255, 255)), (120, 195))

            self._draw_hp_bar(screen, 780, 80, 200, 18, em.get("hp", 0), em.get("max_hp", 1))
            screen.blit(font.render(f"{em.get('name', '')} {em.get('hp', 0)}/{em.get('max_hp', 0)}", True, (255, 255, 255)), (780, 55))

        if self.event_chain:
            current = self.event_chain[0]
            if current.get("show_dialog", False):
                screen.blit(self.dialog_box, (100, 500))
                font = resource_manager.get_font("Minecraft.ttf", 30)
                lines = current.get("dialog_text", "").split("\n")
                y = 520
                for line in lines:
                    screen.blit(font.render(line, True, (0, 255, 0)), (120, y))
                    y += font.get_height() + 4

            if current.get("show_interaction", False):
                self.battle_button.draw(screen)
                self.switch_button.draw(screen)
                self.item_button.draw(screen)
                self.run_button.draw(screen)
                self.catch_button.draw(screen)
