"""
Mock Agent 3 for demos — answers the scan contract on port 8003.

Agent 3 (the website scanner) is a separate team's service and not part
of this repo. This stub implements just enough of the contract in
docs/technical-design.md section 8 to demo the full pipeline: it accepts
the scan request and returns confirmed website evidence, which the merge
step records with source references.

Run:  python scripts/mock_agent3.py
Stop: type "exit" + Enter, or Ctrl+C  (stopping it mid-demo is also how
you demonstrate the "Partially Completed" graceful-degradation path.)
"""

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8003


def watch_stdin(server: HTTPServer) -> None:
    """Shut the server down when the user types "exit"."""
    for line in sys.stdin:
        if line.strip().lower() == "exit":
            print("[mock-agent3] exit requested, shutting down", flush=True)
            threading.Thread(target=server.shutdown, daemon=True).start()
            return


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        print(f"[mock-agent3] scan requested: {body.get('companyId')} -> {body.get('websiteUrl')}", flush=True)
        response = {
            "companyId": body.get("companyId"),
            "scanStatus": "Completed",
            "extractedData": {
                "pricingFound": True,
                "blogFound": True,
                "sourceUrls": [
                    f"{body.get('websiteUrl')}/pricing",
                    f"{body.get('websiteUrl')}/blog",
                ],
            },
        }
        payload = json.dumps(response).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):  # silence per-request noise; we print our own line
        pass


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"[mock-agent3] listening on http://localhost:{PORT} — type 'exit' to stop", flush=True)
    threading.Thread(target=watch_stdin, args=(server,), daemon=True).start()
    server.serve_forever()
