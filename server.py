from server.playerHandler import PlayerHandler

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
PORT = 8989

PLAYER_HANDLER = PlayerHandler()
PLAYER_HANDLER.start()
    
class Handler(BaseHTTPRequestHandler):
    # def log_message(self, fmt, *args):
    #     return

    def do_GET(self):
        if self.path == "/":
            self._json(200, {"status": "ok"})
            return
            
        if self.path == "/register":
            pid = PLAYER_HANDLER.register()
            self._json(200, {"message": "registration successful", "id": pid})
            return

        if self.path == "/players":
            self._json(200, {"players": PLAYER_HANDLER.list_players()})
            return

        # Added: Get Chat
        if self.path == "/chat":
            self._json(200, {"messages": PLAYER_HANDLER.get_messages()})
            return

        self._json(404, {"error": "not_found"})

    def do_POST(self):
        # Allow both players update and chat
        if self.path not in ["/players", "/chat"]:
            self._json(404, {"error": "not_found"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        try:
            body = self.rfile.read(length)
            data = json.loads(body.decode("utf-8"))
        except Exception:
            self._json(400, {"error": "invalid_json"})
            return

        # Added: Handle Chat Post
        if self.path == "/chat":
            if "id" not in data or "text" not in data:
                self._json(400, {"error": "missing_fields"})
                return
            try:
                pid = int(data["id"])
                text = str(data["text"])
                PLAYER_HANDLER.add_message(pid, text)
                self._json(200, {"success": True})
            except Exception:
                self._json(400, {"error": "bad_format"})
            return

        # Handle Players Update
        if self.path == "/players":
            missing = [k for k in ("id", "x", "y", "map") if k not in data]
            if missing:
                self._json(400, {"error": "bad_fields", "missing": missing})
                return

            try:
                pid = int(data["id"])
                x = float(data["x"])
                y = float(data["y"])
                map_name = str(data["map"])
                moving = bool(data["moving"])
                direction = str(data["direction"])
            except (ValueError, TypeError):
                self._json(400, {"error": "bad_fields"})
                return

            ok = PLAYER_HANDLER.update(pid, x, y, map_name, moving, direction)
            if not ok:
                self._json(404, {"error": "player_not_found"})
                return

            self._json(200, {"success": True})

    # Utility for JSON responses
    def _json(self, code: int, obj: object) -> None:
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

if __name__ == "__main__":
    print(f"[Server] Running on localhost with port {PORT}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()