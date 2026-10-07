"""The Agent port's subscription adapter: drafts through the Claude Code CLI
(`claude -p`), so Drafts come out of the developer's Claude subscription rather
than per-token API billing (`--agent subscription`).

It shares its prompts, schemas, model and effort with the API adapter, so a
prompt tuned on one is tuned for the other.
"""
import json
import os
import subprocess
import tempfile
from pathlib import Path

from quarry.claude_agent import EFFORT, MODEL, AgentUnavailable, ClaudeDrafter
from quarry.validation import InvalidDraft

MINIMUM_VERSION = (2, 1, 280)  # the first Claude Code that runs MODEL
PROFILE = Path(".quarry") / "claude-code"  # under the home directory
# Credentials that would make the CLI bill per token instead of the subscription.
_API_CREDENTIALS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")


class ClaudeCodeAgent(ClaudeDrafter):
    """Drafts on the Claude subscription through `claude -p` (`--agent subscription`)."""

    def __init__(self, run=subprocess.run, profile=None, model=MODEL, timeout=15 * 60):
        self.run = run
        self.profile = Path(profile) if profile else Path.home() / PROFILE
        self.model = model
        self.timeout = timeout  # seconds; a high-effort Draft can take minutes
        self._version_checked = False

    def _ask(self, system, prompt, schema):
        self._require_version()
        argv = [
            "claude", "-p",
            "--model", self.model,
            "--effort", EFFORT,
            "--system-prompt", system,
            "--json-schema", json.dumps(schema),
            "--output-format", "json",
            # Isolation: the model sees Quarry's prompt and nothing of the developer's.
            "--tools", "",
            "--strict-mcp-config",
            "--no-session-persistence",
        ]
        return self._read(self._run_isolated(argv, prompt))

    def _run_isolated(self, argv, prompt):
        """Run in Quarry's own profile from an empty directory, so no CLAUDE.md,
        memory, hook or MCP server of the developer's reaches the model, and
        with no API credential, so the subscription is what pays."""
        env = {k: v for k, v in os.environ.items() if k not in _API_CREDENTIALS}
        env["CLAUDE_CONFIG_DIR"] = str(self.profile)
        self.profile.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="quarry-draft-") as empty:
            try:
                return self._claude(argv, input=prompt, env=env, cwd=empty, timeout=self.timeout)
            except subprocess.TimeoutExpired:
                raise AgentUnavailable(
                    f"Claude Code took longer than {self.timeout / 60:g} minutes; nothing was drafted"
                ) from None

    def _read(self, finished):
        """The Draft from `claude -p --output-format json`, or why there is none."""
        try:
            reply = json.loads(finished.stdout)
        except json.JSONDecodeError:
            printed = (finished.stderr or finished.stdout).strip() or f"exit status {finished.returncode}"
            raise AgentUnavailable(f"Claude Code failed: {printed}") from None
        if reply.get("is_error"):
            message = reply.get("result", "")
            if "not logged in" in message.lower():
                raise AgentUnavailable(
                    "Quarry's Claude Code profile is not logged in. Log in once with "
                    f"`CLAUDE_CONFIG_DIR={self.profile} claude`, then type /login"
                )
            raise AgentUnavailable(f"Claude Code could not draft: {message}")
        if "structured_output" not in reply:
            raise InvalidDraft(f"the model stopped early ({reply.get('stop_reason')}); nothing was drafted")
        return reply["structured_output"]

    def _require_version(self):
        if self._version_checked:
            return
        printed = self._claude(["claude", "--version"]).stdout.strip()  # e.g. "2.1.280 (Claude Code)"
        try:
            version = tuple(int(part) for part in printed.split()[0].split("."))
        except (IndexError, ValueError):
            raise AgentUnavailable(f"could not read the Claude Code version from {printed!r}") from None
        if version < MINIMUM_VERSION:
            needed = ".".join(map(str, MINIMUM_VERSION))
            raise AgentUnavailable(
                f"Claude Code {printed.split()[0]} cannot run {self.model}; it needs {needed} or newer. "
                "Run `claude update`"
            )
        self._version_checked = True

    def _claude(self, argv, **options):
        try:
            return self.run(argv, capture_output=True, text=True, **options)
        except FileNotFoundError:
            raise AgentUnavailable(
                "the `claude` command was not found: install Claude Code, or use --agent api or --agent fake"
            ) from None
