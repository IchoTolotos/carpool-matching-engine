"""Stable public errors raised by the matching engine."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    """Machine-readable engine error codes."""

    INVALID_MATRIX = "invalid_matrix"
    INVALID_PROBLEM = "invalid_problem"
    NO_SOLUTION = "no_solution"


class MatchingEngineError(Exception):
    """An expected engine failure with a stable code and structured context."""

    def __init__(self, code: ErrorCode, message: str, **context: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.context = context
