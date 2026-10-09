"""`quarry`: thin command-line wiring over a Site. All rules live in the core."""
import argparse
import getpass
import sys
import tempfile
import time
import webbrowser

import anthropic

from quarry.agent import FakeAgent
from quarry.brief import Brief
from quarry.claude_agent import AgentUnavailable, ClaudeAgent
from quarry.claude_code_agent import ClaudeCodeAgent
from quarry.export import ExportError, write_tscn
from quarry.identity import Automated, Human
from quarry.page import serve
from quarry.selftest import selftest
from quarry.site import Refused, Site
from quarry.validation import InvalidDraft, NeedsReopen

# Who drafts. The subscription is the default whatever the environment holds:
# an API key never switches Quarry to per-token billing on its own.
AGENTS = {"subscription": ClaudeCodeAgent, "api": ClaudeAgent, "fake": FakeAgent}


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        code = args.run(args)
    except (Refused, ExportError, FileExistsError, FileNotFoundError) as error:
        print(f"quarry: {error}", file=sys.stderr)
        return 1
    except InvalidDraft as error:
        print(f"quarry: the Agent's Draft was refused, nothing recorded: {error}", file=sys.stderr)
        return 1
    except (AgentUnavailable, anthropic.AnthropicError) as error:
        print(f"quarry: the Claude Agent could not draft: {error}", file=sys.stderr)
        return 1
    return code or 0


def _parser():
    parser = argparse.ArgumentParser(prog="quarry")
    commands = parser.add_subparsers(required=True)

    new = commands.add_parser("new", help="create a Site from a Brief")
    new.add_argument("site")
    source = new.add_mutually_exclusive_group(required=True)
    source.add_argument("--brief", help="a Brief JSON file")
    source.add_argument("--from", dest="from_site", help="copy the Brief of an existing Site")
    new.set_defaults(run=_new)

    draft = commands.add_parser("draft", help="ask the Agent for a Blockout Draft")
    draft.add_argument("site")
    _agent_option(draft)
    draft.set_defaults(run=_draft)

    refine = commands.add_parser("refine", help="ask the Agent for a Refine Plan Draft")
    refine.add_argument("site")
    _agent_option(refine)
    refine.set_defaults(run=_refine)

    page = commands.add_parser("open", help="open the current Checkpoint's page in the browser")
    page.add_argument("site")
    page.add_argument("--port", type=int, default=0, help="a fixed port; any free one by default")
    page.add_argument("--no-browser", action="store_true", help="print the URL without opening it")
    page.add_argument("--refine-plan", type=int, metavar="N", help="view a Superseded Refine Plan Revision's Terrain, read-only")
    _agent_option(page, "who answers Edit Requests")
    page.set_defaults(run=_open)

    status = commands.add_parser("status", help="Checkpoint, Revision and Check results")
    status.add_argument("site")
    status.set_defaults(run=_status)

    show = commands.add_parser("show", help="one Revision's choices and Reasons, at the current Checkpoint")
    show.add_argument("site")
    show.add_argument("revision", type=int)
    show.add_argument("--refine-plan", action="store_true", help="a Refine Plan Revision, Superseded ones included")
    show.set_defaults(run=_show)

    approve = commands.add_parser("approve", help="approve one exact Revision at the current Checkpoint")
    approve.add_argument("site")
    approve.add_argument("revision", type=int)
    approve.add_argument(
        "--waive", action="append", default=[], metavar="CHECK=WHY",
        help="accept a missed Check anyway; one per missed Check",
    )
    approve.set_defaults(run=_approve)

    reject = commands.add_parser("reject", help="reject a Revision with a note")
    reject.add_argument("site")
    reject.add_argument("revision", type=int)
    reject.add_argument("--note", required=True, help="what was wrong")
    reject.set_defaults(run=_reject)

    revive = commands.add_parser("revive", help="copy a rejected Revision forward as a new one")
    revive.add_argument("site")
    revive.add_argument("revision", type=int)
    revive.set_defaults(run=_revive)

    request = commands.add_parser("request", help="an Edit Request: ask the Agent for a change in plain words")
    request.add_argument("site")
    request.add_argument("words", help='e.g. "make the hill less steep"')
    _agent_option(request)
    request.set_defaults(run=_request)

    reopen = commands.add_parser("reopen", help="withdraw the Blockout's Approval to change it")
    reopen.add_argument("site")
    reopen.set_defaults(run=_reopen)

    brief = commands.add_parser("brief", help="change the Brief; after Approval this Reopens the Blockout")
    brief.add_argument("site")
    brief.add_argument("--brief", required=True, help="the new Brief JSON file")
    brief.set_defaults(run=_brief)

    export = commands.add_parser("export", help="write the .glb once the Refine Plan is approved")
    export.add_argument("site")
    export.add_argument("out", help="the .glb file to write")
    export.add_argument("--tscn", action="store_true", help="also write a Godot 4 scene that instances it")
    export.set_defaults(run=_export)

    selftest = commands.add_parser("selftest", help="prove the Checks and Ledger rules catch deliberate corruptions")
    selftest.set_defaults(run=_selftest)

    return parser


def _agent_option(command, role="who drafts"):
    command.add_argument(
        "--agent", choices=AGENTS, default="subscription",
        help=f"{role}: your Claude subscription via Claude Code (default), "
        "the Anthropic API (needs ANTHROPIC_API_KEY, billed per token), or the offline fake",
    )


def _caller():
    """The person at the keyboard. Without a terminal there is no person to
    name, so the core receives an Automated caller and refuses human acts."""
    if sys.stdin.isatty():
        return Human(getpass.getuser())
    return Automated("non-interactive quarry")


def _new(args):
    brief = Brief.load(args.brief) if args.brief else Site.open(args.from_site).brief
    Site.create(args.site, brief)
    print(f"created Site {args.site}")


def _draft(args):
    site = Site.open(args.site)
    site.draft(AGENTS[args.agent]())
    print(f"drafted Revision {site.current_revision.number}")
    _print_checks(site.checks(), site.approval, site.current_revision.blockout)


def _refine(args):
    site = Site.open(args.site)
    site.draft_refine_plan(AGENTS[args.agent]())
    print(f"drafted Refine Plan Revision {site.current_refine_plan.number}")
    _print_checks(site.terrain_checks(), site.refine_plan_approval, site.current_revision.blockout)


def _request(args):
    site = Site.open(args.site)
    answer = site.request_edit(args.words, AGENTS[args.agent]())
    if isinstance(answer, NeedsReopen):
        print(answer)
        print(f"nothing changed; to change it, run `quarry reopen {args.site}` and ask again at Checkpoint 1")
    elif site.checkpoint == 1:
        print(f"drafted Revision {answer.number} for your Edit Request")
        _print_checks(site.checks(), site.approval, answer.blockout)
    else:
        print(f"drafted Refine Plan Revision {answer.number} for your Edit Request")
        _print_checks(site.terrain_checks(), site.refine_plan_approval, site.revision(site.approval.revision).blockout)


def _reopen(args):
    site = Site.open(args.site)
    site.reopen(by=_caller())
    _print_reopened(site)


def _brief(args):
    site = Site.open(args.site)
    reopenings = len(site.reopenings)
    site.edit_brief(Brief.load(args.brief), by=_caller())
    print(f"changed the Brief of {args.site}")
    if len(site.reopenings) > reopenings:
        _print_reopened(site)


def _print_reopened(site):
    print(f"Reopened Blockout Revision {site.reopenings[-1].revision}")
    superseded = [r.number for r in site.superseded_refine_plans]
    if superseded:
        print(f"{_refine_plans(superseded)} {'is' if len(superseded) == 1 else 'are'} Superseded: viewable, never exportable")


def _refine_plans(numbers):
    if len(numbers) == 1:
        return f"Refine Plan Revision {numbers[0]}"
    return f"Refine Plan Revisions {numbers[0]}–{numbers[-1]}"


def _open(args):
    site = Site.open(args.site)
    if site.current_revision is None:
        raise Refused(f"nothing to review yet; run `quarry draft {args.site}` first")
    server = serve(args.site, _caller(), port=args.port, agent=AGENTS[args.agent](), superseded=args.refine_plan)
    print(f"Checkpoint page for {args.site}: {server.url}")
    print("acting as", server.caller.name, "· Ctrl-C to stop")
    if not args.no_browser:
        webbrowser.open(server.url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _status(args):
    site = Site.open(args.site)
    revision = site.current_revision
    if revision is None:
        problems = site.brief_problems()
        if problems:
            print("Checkpoint 1 · the Brief fails the Brief Check, so it cannot be drafted:")
            for problem in problems:
                print(f"  {problem}")
            return
        print(f"Checkpoint 1 · no Draft yet (run `quarry draft {args.site}`)")
        return
    print(f"Checkpoint 1 · Blockout Revision {revision.number} · {_state(revision, site.approval, site.rejections)}")
    superseded = [r.number for r in site.superseded_refine_plans]
    if superseded:
        print(f"{_refine_plans(superseded)} Superseded by a Reopen (see `quarry show {args.site} N --refine-plan`)")
    _print_checks(site.checks(), site.approval, site.current_revision.blockout)
    if site.checkpoint == 1:
        return
    plan = site.current_refine_plan
    if plan is None:
        print(f"Checkpoint 2 · no Refine Plan yet (run `quarry refine {args.site}`)")
        return
    state = _state(plan, site.refine_plan_approval, site.refine_plan_rejections)
    print(f"Checkpoint 2 · Refine Plan Revision {plan.number} · {state} · Checks on the Terrain:")
    _print_checks(site.terrain_checks(), site.refine_plan_approval, site.current_revision.blockout)
    if site.checkpoint == "done":
        print(f"ready to export (run `quarry export {args.site} {args.site}.glb`)")


def _state(revision, approval, rejections):
    if approval:
        return f"approved by {approval.by.name}"
    if any(r.revision == revision.number for r in rejections):
        return "rejected"
    return "awaiting review"


def _show(args):
    site = Site.open(args.site)
    if args.refine_plan or site.checkpoint != 1:
        _show_refine_plan(site, args.revision)
        return
    revision = site.revision(args.revision)
    for rejection in site.rejections:
        if rejection.revision == revision.number:
            print(f"rejected by {rejection.by.name}: {rejection.note}")
    if revision.revived_from:
        print(f"revived from Revision {revision.revived_from}")
    if revision.request:
        print(f"drafted for the Edit Request “{revision.request}”")
    blockout = revision.blockout
    for landmark in blockout.landmarks:
        x, y = landmark.position
        flag = " [AI-chosen]" if landmark.ai_chosen else ""
        print(
            f"landmark {landmark.name}{flag} at ({x:.0f}, {y:.0f}), pad {landmark.pad_radius:g} m"
            f" — {landmark.reason.text}"
        )
    for path in blockout.paths:
        flag = " [decorative]" if path.decorative else ""
        print(f"path {path.start}→{path.end}{flag} — {path.reason.text}")
    for order, zone in enumerate(blockout.zones, 1):
        x, y = zone.center
        print(
            f"zone {order} {zone.name}: {zone.profile} {zone.height:+g} m, radius {zone.radius:.0f} m"
            f" at ({x:.0f}, {y:.0f}), {zone.combine} — {zone.reason.text}"
        )
    for reading in blockout.readings:
        print(f"reading “{reading.phrase}” as {reading.meaning} — {reading.reason.text}")


def _show_refine_plan(site, number):
    revision = site.refine_plan(number)
    if revision.superseded:
        print(f"Superseded: built on Blockout Revision {revision.blockout_revision}, since Reopened")
    if revision.request:
        print(f"drafted for the Edit Request “{revision.request}”")
    for rejection in site.refine_plan_rejections:
        if rejection.revision == revision.number:
            print(f"rejected by {rejection.by.name}: {rejection.note}")
    if revision.revived_from:
        print(f"revived from Refine Plan Revision {revision.revived_from}")
    for s in revision.plan.surfaces:
        print(
            f"{s.surface}: {s.slope_profile} slopes, falloff {s.falloff_width:g} m, "
            f"roughness {s.roughness:g} m, seed {s.seed}, vegetation {s.vegetation_density:.0%}"
            f" — {s.reason.text}"
        )


def _approve(args):
    site = Site.open(args.site)
    waivers = dict(_waiver(w) for w in args.waive)
    if site.checkpoint == 1:
        site.approve(args.revision, by=_caller(), waivers=waivers)
        print(f"approved Blockout Revision {args.revision}")
    else:
        site.approve_refine_plan(args.revision, by=_caller(), waivers=waivers)
        print(f"approved Refine Plan Revision {args.revision}")


def _reject(args):
    site = Site.open(args.site)
    if site.checkpoint == 1:
        site.reject(args.revision, by=_caller(), note=args.note)
        print(f"rejected Blockout Revision {args.revision}")
    else:
        site.reject_refine_plan(args.revision, by=_caller(), note=args.note)
        print(f"rejected Refine Plan Revision {args.revision}")


def _revive(args):
    site = Site.open(args.site)
    if site.checkpoint == 1:
        site.revive(args.revision)
        print(f"revived Blockout Revision {args.revision} as Revision {site.current_revision.number}")
    else:
        site.revive_refine_plan(args.revision)
        number = site.current_refine_plan.number
        print(f"revived Refine Plan Revision {args.revision} as Revision {number}")


def _export(args):
    site = Site.open(args.site)
    site.export(args.out)
    terrain = site.terrain()
    print(
        f"exported {args.out} from Blockout Revision {terrain.blockout_revision} "
        f"and Refine Plan Revision {terrain.refine_plan_revision}; collision, anchors and curves verified"
    )
    if args.tscn:
        print(f"wrote {write_tscn(args.out)}, which instances it and makes each Path a Path3D")


def _selftest(args):
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="quarry-selftest-") as workdir:
        outcomes = selftest(workdir)
    passed = all(o.caught for o in outcomes)
    print(f"selftest {'PASS' if passed else 'FAIL'} ({time.monotonic() - started:.1f}s): "
          f"a known-good Site exported and verified, then {len(outcomes)} corruptions")
    for outcome in outcomes:
        print(f"  {'caught' if outcome.caught else 'MISSED'}  {outcome.corruption} — {outcome.detail}")
    return 0 if passed else 1


def _waiver(text):
    check, _, why = text.partition("=")
    if not why.strip():
        raise Refused(f"a Waiver needs a reason: --waive '{check}=why it is accepted'")
    return check.strip(), why.strip()


def _print_checks(results, approval, blockout):
    for result in results:
        waived = approval and result.check in approval.waivers
        mark = "pass" if result.passed else "waived" if waived else "MISS"
        measured, target = _amount(result.measured, result.unit), _amount(result.target, result.unit)
        goal = f"≤ {target}" if result.at_most else f"/ {target} ±{result.tolerance:.0%}"
        print(f"  {mark:6}  {result.check}  {measured} {goal}")
    for reading in blockout.readings:
        if reading.measure is None:
            print(f"  {'—':6}  reading {reading.phrase}  not measurable: {reading.meaning}")


def _amount(value, unit):
    if unit == "s":
        minutes, seconds = divmod(round(value), 60)
        return f"{minutes}:{seconds:02d}"
    if unit == "°":
        return f"{value:.1f}°"
    return f"{value:.0f} m"


if __name__ == "__main__":
    sys.exit(main())
