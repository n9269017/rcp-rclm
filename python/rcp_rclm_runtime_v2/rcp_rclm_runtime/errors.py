from __future__ import annotations

from typing import Final


class RuntimeValidationError(ValueError):
    __slots__ = ("code", "path", "detail")

    def __init__(self, code: str, path: str, detail: str) -> None:
        super().__init__(code, path, detail)
        self.code = code
        self.path = path
        self.detail = detail

    def __str__(self) -> str:
        location = f" at {self.path}" if self.path else ""
        return f"{self.code}{location}: {self.detail}"


class CanonicalizationError(RuntimeValidationError):
    def __init__(self, path: str, detail: str) -> None:
        super().__init__("CANONICALIZATION_FAILED", path, detail)


class SchemaValidationError(RuntimeValidationError):
    def __init__(self, path: str, detail: str) -> None:
        super().__init__("SCHEMA_MALFORMED", path, detail)


class UnsupportedScopeError(RuntimeValidationError):
    def __init__(self, path: str, detail: str) -> None:
        super().__init__("UNSUPPORTED_SCOPE", path, detail)


class NumericValidationError(RuntimeValidationError):
    def __init__(self, path: str, detail: str) -> None:
        super().__init__("NUMERIC_INVALID", path, detail)


HASH_HEX_LENGTH: Final[int] = 64
