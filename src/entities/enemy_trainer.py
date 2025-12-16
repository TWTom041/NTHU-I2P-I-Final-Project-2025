# enemy_trainer.py  (replace/merge)
from __future__ import annotations
import pygame
from enum import Enum
from dataclasses import dataclass
from typing import override

from .entity import Entity
from src.sprites import Sprite
from src.core import GameManager
from src.core.services import input_manager, scene_manager
from src.utils import GameSettings, Direction, Position, PositionCamera


class EnemyTrainerClassification(Enum):
    STATIONARY = "stationary"
    # new merchant "classification" string allowed in JSON
    MERCHANT = "merchant"


@dataclass
class IdleMovement:
    def update(self, enemy: "EnemyTrainer", dt: float) -> None:
        return


class EnemyTrainer(Entity):
    classification: EnemyTrainerClassification
    max_tiles: int | None
    _movement: IdleMovement
    warning_sign: Sprite
    detected: bool
    los_direction: Direction

    @override
    def __init__(
        self,
        x: float,
        y: float,
        game_manager: GameManager,
        classification: EnemyTrainerClassification = EnemyTrainerClassification.STATIONARY,
        max_tiles: int | None = 2,
        facing: Direction | None = None,
    ) -> None:
        super().__init__(x, y, game_manager)
        self.classification = classification
        self.max_tiles = max_tiles
        if classification == EnemyTrainerClassification.STATIONARY:
            self._movement = IdleMovement()
            if facing is None:
                raise ValueError("Idle EnemyTrainer requires a 'facing' Direction at instantiation")
            self._set_direction(facing)
        else:
            raise ValueError("Invalid classification")
        self.warning_sign = Sprite("exclamation.png", (GameSettings.TILE_SIZE // 2, GameSettings.TILE_SIZE // 2))
        self.warning_sign.update_pos(Position(x + GameSettings.TILE_SIZE // 4, y - GameSettings.TILE_SIZE // 2))
        self.detected = False

    @override
    def update(self, dt: float) -> None:
        self._movement.update(self, dt)
        self._has_los_to_player()
        # default behaviour: start battle when detected + space
        if self.detected and input_manager.key_pressed(pygame.K_SPACE):
            scene_manager.change_scene("battle")
        self.animation.update_pos(self.position)

    @override
    def draw(self, screen: pygame.Surface, camera: PositionCamera) -> None:
        super().draw(screen, camera)
        if self.detected:
            self.warning_sign.draw(screen, camera)
        if GameSettings.DRAW_HITBOXES:
            los_rect = self._get_los_rect()
            if los_rect is not None:
                pygame.draw.rect(screen, (255, 255, 0), camera.transform_rect(los_rect), 1)

    def _set_direction(self, direction: Direction) -> None:
        self.direction = direction
        if direction == Direction.RIGHT:
            self.animation.switch("right")
        elif direction == Direction.LEFT:
            self.animation.switch("left")
        elif direction == Direction.DOWN:
            self.animation.switch("down")
        else:
            self.animation.switch("up")
        self.los_direction = self.direction

    def _get_los_rect(self) -> pygame.Rect | None:
        ex, ey, ew, eh = self.animation.rect  # enemy rect

        if self.direction == Direction.RIGHT:
            candidates = [b for b in self.game_manager.current_map._collision_map
                        if b.y == ey and b.x > ex]
            if not candidates:
                return None
            border = min(candidates, key=lambda b: b.x)
            width = border.x - (ex + ew)
            return pygame.Rect(ex + ew, ey, width, eh)

        elif self.direction == Direction.LEFT:
            candidates = [b for b in self.game_manager.current_map._collision_map
                        if b.y == ey and b.x < ex]
            if not candidates:
                return None
            border = max(candidates, key=lambda b: b.x)
            width = (ex - border.x)
            return pygame.Rect(border.x, ey, width, eh)

        elif self.direction == Direction.UP:
            candidates = [b for b in self.game_manager.current_map._collision_map
                        if b.x == ex and b.y < ey]
            if not candidates:
                return None
            border = max(candidates, key=lambda b: b.y)
            height = (ey - border.y)
            return pygame.Rect(ex, border.y, ew, height)

        elif self.direction == Direction.DOWN:
            candidates = [b for b in self.game_manager.current_map._collision_map
                        if b.x == ex and b.y > ey]
            if not candidates:
                return None
            border = min(candidates, key=lambda b: b.y)
            height = (border.y - (ey + eh))
            return pygame.Rect(ex, ey + eh, ew, height)

        return None

    def _has_los_to_player(self) -> None:
        player = self.game_manager.player
        if player is None:
            self.detected = False
            return
        los_rect = self._get_los_rect()
        if los_rect is None:
            self.detected = False
            return
        if los_rect.colliderect(player.animation.rect):
            self.detected=True
        else:
            self.detected = False

    @classmethod
    @override
    def from_dict(cls, data: dict, game_manager: GameManager) -> "EnemyTrainer":
        # If the JSON marks this trainer as a merchant, construct a Merchant instance
        raw_class = data.get("classification", "stationary")
        facing_val = data.get("facing")
        facing = None
        if facing_val is not None:
            if isinstance(facing_val, str):
                try:
                    facing = Direction[facing_val]
                except Exception:
                    facing = None
            elif isinstance(facing_val, Direction):
                facing = facing_val

        if raw_class == EnemyTrainerClassification.MERCHANT.value:
            # import locally to avoid circulars
            return Merchant.from_dict(data, game_manager)

        classification = EnemyTrainerClassification(raw_class)
        max_tiles = data.get("max_tiles")
        if facing is None and classification == EnemyTrainerClassification.STATIONARY:
            facing = Direction.DOWN
        return cls(
            data["x"] * GameSettings.TILE_SIZE,
            data["y"] * GameSettings.TILE_SIZE,
            game_manager,
            classification,
            max_tiles,
            facing,
        )

    @override
    def to_dict(self) -> dict[str, object]:
        base: dict[str, object] = super().to_dict()
        base["classification"] = self.classification.value
        base["facing"] = self.direction.name
        base["max_tiles"] = self.max_tiles
        return base


# ---------------------------
# Merchant subclass
# ---------------------------
class Merchant(EnemyTrainer):
    """
    A simple merchant NPC. Keeps its own inventory list of item dicts:
      { "name": str, "price": int, "sprite_path": str, "count": int }
    """
    inventory: list[dict]
    is_merchant: bool

    def __init__(
        self,
        x: float,
        y: float,
        game_manager: GameManager,
        facing: Direction | None = None,
        inventory: list[dict] | None = None,
    ) -> None:
        # merchant behaves stationary
        super().__init__(x, y, game_manager, EnemyTrainerClassification.STATIONARY, 0, facing or Direction.DOWN)
        self.inventory = inventory or []
        self.is_merchant = True

    @override
    def update(self, dt: float) -> None:
        # Merchant doesn't do LOS-battle; but keep detection (for exclamation) to show interaction hint
        self._movement.update(self, dt)
        # show hint if player is close enough
        player = self.game_manager.player
        if player is None:
            self.detected = False
        else:
            # interact range — tile distance threshold
            if player.position.distance_to(self.position) < GameSettings.TILE_SIZE * 1.4:
                self.detected = True
            else:
                self.detected = False

        # Merchant interaction is handled by GameScene (press space to open shop)
        self.animation.update_pos(self.position)

    @classmethod
    def from_dict(cls, data: dict, game_manager: GameManager) -> "Merchant":
        facing_val = data.get("facing")
        facing = None
        if facing_val is not None:
            if isinstance(facing_val, str):
                try:
                    facing = Direction[facing_val]
                except Exception:
                    facing = None
            elif isinstance(facing_val, Direction):
                facing = facing_val
        inv = data.get("inventory", [])
        return cls(data["x"] * GameSettings.TILE_SIZE, data["y"] * GameSettings.TILE_SIZE, game_manager, facing, inv)

    def to_dict(self) -> dict[str, object]:
        base = super().to_dict()
        base["classification"] = EnemyTrainerClassification.MERCHANT.value
        base["inventory"] = self.inventory
        return base
