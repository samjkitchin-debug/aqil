"""CLI offline execution tests."""

from __future__ import annotations

from pathlib import Path

from aqil_research.cli import main

FIXTURE = Path(__file__).parent / "fixtures" / "bls" / "api_lns14000000_success.json"


def test_cli_offline_run_succeeds(capsys) -> None:
    code = main(
        [
            "run",
            "--source",
            "bls",
            "--method",
            "sahm",
            "--fixture",
            str(FIXTURE),
            "--start-year",
            "2022",
            "--end-year",
            "2025",
        ],
    )
    captured = capsys.readouterr()
    assert code == 0
    assert "Sahm rule" in captured.out
    assert "execution_status=completed" in captured.out
