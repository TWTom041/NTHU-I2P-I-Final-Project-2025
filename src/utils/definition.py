from pygame import Rect
from .settings import GameSettings
from dataclasses import dataclass
from enum import Enum
from typing import overload, TypedDict, Protocol

MouseBtn = int
Key = int

Direction = Enum('Direction', ['UP', 'DOWN', 'LEFT', 'RIGHT', 'NONE'])

@dataclass
class Position:
    x: float
    y: float

    def __add__(self, a: "Position"):  # [TODO HACKATHON 2]
        self.x += a.x
        self.y += a.y
        return self

    def normalize(self, mul=1):  # [TODO HACKATHON 2]
        if self.x == 0 and self.y == 0:
            return
        denominator = (self.x ** 2 + self.y ** 2) ** 0.5 / mul
        self.x /= denominator
        self.y /= denominator
    
    def copy(self):
        return Position(self.x, self.y)
        
    def distance_to(self, other: "Position") -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5
        
@dataclass
class PositionCamera:
    x: int
    y: int
    
    def __add__(self, a: "PositionCamera"):  # [TODO HACKATHON 3]
        self.x += a.x
        self.y += a.y
        return self

    def copy(self):
        return PositionCamera(self.x, self.y)
        
    def to_tuple(self) -> tuple[int, int]:
        return (self.x, self.y)
        
    def transform_position(self, position: Position) -> tuple[int, int]:
        return (int(position.x) - self.x, int(position.y) - self.y)
        
    def transform_position_as_position(self, position: Position) -> Position:
        return Position(int(position.x) - self.x, int(position.y) - self.y)
        
    def transform_rect(self, rect: Rect) -> Rect:
        return Rect(rect.x - self.x, rect.y - self.y, rect.width, rect.height)

@dataclass
class Teleport:
    pos: Position
    destination: str
    
    @overload
    def __init__(self, x: int, y: int, destination: str, dst_x: int, dst_y: int) -> None: ...
    @overload
    def __init__(self, pos: Position, destination: str, dst_pos: Position) -> None: ...

    def __init__(self, *args, **kwargs):
        if isinstance(args[0], Position):
            self.pos = args[0]
            self.destination = args[1]
            self.dst_pos = args[2]
        else:
            x, y, dest, dst_x, dst_y = args
            self.pos = Position(x, y)
            self.destination = dest
            self.dst_pos = Position(dst_x, dst_y)
    
    def to_dict(self):
        return {
            "x": self.pos.x // GameSettings.TILE_SIZE,
            "y": self.pos.y // GameSettings.TILE_SIZE,
            "destination": self.destination,
            "dst_x": self.dst_pos.x // GameSettings.TILE_SIZE,
            "dst_y": self.dst_pos.y // GameSettings.TILE_SIZE
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(data["x"] * GameSettings.TILE_SIZE, data["y"] * GameSettings.TILE_SIZE, data["destination"], data["dst_x"] * GameSettings.TILE_SIZE, data["dst_y"] * GameSettings.TILE_SIZE)
    
class Monster(TypedDict):
    name: str
    hp: int
    max_hp: int
    level: int
    sprite_path: str

class Item(TypedDict):
    name: str
    count: int
    sprite_path: str