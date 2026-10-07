# 11 — Subscription Agent: draft on the Claude subscription via Claude Code

Status: ready-for-agent

## Parent

`.scratch/quarry-mvp/PRD.md`

## What to build

Quarry runs only on its developer's own machine, so drafting should run on their Claude subscription rather than per-token API billing. Add a third adapter behind the Agent port, `ClaudeCodeAgent`, which drafts Blockouts and Refine Plans by running the Claude Code CLI headless (`claude -p`). It reuses the existing prompts and output schemas, and every output still passes the validation layer.

- **Default:** `quarry draft` and `quarry refine` use it unless told otherwise. No auto-detection: an API key in the environment never changes which adapter runs.
- **Names:** `--agent subscription | api | fake`. `api` is the existing `ClaudeAgent`, and `claude` stops being a choice.
- **Same model as `api`:** both Claude adapters read one pinned model (`claude-opus-5-5`) and effort (`high`), so a prompt tuned on one is tuned for the other.
- **Isolated context:** the CLI runs with a dedicated Quarry profile (`CLAUDE_CONFIG_DIR`, e.g. `~/.quarry/claude-code`), from an empty working directory, with no MCP servers (`--strict-mcp-config`), no tools (`--tools ""`) and no session persistence. A Draft sees only Quarry's system prompt and its input: never the developer's CLAUDE.md, memory, hooks, MCP instructions or email. (Checked on 2026-10-07: without this, `claude -p` from an empty directory carried the global CLAUDE.md, email and MCP instructions.)
- **Clear failures:** a CLI older than 2.1.280 (the first that runs `claude-opus-5-5`), a Quarry profile that isn't logged in, a missing `claude` binary, a hit usage limit or a timeout each fail with one actionable line and record nothing. The not-logged-in message gives the exact login command.

## Acceptance criteria

- [x] `ClaudeCodeAgent` drafts Blockouts and Refine Plans through `claude -p` with structured output, using the shared prompts and schemas
- [x] It is the CLI default; `--agent subscription | api | fake` selects the adapter, and an API key in the environment does not change the default
- [x] Both Claude adapters use the same pinned model and effort
- [x] The CLI is invoked with the Quarry profile, an empty working directory, no tools and no MCP servers (tested)
- [x] The latest Rejection note reaches the next Draft's input, as with `api`
- [x] An outdated CLI, a logged-out profile, a missing binary, a usage limit and a timeout each fail with an actionable message and record nothing (tested)
- [x] No test runs the real `claude` binary; tests inject a fake runner
- [x] README explains the one-time profile login and the `--agent` choices

## Blocked by

- `06-live-agent.md`
