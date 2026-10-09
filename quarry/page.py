"""The Checkpoint pages: a local server over one Site, showing whichever
Checkpoint it is at — the Blockout editor at #1, the walkable Terrain at #2.

Every request re-opens the Site from disk, so its history stays the only
source of truth. The caller is fixed when the server starts, and every act is
passed to the core under it, so the core's refusal rules apply unchanged.
A random token in every URL keeps other pages in the browser from acting.

Started on a Superseded Refine Plan Revision, the server shows that Revision's
Terrain at Checkpoint #2, read-only: every act is refused.
"""
import json
import secrets
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from quarry.checks import run_checks
from quarry.claude_agent import AgentUnavailable
from quarry.edits import EditError
from quarry.site import Refused, Site
from quarry.validation import InvalidDraft, NeedsReopen

_PAGES = {1: Path(__file__).with_name("checkpoint1.html"), 2: Path(__file__).with_name("checkpoint2.html")}


def serve(site_path, caller, port=0, agent=None, superseded=None):
    """A server for one Site on 127.0.0.1; call `serve_forever()` to run it.
    `agent` answers Edit Requests; `superseded` names a Superseded Refine Plan
    Revision to view instead of the Site's current Checkpoint."""
    return _Server(Path(site_path), caller, port, agent, superseded)


class _Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, site_path, caller, port, agent, superseded):
        super().__init__(("127.0.0.1", port), _Handler)
        self.site_path, self.caller = site_path, caller
        self.agent, self.superseded = agent, superseded
        if superseded is not None:
            Site.open(site_path).superseded_terrain(superseded)  # refuses one that is not Superseded
        self.token = secrets.token_urlsafe(16)
        self.address = f"http://127.0.0.1:{self.server_address[1]}"
        self.url = f"{self.address}/?token={self.token}"


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        route = self._authorised_route()
        if route is None:
            return
        if route == "/":
            first = self.server.superseded is None and _at_first(Site.open(self.server.site_path))
            self._send(200, "text/html; charset=utf-8", _PAGES[1 if first else 2].read_bytes())
        elif route == "/api/state":
            self._json(200, _state(Site.open(self.server.site_path), self.server.superseded))
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
        if self.server.superseded is not None:
            number = self.server.superseded
            self._json(409, {"error": f"Refine Plan Revision {number} is Superseded: viewable, but closed to every act"})
            return
        site = Site.open(self.server.site_path)
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            answer = act(site, body, self.server)
        except EditError as error:
            self._json(400, {"error": str(error)})
        except (KeyError, TypeError, ValueError) as error:
            self._json(400, {"error": f"malformed request: {type(error).__name__} {error}"})
        except Refused as error:
            self._json(409, {"error": str(error)})
        except InvalidDraft as error:
            self._json(502, {"error": f"the Agent's answer was refused, nothing recorded: {error}"})
        except AgentUnavailable as error:
            self._json(503, {"error": f"the Agent could not answer: {error}"})
        else:
            needs = asdict(answer) if isinstance(answer, NeedsReopen) else None
            self._json(200, {**_state(site), "needs_reopen": needs})

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


def _request(site, body, server):
    if server.agent is None:
        raise Refused("this page was started without an Agent, so it cannot answer Edit Requests")
    return site.request_edit(body["request"], server.agent)


# Each act goes to whichever Checkpoint the Site is at; the core decides the rest.
_ACTS = {
    "/api/edit": lambda site, body, server: (site.edit if _at_first(site) else site.edit_refine_plan)(
        body["revision"], body["change"], by=server.caller
    ),
    "/api/approve": lambda site, body, server: (site.approve if _at_first(site) else site.approve_refine_plan)(
        body["revision"], by=server.caller, waivers=body["waivers"]
    ),
    "/api/reject": lambda site, body, server: (site.reject if _at_first(site) else site.reject_refine_plan)(
        body["revision"], by=server.caller, note=body["note"]
    ),
    "/api/request": _request,
    "/api/reopen": lambda site, body, server: site.reopen(by=server.caller),
}


def _state(site, superseded=None):
    if superseded is not None:
        revision = site.refine_plan(superseded)
        state = f"Superseded: built on Blockout Revision {revision.blockout_revision}, since Reopened"
        return _checkpoint2(site, revision, site.superseded_terrain(superseded), state, None, superseded=True)
    if not _at_first(site):
        revision, approval = site.current_refine_plan, site.refine_plan_approval
        state = _review_state(revision, approval, site.refine_plan_rejections)
        return _checkpoint2(site, revision, site.terrain(), state, approval)
    revision, approval = site.current_revision, site.approval
    return _view(
        site, 1, revision, _review_state(revision, approval, site.rejections), approval,
        revision.blockout, site.checks(),
    )


def _checkpoint2(site, revision, terrain, state, approval, superseded=False):
    """Checkpoint #2's view: a Refine Plan Revision's Terrain, walkable."""
    blockout = site.revision(revision.blockout_revision).blockout
    return {
        **_view(site, 2, revision, state, approval, blockout, run_checks(site.brief, blockout, terrain), superseded),
        "blockout_revision": revision.blockout_revision,
        "refine_plan": revision.plan.to_dict(),
        "terrain": {"spacing": terrain.spacing, "heights": terrain.heights},
        "walk_speed": site.brief.walk_speed,
        "max_walkable_slope": site.brief.max_walkable_slope,
    }


def _view(site, checkpoint, revision, state, approval, blockout, checks, superseded=False):
    return {
        "checkpoint": checkpoint,
        "footprint": list(site.brief.footprint),
        "revision": revision.number,
        "state": state,
        "blockout": blockout.to_dict(),
        "checks": [asdict(r) for r in checks],
        "waivers": approval.waivers if approval else {},
        "can_reopen": not superseded and site.approval is not None,
        "superseded": superseded,
        "needs_reopen": None,
    }


def _review_state(revision, approval, rejections):
    if approval:
        return f"approved by {approval.by.name}"
    if any(r.revision == revision.number for r in rejections):
        return "rejected"
    return "awaiting review"
