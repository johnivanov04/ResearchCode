"""Deliberately defective variants ("mutants") of a reference solution.

A mutant is a realistic defect applied to a reference solution by exact text replacement
(every ``old`` string must occur exactly once, so a patch can never silently do nothing).
Mutants validate an evaluator (a defect must lower the hidden pass rate) and measure the
quality of a submission's own tests (mutation score). The genuine mutants are private; the
public fixture evaluator has its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Mutant:
    task: str
    name: str
    description: str
    replacements: tuple[tuple[str, str], ...]
    reference: Path

    def source(self) -> str:
        text = self.reference.read_text(encoding="utf-8")
        for old, new in self.replacements:
            count = text.count(old)
            if count != 1:
                raise ValueError(f"{self.task}/{self.name}: expected one occurrence of {old!r}, found {count}")
            text = text.replace(old, new)
        return text
