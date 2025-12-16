import threading
import time
import copy
from dataclasses import dataclass
from typing import Dict, Optional, List

TIMEOUT_TIME = 60.0
CHECK_INTERVAL_TIME = 10.0

@dataclass
class Player:
    id: int
    x: float
    y: float
    map: str
    last_update: float
    moving: bool
    direction: str

    def update(self, x: float, y: float, map: str, moving:bool, direction:str) -> None:
        if x != self.x or y != self.y or map != self.map:
            self.last_update = time.monotonic()
        self.x = x
        self.y = y
        self.map = map
        self.moving = moving
        self.direction = direction

    def is_inactive(self) -> bool:
        now = time.monotonic()
        return (now - self.last_update) >= TIMEOUT_TIME


class PlayerHandler:
    _lock: threading.Lock
    _stop_event: threading.Event
    _thread: threading.Thread | None
    
    players: Dict[int, Player]
    _next_id: int
    
    # Added: Chat storage
    chat_history: List[dict]

    def __init__(self, *, timeout_seconds: float = 120.0, check_interval_seconds: float = 5.0):
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None
        
        self.players = {}
        self._next_id = 0
        self.chat_history = [] # Initialize
        
    # Threading
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._cleaner, name="PlayerCleaner", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _cleaner(self) -> None:
        while not self._stop_event.wait(CHECK_INTERVAL_TIME):
            now = time.monotonic()
            to_remove: list[int] = []
            with self._lock:
                for pid, p in list(self.players.items()):
                    if now - p.last_update >= TIMEOUT_TIME:
                        to_remove.append(pid)
                for pid in to_remove:
                    _ = self.players.pop(pid, None)
                    
    # API
    def register(self) -> int:
        with self._lock:
            pid = self._next_id
            self._next_id += 1
            self.players[pid] = Player(pid, 0.0, 0.0, "", time.monotonic(), False, "down")
            return pid

    def update(self, pid: int, x: float, y: float, map_name: str, moving:bool, direction:str) -> bool:
        with self._lock:
            p = self.players.get(pid)
            if not p:
                return False
            else:
                p.update(float(x), float(y), str(map_name), bool(moving), str(direction))
                return True

    def list_players(self) -> dict:
        with self._lock:
            player_list = {}
            for p in self.players.values():
                player_list[p.id] = {
                    "id": p.id,
                    "x": p.x,
                    "y": p.y,
                    "map": p.map,
                    "moving": p.moving,
                    "direction": p.direction
                }
            return player_list

    # Added: Chat Logic
    def add_message(self, pid: int, text: str) -> None:
        with self._lock:
            # Simple structure, keeping last 50 messages
            msg = {
                "from": f"Player {pid}",
                "text": text,
                "timestamp": time.time()
            }
            self.chat_history.append(msg)
            if len(self.chat_history) > 50:
                self.chat_history.pop(0)

    def get_messages(self) -> list[dict]:
        with self._lock:
            return list(self.chat_history)