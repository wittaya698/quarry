"""The Checkpoint pages: a local server over one Site, showing whichever
Checkpoint it is at — the Blockout editor at #1, the walkable Terrain at #2.

Every request re-opens the Site from disk, so its history stays the only
source of truth. The caller is fixed when the server starts, and every act is
passed to the core under it, so the core's refusal rules apply unchanged.
A random token in every URL keeps other pages in the browser from acting.
"""
import json
import secrets
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from quarry.checks import run_checks
from quarry.edits import EditError
from quarry.site import Refused, Site

_PAGES = {1: Path(__file__).with_name("checkpoint1.html"), 2: Path(__file__).with_name("checkpoint2.html")}


def serve(site_path, caller, port=0):
    """A server for one Site on 127.0.0.1; call `serve_forever()` to run it."""
    return _Server(Path(site_path), caller, port)


class _Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, site_path, caller, port):
        super().__init__(("127.0.0.1", port), _Handler)
        self.site_path, self.caller = site_path, caller
        self.token = secrets.token_urlsafe(16)
        self.address = f"http://127.0.0.1:{self.server_address[1]}"
        self.url = f"{self.address}/?token={self.token}"


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        route = self._authorised_route()
        if route is None:
            return
        if route == "/":
            page = _PAGES[1 if _at_first(Site.open(self.server.site_path)) else 2]
            self._send(200, "text/html; charset=utf-8", page.read_bytes())
        elif route == "/api/state":
            self._json(200, _state(Site.open(self.server.site_path)))
        else:
            self._json(404, {"error": f"no route {route}"})

    def do_POST(self):
        route = self._authorised_route()
        if route is None:
            return
        act = _ACTS.get(route)
        if act is None:
            self._json(404, {"error": f"no route {route}"})
            return
        site = Site.open(self.server.site_path)
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            act(site, body, self.server.caller)
        except EditError as error:
            self._json(400, {"error": str(error)})
        except (KeyError, TypeError, ValueError) as error:
            self._json(400, {"error": f"malformed request: {type(error).__name__} {error}"})
        except Refused as error:
            self._json(409, {"error": str(error)})
        else:
            self._json(200, _state(site))

    def _authorised_route(self):
        """The request's route, or None after answering 403 to a wrong token."""
        url = urlparse(self.path)
        [token] = parse_qs(url.query).get("token", [""])
        if not secrets.compare_digest(token, self.server.token):
            self._json(403, {"error": "this page's token is missing or wrong; open the URL quarry printed"})
            return None
        return url.path

    def _json(self, status, body):
        self._send(status, "application/json", json.dumps(body).encode())

    def _send(self, status, content_type, data):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        pass  # keep the terminal for the developer


def _at_first(site):
    """Checkpoint #1's view, which stays up, approved, until a Refine Plan is drafted."""
    return site.checkpoint == 1 or site.current_refine_plan is None


# Each act goes to whichever Checkpoint the Site is at; the core decides the rest.
_ACTS = {
    "/api/edit": lambda site, body, caller: (site.edit if _at_first(site) else site.edit_refine_plan)(
        body["revision"], body["change"], by=caller
    ),
    "/api/approve": lambda site, body, caller: (site.approve if _at_first(site) else site.approve_refine_plan)(
        body["revision"], by=caller, waivers=body["waivers"]
    ),
    "/api/reject": lambda site, body, caller: (site.reject if _at_first(site) else site.reject_refine_plan)(
        body["revision"], by=caller, note=body["note"]
    ),
}


def _state(site):
    if _at_first(site):
        revision, approval, rejections = site.current_revision, site.approval, site.rejections
        blockout, checks = revision.blockout, site.checks()
        extra = {}
    else:
        revision, approval = site.current_refine_plan, site.refine_plan_approval
        rejections = site.refine_plan_rejections
        blockout = site.revision(site.approval.revision).blockout
        terrain = site.terrain()
        checks = run_checks(site.brief, blockout, terrain)
        extra = {
            "blockout_revision": site.approval.revision,
            "refine_plan": revision.plan.to_dict(),
            "terrain": {"spacing": terrain.spacing, "heights": terrain.heights},
            "walk_speed": site.brief.walk_speed,
            "max_walkable_slope": site.brief.max_walkable_slope,
        }
    return {
        "checkpoint": 1 if _at_first(site) else 2,
        "footprint": list(site.brief.footprint),
        "revision": revision.number,
        "state": _review_state(revision, approval, rejections),
        "blockout": blockout.to_dict(),
        "checks": [asdict(r) for r in checks],
        "waivers": approval.waivers if approval else {},
        **extra,
    }


def _review_state(revision, approval, rejections):
    if approval:
        return f"approved by {approval.by.name}"
    if any(r.revision == revision.number for r in rejections):
        return "rejected"
    return "awaiting review"
