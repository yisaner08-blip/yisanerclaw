"""HTTP API 服务 —— Hermes 网关对齐：RESTful Agent 接口"""

import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from http.server import HTTPServer, BaseHTTPRequestHandler
from src.cli.main import create_agent
from src.tools.registry import get_registry

_agent = create_agent()


class AgentHandler(BaseHTTPRequestHandler):
    def _json_response(self, data: dict, code: int = 200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def do_POST(self):
        if self.path == "/api/chat":
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            _agent.reset_memory()
            result = _agent.run_conversation(body.get("message", ""))
            self._json_response(result.to_dict())
        else:
            self._json_response({"error": "Not found"}, 404)

    def do_GET(self):
        if self.path == "/api/tools":
            tools = [{"name": t.name, "description": t.description} for t in get_registry().list_all()]
            self._json_response({"tools": tools})
        elif self.path == "/api/stats":
            self._json_response(_agent.stats)
        else:
            self._json_response({"error": "Not found"}, 404)


def main(port: int = 8080):
    server = HTTPServer(("0.0.0.0", port), AgentHandler)
    print(f"API server started on http://0.0.0.0:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
