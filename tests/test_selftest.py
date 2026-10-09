import pytest

from quarry.cli import main
from quarry.selftest import CORRUPTIONS, selftest


def test_on_a_clean_install_every_corruption_is_caught(tmp_path):
    outcomes = selftest(tmp_path)

    assert [o.corruption for o in outcomes] == list(CORRUPTIONS)
    assert all(o.caught for o in outcomes), [o for o in outcomes if not o.caught]


def _no_op(*args, **kwargs):
    return None


def _flat(*args, **kwargs):
    return 0.0


# Each guard, switched off, and the corruption only it catches. Removing it must
# fail the self-test, or the self-test proves nothing about it.
GUARDS = {
    "the Path slope Check": (
        [("quarry.checks._steepest", _flat), ("quarry.checks._steepest_ground", _flat)],
        "a Path steepened past the Max Walkable Slope",
    ),
    "the round-trip's anchor check": ([("quarry.export._verify_anchors", _no_op)], "a Landmark moved off its Pad"),
    "the Pad Check": ([("quarry.checks._steepest_on_pad", _flat)], "Pad flatness broken"),
    "the round-trip's height check": (
        [("quarry.export._verify_heights", _no_op)], "Terrain changed without a Revision",
    ),
    "human-only acts": ([("quarry.site._require_human", _no_op)], "an Approval by the Agent"),
    "each Checkpoint's own Waivers": (
        [("quarry.site._Stage.refuse_approval", _no_op)], "a Waiver from Checkpoint #1 reused at Checkpoint #2",
    ),
    "Superseded is closed to every act": (
        [("quarry.site._Stage.live", lambda stage, number: stage.revision(number))],
        "an Export of Superseded Terrain",
    ),
}


@pytest.mark.parametrize("guard", GUARDS)
def test_removing_any_one_guard_fails_the_selftest(tmp_path, monkeypatch, guard):
    patches, corruption = GUARDS[guard]
    for target, replacement in patches:
        monkeypatch.setattr(target, replacement)

    outcomes = {o.corruption: o for o in selftest(tmp_path)}

    assert not outcomes[corruption].caught


def test_selftest_from_the_cli_reports_each_corruption_caught(capsys):
    assert main(["selftest"]) == 0

    out = capsys.readouterr().out
    assert out.startswith("selftest PASS")
    for corruption in CORRUPTIONS:
        assert f"caught  {corruption}" in out


def test_selftest_from_the_cli_fails_when_a_guard_lets_one_through(monkeypatch, capsys):
    monkeypatch.setattr("quarry.checks._steepest_on_pad", _flat)

    assert main(["selftest"]) == 1

    out = capsys.readouterr().out
    assert out.startswith("selftest FAIL") and "MISSED  Pad flatness broken" in out
