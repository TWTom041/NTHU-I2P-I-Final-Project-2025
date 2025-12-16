from __future__ import annotations
import pygame as pg
from .entity import Entity
from src.core.services import input_manager, scene_manager
from src.utils import Position, PositionCamera, GameSettings, Logger
from src.core import GameManager
import math
from typing import override
import random
import heapq  # Required for A* Priority Queue

class Player(Entity):
    speed: float = 4.0 * GameSettings.TILE_SIZE
    game_manager: GameManager
    bush_counter: int
    max_bush_counter: int
    moving: bool = False
    mouse_released: bool = False
    
    # Pathfinding properties
    path: list[Position] = [] 
    target_node: Position | None = None

    def __init__(self, x: float, y: float, game_manager: GameManager) -> None:
        super().__init__(x, y, game_manager)
        self.bush_counter = 0
        self.max_bush_counter = random.randint(5*60, 10*60)
        self.path = []

    def get_grid_pos(self, pos: Position) -> tuple[int, int]:
        """Helper to convert world pixel coordinates to grid indices."""
        return int(pos.x // GameSettings.TILE_SIZE), int(pos.y // GameSettings.TILE_SIZE)

    def a_star_search(self, start_pos: Position, end_pos: Position) -> list[Position]:
        """Calculates the path from start to end using A* algorithm."""
        start_node = self.get_grid_pos(start_pos)
        end_node = self.get_grid_pos(end_pos)
        
        # 1. OPTIMIZATION: Check if destination is the same as start
        if start_node == end_node:
            return []

        # 2. CRITICAL FIX: Check if destination is a collision block (Wall/Obstacle)
        # We construct a Rect for the target grid cell to check against the map's collision list
        target_rect = pg.Rect(
            end_node[0] * GameSettings.TILE_SIZE, 
            end_node[1] * GameSettings.TILE_SIZE, 
            GameSettings.TILE_SIZE, 
            GameSettings.TILE_SIZE
        )
        
        # If the destination is a wall or a trainer, return immediately.
        # This prevents the A* from searching the entire map for an unreachable point (the "Infinite Loop" freeze).
        if self.game_manager.current_map.check_collision(target_rect) or \
           any(target_rect.colliderect(e.animation.rect) for e in self.game_manager.current_enemy_trainers):
            Logger.info("Destination is invalid (Collision/Occupied). Autopilot cancelled.")
            return []

        # --- Standard A* Implementation ---
        open_set = []
        heapq.heappush(open_set, (0, start_node[0], start_node[1]))
        came_from = {}
        g_score = {start_node: 0}
        f_score = {start_node: abs(start_node[0] - end_node[0]) + abs(start_node[1] - end_node[1])}
        open_set_hash = {start_node}

        while open_set:
            current = heapq.heappop(open_set)
            current_node = (current[1], current[2])
            open_set_hash.remove(current_node)

            if current_node == end_node:
                path = []
                while current_node in came_from:
                    pixel_x = current_node[0] * GameSettings.TILE_SIZE
                    pixel_y = current_node[1] * GameSettings.TILE_SIZE
                    path.append(Position(pixel_x, pixel_y))
                    current_node = came_from[current_node]
                path.reverse()
                return path

            neighbors = [(0, 1), (0, -1), (1, 0), (-1, 0)]
            
            for dx, dy in neighbors:
                neighbor = (current_node[0] + dx, current_node[1] + dy)
                
                check_rect = pg.Rect(
                    neighbor[0] * GameSettings.TILE_SIZE, 
                    neighbor[1] * GameSettings.TILE_SIZE, 
                    GameSettings.TILE_SIZE, 
                    GameSettings.TILE_SIZE
                )
                
                if self.game_manager.current_map.check_collision(check_rect):
                    continue

                tentative_g_score = g_score[current_node] + 1

                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current_node
                    g_score[neighbor] = tentative_g_score
                    h_score = abs(neighbor[0] - end_node[0]) + abs(neighbor[1] - end_node[1])
                    f_score[neighbor] = tentative_g_score + h_score
                    
                    if neighbor not in open_set_hash:
                        heapq.heappush(open_set, (f_score[neighbor], neighbor[0], neighbor[1]))
                        open_set_hash.add(neighbor)
        
        return []

    @override
    def update(self, dt: float) -> None:
        dis = Position(0, 0)
        
        # --- AUTO PILOT INPUT ---
        # If Mouse Left Click, Calculate Path
        if pg.mouse.get_pressed()[0] and self.mouse_released:
            self.mouse_released = False
            mx, my = pg.mouse.get_pos()
            # Convert screen mouse pos to world pos using camera
            cam_x = int(self.position.x) - GameSettings.SCREEN_WIDTH // 2
            cam_y = int(self.position.y) - GameSettings.SCREEN_HEIGHT // 2
            
            target_world_pos = Position(mx + cam_x, my + cam_y)
            game_scene = scene_manager._scenes["game"]

            if not(my < 140 or game_scene.in_setting or game_scene.in_bag or game_scene.in_shop):
                # Run A*
                new_path = self.a_star_search(self.position, target_world_pos)
                if new_path:
                    self.path = new_path
                    self.moving = True
        elif not pg.mouse.get_pressed()[0]:
            self.mouse_released = True

        # --- MOVEMENT LOGIC ---
        # If we have a path, follow it
        if self.path:
            target = self.path[0]
            
            # Calculate direction vector
            dx = target.x - self.position.x
            dy = target.y - self.position.y
            
            # Snap if very close to the node (tolerance)
            if math.sqrt(dx**2 + dy**2) < (self.speed * dt) * 1.5:
                self.position.x = target.x
                self.position.y = target.y
                self.path.pop(0) # Remove visited node
                
                # Stop if path is finished
                if not self.path:
                    self.moving = False
            else:
                # Normalize manually to direction (-1, 0, or 1) for the animation switch logic
                if abs(dx) > abs(dy):
                    dis.x = 1 if dx > 0 else -1
                else:
                    dis.y = 1 if dy > 0 else -1
                
                # Determine animation based on auto-pilot direction
                if dis.y > 0: self.animation.switch("down")
                elif dis.y < 0: self.animation.switch("up")
                elif dis.x > 0: self.animation.switch("right")
                elif dis.x < 0: self.animation.switch("left")
        
        # --- MANUAL INPUT (Override) ---
        # Only allow manual input if NOT auto-piloting (or let manual override cancel path)
        else:
            if input_manager.key_down(pg.K_s):
                self.animation.switch("down")
                dis.y += 1
            if input_manager.key_down(pg.K_w):
                self.animation.switch("up")
                dis.y -= 1
            if input_manager.key_down(pg.K_d):
                self.animation.switch("right")
                dis.x += 1
            if input_manager.key_down(pg.K_a):
                self.animation.switch("left")
                dis.x -= 1
            
            # Cancel path if manual key is pressed
            if dis.x != 0 or dis.y != 0:
                self.path = []

        if dis.x == 0 and dis.y == 0 and not self.path:
            self.animation.accumulator = 0
            self.moving = False
        else:
            self.moving = True
            
        dis.normalize(self.speed * dt)

        # Collision Handling (Existing logic)
        temp_rect = self.animation.rect.copy()
        if dis.x != 0:
            maybe_x_rect = temp_rect.move(dis.x, 0)
            if not self.game_manager.current_map.check_collision(maybe_x_rect) and not any(maybe_x_rect.colliderect(e.animation.rect) for e in self.game_manager.current_enemy_trainers):
                self.position.x += dis.x
                temp_rect = maybe_x_rect
            else:
                self.position.x = Entity._snap_to_grid(self.position.x)
                # If we hit a wall while auto-piloting, clear path
                if self.path: self.path = []

        if dis.y != 0:
            maybe_y_rect = temp_rect.move(0, dis.y)
            if not self.game_manager.current_map.check_collision(maybe_y_rect) and not any(maybe_y_rect.colliderect(e.animation.rect) for e in self.game_manager.current_enemy_trainers):
                self.position.y += dis.y
                temp_rect = maybe_y_rect
            else:
                self.position.y = Entity._snap_to_grid(self.position.y)
                # If we hit a wall while auto-piloting, clear path
                if self.path: self.path = []

        # check bush
        if self.game_manager.current_map.check_touch_bush(self.animation.rect):
            self.bush_counter += 1
        elif self.bush_counter > 0:
            self.bush_counter -= 1

        if self.bush_counter > self.max_bush_counter:
            self.bush_counter = 0
            self.max_bush_counter = random.randint(5*60, 10*60)
            scene_manager.change_scene("encounter")
        
        # Check teleportation
        tp = self.game_manager.current_map.check_teleport(self.position)
        if tp:
            dest = tp.destination
            self.game_manager.switch_map(dest, tp.dst_pos)
            # self.position = tp.dst_pos
            self.path = [] # Clear path on teleport
                
        # Call super update (Entity update) which handles animation tick
        # Note: Do NOT call super().update(dt) if Entity.update does movement logic. 
        # Assuming Entity.update only handles basic state/animation.
        super().update(dt)

    @override
    def draw(self, screen: pg.Surface, camera: PositionCamera) -> None:
        super().draw(screen, camera)
        
        # --- DRAW PATH ---
        if self.path:
            # Convert world path points to screen coordinates
            points = []
            # Start form current player center
            start_screen = camera.transform_position(Position(self.position.x + GameSettings.TILE_SIZE/2, self.position.y + GameSettings.TILE_SIZE/2))
            points.append(start_screen)
            
            for p in self.path:
                # Center of the target tiles
                screen_pos = camera.transform_position(Position(p.x + GameSettings.TILE_SIZE/2, p.y + GameSettings.TILE_SIZE/2))
                points.append(screen_pos)
            
            if len(points) > 1:
                pg.draw.lines(screen, (0, 255, 255), False, points, 3)
                # Draw small rect at the target
                pg.draw.rect(screen, (0, 255, 255), (points[-1][0]-5, points[-1][1]-5, 10, 10))
    
    @override
    def to_dict(self) -> dict[str, object]:
        return super().to_dict()
    
    @property
    @override
    def camera(self) -> PositionCamera:
        return PositionCamera(int(self.position.x) - GameSettings.SCREEN_WIDTH // 2, int(self.position.y) - GameSettings.SCREEN_HEIGHT // 2)
            
    @classmethod
    @override
    def from_dict(cls, data: dict[str, object], game_manager: GameManager) -> Player:
        return cls(data["x"] * GameSettings.TILE_SIZE, data["y"] * GameSettings.TILE_SIZE, game_manager)