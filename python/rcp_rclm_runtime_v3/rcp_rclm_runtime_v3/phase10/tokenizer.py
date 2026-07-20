from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import strict_object

from rcp_rclm_runtime_v3.contract.common import require_hash, require_schema
from rcp_rclm_runtime_v3.phase10.constants import (
    BOS_TOKEN_ID,
    BYTE_TOKEN_COUNT,
    EOS_TOKEN_ID,
    PAD_TOKEN_ID,
    PHASE10_CONTRACT_VERSION,
    SEP_TOKEN_ID,
    TOKENIZER_ID,
    TOKENIZER_SCHEMA_ID,
    VOCAB_SIZE,
    require_exact_integer,
    require_exact_string,
)

_TOKENIZER_MAGIC = b"RCLM-UTF8-BYTE-TOKENIZER-V1\0"
_SPECIAL_TOKEN_BYTES = b"PAD=256\0BOS=257\0EOS=258\0SEP=259\0"


def tokenizer_bytes() -> bytes:
    return _TOKENIZER_MAGIC + bytes(range(BYTE_TOKEN_COUNT)) + _SPECIAL_TOKEN_BYTES


def vocabulary_json() -> dict[str, object]:
    tokens: list[dict[str, object]] = []
    for token_id in range(BYTE_TOKEN_COUNT):
        tokens.append(
            {
                "id": token_id,
                "kind": "byte",
                "value_hex": f"{token_id:02x}",
            }
        )
    tokens.extend(
        (
            {"id": PAD_TOKEN_ID, "kind": "special", "value": "<pad>"},
            {"id": BOS_TOKEN_ID, "kind": "special", "value": "<bos>"},
            {"id": EOS_TOKEN_ID, "kind": "special", "value": "<eos>"},
            {"id": SEP_TOKEN_ID, "kind": "special", "value": "<sep>"},
        )
    )
    return {
        "tokenizer_id": TOKENIZER_ID,
        "vocabulary_size": VOCAB_SIZE,
        "tokens": tokens,
    }


@dataclass(frozen=True, slots=True)
class ByteTokenizerManifest:
    tokenizer_id: str
    tokenizer_bytes_hash: str
    vocabulary_hash: str
    vocabulary_size: int
    byte_token_count: int
    pad_token_id: int
    bos_token_id: int
    eos_token_id: int
    sep_token_id: int
    contract_version: str = PHASE10_CONTRACT_VERSION

    schema_id: ClassVar[str] = TOKENIZER_SCHEMA_ID

    def __post_init__(self) -> None:
        if self.tokenizer_id != TOKENIZER_ID:
            raise SchemaValidationError("phase10.tokenizer.tokenizer_id", f"expected {TOKENIZER_ID}")
        require_hash(self.tokenizer_bytes_hash, "phase10.tokenizer.tokenizer_bytes_hash")
        require_hash(self.vocabulary_hash, "phase10.tokenizer.vocabulary_hash")
        expected = {
            "vocabulary_size": VOCAB_SIZE,
            "byte_token_count": BYTE_TOKEN_COUNT,
            "pad_token_id": PAD_TOKEN_ID,
            "bos_token_id": BOS_TOKEN_ID,
            "eos_token_id": EOS_TOKEN_ID,
            "sep_token_id": SEP_TOKEN_ID,
        }
        for name, value in expected.items():
            if getattr(self, name) != value:
                raise SchemaValidationError(f"phase10.tokenizer.{name}", f"expected {value}")
        if self.contract_version != PHASE10_CONTRACT_VERSION:
            raise SchemaValidationError(
                "phase10.tokenizer.contract_version",
                f"expected {PHASE10_CONTRACT_VERSION}",
            )
        if self.tokenizer_bytes_hash != sha256_hex(tokenizer_bytes()):
            raise SchemaValidationError(
                "phase10.tokenizer.tokenizer_bytes_hash",
                "hash does not identify the frozen tokenizer bytes",
            )
        if self.vocabulary_hash != canonical_json_hash(vocabulary_json()):
            raise SchemaValidationError(
                "phase10.tokenizer.vocabulary_hash",
                "hash does not identify the frozen vocabulary",
            )

    @property
    def manifest_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "tokenizer_id": self.tokenizer_id,
            "tokenizer_bytes_hash": self.tokenizer_bytes_hash,
            "vocabulary_hash": self.vocabulary_hash,
            "vocabulary_size": self.vocabulary_size,
            "byte_token_count": self.byte_token_count,
            "pad_token_id": self.pad_token_id,
            "bos_token_id": self.bos_token_id,
            "eos_token_id": self.eos_token_id,
            "sep_token_id": self.sep_token_id,
        }

    @classmethod
    def frozen(cls) -> "ByteTokenizerManifest":
        return cls(
            tokenizer_id=TOKENIZER_ID,
            tokenizer_bytes_hash=sha256_hex(tokenizer_bytes()),
            vocabulary_hash=canonical_json_hash(vocabulary_json()),
            vocabulary_size=VOCAB_SIZE,
            byte_token_count=BYTE_TOKEN_COUNT,
            pad_token_id=PAD_TOKEN_ID,
            bos_token_id=BOS_TOKEN_ID,
            eos_token_id=EOS_TOKEN_ID,
            sep_token_id=SEP_TOKEN_ID,
        )

    @classmethod
    def from_json(cls, value: object) -> "ByteTokenizerManifest":
        obj = strict_object(
            value,
            "phase10.tokenizer",
            {
                "schema_id",
                "contract_version",
                "tokenizer_id",
                "tokenizer_bytes_hash",
                "vocabulary_hash",
                "vocabulary_size",
                "byte_token_count",
                "pad_token_id",
                "bos_token_id",
                "eos_token_id",
                "sep_token_id",
            },
        )
        require_schema(obj["schema_id"], cls.schema_id, "phase10.tokenizer.schema_id")
        return cls(
            contract_version=require_exact_string(
                obj["contract_version"], PHASE10_CONTRACT_VERSION, "phase10.tokenizer.contract_version"
            ),
            tokenizer_id=require_exact_string(
                obj["tokenizer_id"], TOKENIZER_ID, "phase10.tokenizer.tokenizer_id"
            ),
            tokenizer_bytes_hash=require_hash(
                obj["tokenizer_bytes_hash"], "phase10.tokenizer.tokenizer_bytes_hash"
            ),
            vocabulary_hash=require_hash(obj["vocabulary_hash"], "phase10.tokenizer.vocabulary_hash"),
            vocabulary_size=require_exact_integer(
                obj["vocabulary_size"], VOCAB_SIZE, "phase10.tokenizer.vocabulary_size"
            ),
            byte_token_count=require_exact_integer(
                obj["byte_token_count"], BYTE_TOKEN_COUNT, "phase10.tokenizer.byte_token_count"
            ),
            pad_token_id=require_exact_integer(
                obj["pad_token_id"], PAD_TOKEN_ID, "phase10.tokenizer.pad_token_id"
            ),
            bos_token_id=require_exact_integer(
                obj["bos_token_id"], BOS_TOKEN_ID, "phase10.tokenizer.bos_token_id"
            ),
            eos_token_id=require_exact_integer(
                obj["eos_token_id"], EOS_TOKEN_ID, "phase10.tokenizer.eos_token_id"
            ),
            sep_token_id=require_exact_integer(
                obj["sep_token_id"], SEP_TOKEN_ID, "phase10.tokenizer.sep_token_id"
            ),
        )


class ByteTokenizer:
    __slots__ = ()

    manifest = ByteTokenizerManifest.frozen()

    @staticmethod
    def encode(text: str, *, add_bos: bool = False, add_eos: bool = False) -> Sequence[int]:
        if not isinstance(text, str):
            raise SchemaValidationError("phase10.tokenizer.text", "expected a string")
        tokens: list[int] = []
        if add_bos:
            tokens.append(BOS_TOKEN_ID)
        tokens.extend(text.encode("utf-8"))
        if add_eos:
            tokens.append(EOS_TOKEN_ID)
        return tuple(tokens)

    @staticmethod
    def decode(tokens: Sequence[int], *, stop_at_eos: bool = True) -> str:
        payload = bytearray()
        for index, token in enumerate(tokens):
            if isinstance(token, bool) or not isinstance(token, int):
                raise SchemaValidationError(
                    f"phase10.tokenizer.tokens[{index}]",
                    "token identifiers must be integers",
                )
            if 0 <= token < BYTE_TOKEN_COUNT:
                payload.append(token)
                continue
            if token == EOS_TOKEN_ID and stop_at_eos:
                break
            if token in {PAD_TOKEN_ID, BOS_TOKEN_ID, SEP_TOKEN_ID}:
                continue
            if token == EOS_TOKEN_ID:
                continue
            raise SchemaValidationError(
                f"phase10.tokenizer.tokens[{index}]",
                f"token identifier {token} is outside the frozen vocabulary",
            )
        try:
            return bytes(payload).decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise SchemaValidationError(
                "phase10.tokenizer.tokens",
                f"token sequence is not valid UTF-8: {exc}",
            ) from exc


__all__ = [
    "ByteTokenizer",
    "ByteTokenizerManifest",
    "tokenizer_bytes",
    "vocabulary_json",
]
