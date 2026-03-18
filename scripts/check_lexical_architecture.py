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
import re
import sys
from pathlib import Path


class LexicalArchitectureChecker(ast.NodeVisitor):
    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.errors: list[str] = []
        self.valid_suffixes = (
            "Event",
            "Receipt",
            "Intent",
            "Task",
            "Policy",
            "Contract",
            "State",
            "Manifest",
        )
        self.forbidden_words = ("Update", "Delete", "Remove", "List", "Data", "Create")
        # Compile regexes for each forbidden word, allowing prefixes/suffixes
        # that split words like underscore or CamelCase.
        # But for 'Data', we don't want to match 'Database'.
        self.forbidden_patterns = [
            re.compile(rf"(?:^|_|(?<=[a-z]))({word})(?:$|_|(?=[A-Z]))", re.IGNORECASE) for word in self.forbidden_words
        ]

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        # Check Anti-CRUD Mandate
        for word, pattern in zip(self.forbidden_words, self.forbidden_patterns, strict=False):
            if pattern.search(node.name):
                self.errors.append(
                    f"{self.filename}:{node.lineno}: Class '{node.name}' violates "
                    f"Anti-CRUD Mandate (contains forbidden word '{word}')"
                )

        # Check Categorical Suffixing (mainly for models/states)
        # To avoid false positives on standard exceptions or utility classes,
        # we enforce this on classes that don't end with generic suffixes like 'Checker'.
        # According to AGENTS.md, "Every object name MUST terminate with a strictly typed suffix"
        # However, we must be careful not to break existing valid code if it's already compliant.
        # Let's check if it ends with one of the valid suffixes if it's not a generic Python class type.
        has_valid_suffix = any(node.name.endswith(s) for s in self.valid_suffixes)

        # Exception classes and internal utils might be exempt, but per strict rules:
        # Let's enforce it on all classes except standard exceptions or classes defined in this script itself.
        if not has_valid_suffix and not node.name.endswith(("Exception", "Error", "Checker", "Visitor")):
            self.errors.append(
                f"{self.filename}:{node.lineno}: Class '{node.name}' violates "
                f"Categorical Suffixing (must end with one of {self.valid_suffixes})"
            )

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Check Anti-CRUD Mandate for function names
        for word, pattern in zip(self.forbidden_words, self.forbidden_patterns, strict=False):
            if pattern.search(node.name):
                self.errors.append(
                    f"{self.filename}:{node.lineno}: Function '{node.name}' violates "
                    f"Anti-CRUD Mandate (contains forbidden word '{word}')"
                )
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        # Check Anti-CRUD Mandate for async function names
        for word, pattern in zip(self.forbidden_words, self.forbidden_patterns, strict=False):
            if pattern.search(node.name):
                self.errors.append(
                    f"{self.filename}:{node.lineno}: AsyncFunction '{node.name}' violates "
                    f"Anti-CRUD Mandate (contains forbidden word '{word}')"
                )
        self.generic_visit(node)


def check_file(filepath: Path) -> list[str]:
    try:
        content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(filepath))
    except SyntaxError as e:
        return [f"{filepath}:{e.lineno}: Syntax error: {e.msg}"]
    except Exception as e:
        return [f"{filepath}: Error reading file: {e}"]

    checker = LexicalArchitectureChecker(str(filepath))
    checker.visit(tree)
    return checker.errors


def main() -> int:
    src_dir = Path("src")
    if not src_dir.exists():
        print("Error: 'src' directory not found.")
        return 1

    all_errors = []
    # Find all python files in src directory
    for filepath in src_dir.rglob("*.py"):
        # We might want to skip the checker script itself to avoid false positives on its own classes
        if filepath.name == "check_lexical_architecture.py":
            continue

        errors = check_file(filepath)
        all_errors.extend(errors)

    if all_errors:
        print("Lexical Architecture Violations Found:")
        for err in all_errors:
            print(f"  - {err}")
        return 1
    print("Lexical Architecture check passed.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
