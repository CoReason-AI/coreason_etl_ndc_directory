# Copyright (c) 2026 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_ndc_directory

import ast
import sys
from collections.abc import Generator
from pathlib import Path

import pytest

# Add scripts dir to path to import the script for testing
sys.path.append(str(Path(__file__).parent.parent / "scripts"))
from check_lexical_architecture import LexicalArchitectureChecker  # type: ignore[import-not-found]


@pytest.fixture
def checker() -> Generator[LexicalArchitectureChecker]:
    """Provides a fresh LexicalArchitectureChecker instance."""
    return LexicalArchitectureChecker("test_file.py")  # type: ignore[return-value]


def test_valid_class_name(checker: LexicalArchitectureChecker) -> None:
    code = """
class SystemConfigurationState:
    pass
"""
    tree = ast.parse(code)
    checker.visit(tree)
    assert len(checker.errors) == 0


def test_valid_function_name(checker: LexicalArchitectureChecker) -> None:
    code = """
def run_pipeline_task():
    pass
"""
    tree = ast.parse(code)
    checker.visit(tree)
    assert len(checker.errors) == 0


def test_invalid_class_suffix(checker: LexicalArchitectureChecker) -> None:
    code = """
class UserAccount:
    pass
"""
    tree = ast.parse(code)
    checker.visit(tree)
    assert len(checker.errors) == 1
    assert "violates Categorical Suffixing" in checker.errors[0]


def test_invalid_class_crud_name(checker: LexicalArchitectureChecker) -> None:
    code = """
class UserUpdateEvent:
    pass
"""
    tree = ast.parse(code)
    checker.visit(tree)
    # Violates Anti-CRUD (contains "Update") but has valid suffix.
    # The checker might catch just the Anti-CRUD or both, but we definitely expect Anti-CRUD error.
    assert len(checker.errors) >= 1
    assert any("violates Anti-CRUD Mandate" in err for err in checker.errors)


def test_invalid_function_crud_name(checker: LexicalArchitectureChecker) -> None:
    code = """
def create_new_record():
    pass
"""
    tree = ast.parse(code)
    checker.visit(tree)
    assert len(checker.errors) == 1
    assert "violates Anti-CRUD Mandate" in checker.errors[0]
    assert "'create'" in checker.errors[0].lower()


def test_invalid_async_function_crud_name(checker: LexicalArchitectureChecker) -> None:
    code = """
async def update_database():
    pass
"""
    tree = ast.parse(code)
    checker.visit(tree)
    assert len(checker.errors) >= 1
    assert any("violates Anti-CRUD Mandate" in err for err in checker.errors)
    assert any("'update'" in err.lower() for err in checker.errors)


def test_exempt_class_suffixes(checker: LexicalArchitectureChecker) -> None:
    code = """
class NetworkConnectionError(Exception):
    pass

class ASTNodeVisitor(ast.NodeVisitor):
    pass
"""
    tree = ast.parse(code)
    checker.visit(tree)
    assert len(checker.errors) == 0
