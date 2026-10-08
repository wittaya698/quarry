"""The subscription adapter, driven by a fake `claude` runner: no test starts
the real binary. Its replies copy what Claude Code 2.1 prints for
`claude -p --output-format json`."""
import json
import os
import subprocess
from pathlib import Path

import pytest

from quarry.brief import Brief
from quarry.claude_agent import AgentUnavailable
from quarry.claude_code_agent import ClaudeCodeAgent
from quarry.identity import Human
from quarry.site import Site
from quarry.validation import InvalidDraft
from test_agent import FORCED, ISLAND, blockout_output, refine_output

ALICE = Human("alice")


def drafted(output):
    """`claude -p` succeeding with a structured answer."""
    reply = {"type": "result", "subtype": "success", "is_error": False, "result": "",
             "stop_reason": "end_turn", "structured_output": output}
    return 0, json.dumps(reply)


def failed(text, code=1):
    """`claude -p` reporting an error in its JSON envelope, e.g. when logged out."""
    reply = {"type": "result", "subtype": "success", "is_error": True, "result": text,
             "stop_reason": "stop_sequence"}
    return code, json.dumps(reply)


class FakeClaude:
    """Stands in for `subprocess.run` on the `claude` binary: answers each
    draft with the next scripted reply and keeps every call."""

    def __init__(self, *replies, version="2.1.280 (Claude Code)"):
        self.replies = list(replies)
        self.version = version
        self.calls = []
        self.workdirs = []  # what each draft's working directory held while it ran

    def __call__(self, argv, **options):
        self.calls.append((argv, options))
        if options.get("cwd"):
            self.workdirs.append(sorted(p.name for p in Path(options["cwd"]).iterdir()))
        if argv[1:] == ["--version"]:
            return subprocess.CompletedProcess(argv, 0, stdout=f"{self.version}\n", stderr="")
        code, stdout = self.replies.pop(0)
        return subprocess.CompletedProcess(argv, code, stdout=stdout, stderr="")

    @property
    def drafts(self):
        return [(argv, options) for argv, options in self.calls if argv[1:] != ["--version"]]


@pytest.fixture
def island(tmp_path):
    return Site.create(tmp_path / "island", Brief.from_dict(ISLAND))


@pytest.fixture
def profile(tmp_path):
    return tmp_path / "quarry-profile"


def test_the_subscription_agent_drafts_a_blockout_that_becomes_a_revision(island, profile):
    claude = FakeClaude(drafted(blockout_output()))

    island.draft(ClaudeCodeAgent(run=claude, profile=profile))

    blockout = island.current_revision.blockout
    assert [l.name for l in blockout.landmarks] == ["spawn", "lighthouse"]
    assert blockout.paths[0].reason.text == "straight along the ridge"
    [(argv, options)] = claude.drafts
    assert argv[0] == "claude" and "-p" in argv
    assert "lighthouse" in options["input"]  # the Brief goes in on stdin


def test_a_draft_runs_isolated_in_the_quarry_profile_with_no_tools(island, profile, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-would-bill-per-token")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "would-bill-per-token")
    claude = FakeClaude(drafted(blockout_output()))

    island.draft(ClaudeCodeAgent(run=claude, profile=profile))

    [(argv, options)] = claude.drafts
    env = options["env"]
    assert env["CLAUDE_CONFIG_DIR"] == str(profile)  # never the developer's own profile
    assert "ANTHROPIC_API_KEY" not in env and "ANTHROPIC_AUTH_TOKEN" not in env
    assert claude.workdirs == [[]]  # no CLAUDE.md or AGENTS.md to discover
    assert argv[argv.index("--tools") + 1] == ""
    assert "--strict-mcp-config" in argv and "--no-session-persistence" in argv
    assert argv[argv.index("--model") + 1] == "claude-opus-5-5"
    assert argv[argv.index("--effort") + 1] == "high"


def test_the_latest_rejection_note_is_in_the_next_drafts_input(island, profile):
    claude = FakeClaude(drafted(blockout_output()), drafted(blockout_output()))
    agent = ClaudeCodeAgent(run=claude, profile=profile)
    island.draft(agent)
    island.reject(1, by=ALICE, note="the hill hides the lighthouse")

    island.draft(agent)

    [first, latest] = [options["input"] for _, options in claude.drafts]
    assert "the hill hides the lighthouse" not in first
    assert "the hill hides the lighthouse" in latest


def test_the_subscription_agent_drafts_a_refine_plan_from_the_approved_blockout(island, profile):
    claude = FakeClaude(drafted(blockout_output()), drafted(refine_output()))
    agent = ClaudeCodeAgent(run=claude, profile=profile)
    island.draft(agent)
    island.approve(1, by=ALICE)

    island.draft_refine_plan(agent)

    plan = island.current_refine_plan.plan
    assert [s.surface for s in plan.surfaces] == ["ground", "hill"]
    assert "straight along the ridge" in claude.drafts[-1][1]["input"]  # the approved Blockout


def unavailable(site, agent, match):
    with pytest.raises(AgentUnavailable, match=match):
        site.draft(agent)
    assert site.current_revision is None  # nothing reached the history


def test_a_logged_out_profile_says_how_to_log_in(island, profile):
    claude = FakeClaude(failed("Not logged in · Please run /login"))

    unavailable(island, ClaudeCodeAgent(run=claude, profile=profile),
                f"CLAUDE_CONFIG_DIR={profile} claude.*/login")


def test_a_usage_limit_is_reported_in_the_clis_own_words(island, profile):
    claude = FakeClaude(failed("You've hit your limit · resets 3pm"))

    unavailable(island, ClaudeCodeAgent(run=claude, profile=profile), "hit your limit · resets 3pm")


def test_a_missing_claude_binary_says_so(island, profile):
    def nowhere(argv, **options):
        raise FileNotFoundError(2, "No such file or directory", argv[0])

    unavailable(island, ClaudeCodeAgent(run=nowhere, profile=profile), "`claude` command was not found")


def test_a_draft_that_runs_too_long_is_stopped(island, profile):
    claude = FakeClaude()

    def slow(argv, **options):
        if argv[1:] == ["--version"]:
            return claude(argv, **options)
        raise subprocess.TimeoutExpired(argv, options["timeout"])

    unavailable(island, ClaudeCodeAgent(run=slow, profile=profile, timeout=120), "longer than 2 minutes")


def test_a_claude_code_too_old_for_the_model_is_refused_before_drafting(island, profile):
    claude = FakeClaude(drafted(blockout_output()), version="2.1.148 (Claude Code)")

    unavailable(island, ClaudeCodeAgent(run=claude, profile=profile), r"2\.1\.148.*2\.1\.280.*claude update")

    assert claude.drafts == []


def test_the_version_is_checked_once_per_agent(island, profile):
    claude = FakeClaude(drafted(blockout_output()), drafted(blockout_output()), version="2.2.0 (Claude Code)")
    agent = ClaudeCodeAgent(run=claude, profile=profile)

    island.draft(agent)
    island.draft(agent)

    assert [argv[1:] for argv, _ in claude.calls].count(["--version"]) == 1


@pytest.mark.parametrize("stop_reason", ["max_tokens", "refusal"])
def test_a_draft_the_model_did_not_finish_is_rejected(island, profile, stop_reason):
    reply = {"type": "result", "subtype": "success", "is_error": False, "result": "", "stop_reason": stop_reason}
    claude = FakeClaude((0, json.dumps(reply)))

    with pytest.raises(InvalidDraft, match=f"stopped early \\({stop_reason}\\)"):
        island.draft(ClaudeCodeAgent(run=claude, profile=profile))
    assert island.current_revision is None


def test_a_crash_without_a_json_reply_reports_what_claude_printed(island, profile):
    claude = FakeClaude()

    def crashing(argv, **options):
        if argv[1:] == ["--version"]:
            return claude(argv, **options)
        return subprocess.CompletedProcess(argv, 2, stdout="", stderr="Error: unknown option '--json-schema'\n")

    unavailable(island, ClaudeCodeAgent(run=crashing, profile=profile), "unknown option '--json-schema'")


def test_the_cli_drafts_on_the_subscription_by_default_even_with_an_api_key_set(tmp_path, monkeypatch):
    from quarry.cli import main

    bin_dir, home = tmp_path / "bin", tmp_path / "home"
    bin_dir.mkdir()
    home.mkdir()
    called = tmp_path / "claude-was-called"
    reply = json.dumps({"type": "result", "is_error": False, "stop_reason": "end_turn",
                        "structured_output": blockout_output()})
    fake = bin_dir / "claude"
    fake.write_text(
        "#!/usr/bin/env python3\n"
        "import os, sys\n"
        "if sys.argv[1:] == ['--version']:\n"
        "    print('2.1.280 (Claude Code)'); sys.exit()\n"
        "sys.stdin.read()\n"
        f"open({str(called)!r}, 'w').write(os.environ['CLAUDE_CONFIG_DIR'])\n"
        f"print({reply!r})\n"
    )
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-would-bill-per-token")
    brief = tmp_path / "brief.json"
    brief.write_text(json.dumps(ISLAND))
    site = tmp_path / "island"
    assert main(["new", str(site), "--brief", str(brief)]) == 0

    assert main(["draft", str(site)]) == 0

    assert called.read_text() == str(home / ".quarry" / "claude-code")
    assert Site.open(site).current_revision.number == 1


def test_the_latest_shortcut_misses_are_in_the_next_drafts_input(tmp_path, profile):
    forced = Site.create(tmp_path / "forced", Brief.from_dict(FORCED))
    claude = FakeClaude(drafted(blockout_output()), drafted(blockout_output()))
    agent = ClaudeCodeAgent(run=claude, profile=profile)
    forced.draft(agent)

    forced.draft(agent)

    [first, latest] = [options["input"] for _, options in claude.drafts]
    assert "Shortcut" not in first
    assert "Shortcut" in latest and "(268, 200)" in latest
