# Copyright (c) 2026 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_ndc_directory

import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).parent.parent / "scripts"))
from check_lexical_architecture import check_file, main  # type: ignore[import-not-found]


def test_check_file_syntax_error(tmp_path: Path) -> None:
    test_file = tmp_path / "test_syntax_error.py"
    test_file.write_text("class Def InvalidSyntax:\n  pass")

    errors = check_file(test_file)
    assert len(errors) == 1
    assert "Syntax error:" in errors[0]


def test_check_file_read_error(tmp_path: Path) -> None:
    test_file = tmp_path / "non_existent.py"
    errors = check_file(test_file)
    assert len(errors) == 1
    assert "Error reading file:" in errors[0]


def test_main_no_src_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Temporarily change to a directory without a src folder
    with monkeypatch.context() as m:
        m.chdir(tmp_path)
        result = main()
        assert result == 1


def test_main_with_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Setup mock src directory with a bad file
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    bad_file = src_dir / "bad.py"
    bad_file.write_text("class BadClass:\n  pass")

    with monkeypatch.context() as m:
        m.chdir(tmp_path)
        result = main()
        assert result == 1


def test_main_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Setup mock src directory with a good file
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    good_file = src_dir / "good.py"
    good_file.write_text("class GoodEvent:\n  pass")

    # Check that skipping itself works
    checker_file = src_dir / "check_lexical_architecture.py"
    checker_file.write_text("class IgnoreMe:\n  pass")

    with monkeypatch.context() as m:
        m.chdir(tmp_path)
        result = main()
        assert result == 0
