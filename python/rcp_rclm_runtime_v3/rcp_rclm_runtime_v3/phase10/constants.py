from __future__ import annotations

from collections.abc import Sequence
from typing import Final, Literal, cast

from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import require_string, require_structural_integer

PHASE10_CONTRACT_VERSION: Final[str] = "rcp-rclm-executable-v3-phase-10-substrate-v1"
ARCHITECTURE_ID: Final[str] = "rclm-compact-decoder-13m-v1"
TOKENIZER_ID: Final[str] = "rclm-utf8-byte-tokenizer-v1"
MODEL_FAMILY: Final[str] = "compact_decoder_only_transformer_v1"

VOCAB_SIZE: Final[int] = 260
BYTE_TOKEN_COUNT: Final[int] = 256
PAD_TOKEN_ID: Final[int] = 256
BOS_TOKEN_ID: Final[int] = 257
EOS_TOKEN_ID: Final[int] = 258
SEP_TOKEN_ID: Final[int] = 259
CONTEXT_LENGTH: Final[int] = 512
LAYER_COUNT: Final[int] = 8
MODEL_WIDTH: Final[int] = 320
HEAD_COUNT: Final[int] = 5
HEAD_WIDTH: Final[int] = 64
MLP_HIDDEN_WIDTH: Final[int] = 1280
BASE_PARAMETER_COUNT: Final[int] = 13_195_840
LORA_RANK: Final[int] = 8
LORA_ALPHA: Final[int] = 8
LORA_PARAMETER_COUNT: Final[int] = 430_080
EXTENDED_PARAMETER_COUNT: Final[int] = BASE_PARAMETER_COUNT + LORA_PARAMETER_COUNT
TENSOR_DTYPE: Final[str] = "int16"
TENSOR_BYTE_ORDER: Final[str] = "little"
QUANTIZATION_SCALE_NUMERATOR: Final[int] = 1
QUANTIZATION_SCALE_DENOMINATOR: Final[int] = 4096

ARCHITECTURE_SCHEMA_ID: Final[str] = "runtime.v3.phase10.architecture.v1"
TOKENIZER_SCHEMA_ID: Final[str] = "runtime.v3.phase10.tokenizer_manifest.v1"
TENSOR_SPEC_SCHEMA_ID: Final[str] = "runtime.v3.phase10.tensor_spec.v1"
TENSOR_RECORD_SCHEMA_ID: Final[str] = "runtime.v3.phase10.tensor_record.v1"
TENSOR_MANIFEST_SCHEMA_ID: Final[str] = "runtime.v3.phase10.tensor_manifest.v1"
ADAPTER_MANIFEST_SCHEMA_ID: Final[str] = "runtime.v3.phase10.adapter_manifest.v1"
PACKAGE_MANIFEST_SCHEMA_ID: Final[str] = "runtime.v3.phase10.model_package_manifest.v1"
PACKAGE_REPORT_SCHEMA_ID: Final[str] = "runtime.v3.phase10.package_report.v1"
EXTENSION_REPORT_SCHEMA_ID: Final[str] = "runtime.v3.phase10.extension_report.v1"
REFERENCE_REPORT_SCHEMA_ID: Final[str] = "runtime.v3.phase10.reference_report.v1"

TensorRole = Literal["base_weight", "adapter_a", "adapter_b"]
AdapterStatus = Literal["absent", "zero_output_extension", "trained"]

LORA_TARGET_MODULES: Final[Sequence[str]] = (
    "attn_qkv",
    "attn_output",
    "mlp_down",
    "mlp_gate",
    "mlp_up",
)


def require_exact_string(value: object, expected: str, path: str) -> str:
    text = require_string(value, path)
    if text != expected:
        raise SchemaValidationError(path, f"expected {expected}")
    return text


def require_exact_integer(value: object, expected: int, path: str) -> int:
    number = require_structural_integer(value, path)
    if number != expected:
        raise SchemaValidationError(path, f"expected {expected}")
    return number


def require_boolean(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        raise SchemaValidationError(path, "expected Boolean")
    return value


def require_string_sequence(value: object, path: str) -> Sequence[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise SchemaValidationError(path, "expected an array")
    return tuple(require_string(item, f"{path}[{index}]") for index, item in enumerate(value))


def require_integer_sequence(value: object, path: str) -> Sequence[int]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise SchemaValidationError(path, "expected an array")
    return tuple(
        require_structural_integer(item, f"{path}[{index}]", minimum=1)
        for index, item in enumerate(value)
    )


def cast_tensor_role(value: str) -> TensorRole:
    if value not in {"base_weight", "adapter_a", "adapter_b"}:
        raise SchemaValidationError("phase10.tensor.role", "unsupported tensor role")
    return cast(TensorRole, value)


def cast_adapter_status(value: str) -> AdapterStatus:
    if value not in {"absent", "zero_output_extension", "trained"}:
        raise SchemaValidationError("phase10.adapter.status", "unsupported adapter status")
    return cast(AdapterStatus, value)
