from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import strict_object

from rcp_rclm_runtime_v3.contract.common import require_schema
from rcp_rclm_runtime_v3.phase10.constants import (
    ARCHITECTURE_ID,
    ARCHITECTURE_SCHEMA_ID,
    BASE_PARAMETER_COUNT,
    CONTEXT_LENGTH,
    HEAD_COUNT,
    HEAD_WIDTH,
    LAYER_COUNT,
    MLP_HIDDEN_WIDTH,
    MODEL_FAMILY,
    MODEL_WIDTH,
    PHASE10_CONTRACT_VERSION,
    QUANTIZATION_SCALE_DENOMINATOR,
    QUANTIZATION_SCALE_NUMERATOR,
    TENSOR_BYTE_ORDER,
    TENSOR_DTYPE,
    TOKENIZER_ID,
    VOCAB_SIZE,
    require_boolean,
    require_exact_integer,
    require_exact_string,
)


@dataclass(frozen=True, slots=True)
class TensorBlueprint:
    name: str
    shape: Sequence[int]

    def __post_init__(self) -> None:
        shape = tuple(self.shape)
        if not self.name:
            raise SchemaValidationError("phase10.blueprint.name", "name must be nonempty")
        if not shape or any(isinstance(item, bool) or not isinstance(item, int) or item < 1 for item in shape):
            raise SchemaValidationError("phase10.blueprint.shape", "shape must contain positive integers")
        object.__setattr__(self, "shape", shape)

    @property
    def element_count(self) -> int:
        result = 1
        for dimension in self.shape:
            result *= dimension
        return result


@dataclass(frozen=True, slots=True)
class CompactTransformerArchitecture:
    architecture_id: str = ARCHITECTURE_ID
    model_family: str = MODEL_FAMILY
    tokenizer_id: str = TOKENIZER_ID
    context_length: int = CONTEXT_LENGTH
    vocabulary_size: int = VOCAB_SIZE
    layer_count: int = LAYER_COUNT
    model_width: int = MODEL_WIDTH
    head_count: int = HEAD_COUNT
    head_width: int = HEAD_WIDTH
    mlp_hidden_width: int = MLP_HIDDEN_WIDTH
    normalization: str = "rms_norm"
    activation: str = "silu_gated"
    attention: str = "causal_scaled_dot_product"
    position_encoding: str = "rotary_v1"
    tied_token_embeddings: bool = True
    tensor_dtype: str = TENSOR_DTYPE
    tensor_byte_order: str = TENSOR_BYTE_ORDER
    quantization_scale_numerator: int = QUANTIZATION_SCALE_NUMERATOR
    quantization_scale_denominator: int = QUANTIZATION_SCALE_DENOMINATOR
    base_parameter_count: int = BASE_PARAMETER_COUNT
    contract_version: str = PHASE10_CONTRACT_VERSION

    schema_id: ClassVar[str] = ARCHITECTURE_SCHEMA_ID

    def __post_init__(self) -> None:
        expected_strings = {
            "architecture_id": ARCHITECTURE_ID,
            "model_family": MODEL_FAMILY,
            "tokenizer_id": TOKENIZER_ID,
            "normalization": "rms_norm",
            "activation": "silu_gated",
            "attention": "causal_scaled_dot_product",
            "position_encoding": "rotary_v1",
            "tensor_dtype": TENSOR_DTYPE,
            "tensor_byte_order": TENSOR_BYTE_ORDER,
            "contract_version": PHASE10_CONTRACT_VERSION,
        }
        for name, expected in expected_strings.items():
            if getattr(self, name) != expected:
                raise SchemaValidationError(f"phase10.architecture.{name}", f"expected {expected}")
        expected_integers = {
            "context_length": CONTEXT_LENGTH,
            "vocabulary_size": VOCAB_SIZE,
            "layer_count": LAYER_COUNT,
            "model_width": MODEL_WIDTH,
            "head_count": HEAD_COUNT,
            "head_width": HEAD_WIDTH,
            "mlp_hidden_width": MLP_HIDDEN_WIDTH,
            "quantization_scale_numerator": QUANTIZATION_SCALE_NUMERATOR,
            "quantization_scale_denominator": QUANTIZATION_SCALE_DENOMINATOR,
            "base_parameter_count": BASE_PARAMETER_COUNT,
        }
        for name, expected in expected_integers.items():
            if getattr(self, name) != expected:
                raise SchemaValidationError(f"phase10.architecture.{name}", f"expected {expected}")
        if self.tied_token_embeddings is not True:
            raise SchemaValidationError(
                "phase10.architecture.tied_token_embeddings",
                "selected architecture requires tied token embeddings",
            )
        if self.model_width != self.head_count * self.head_width:
            raise SchemaValidationError(
                "phase10.architecture.head_width",
                "head_count multiplied by head_width must equal model_width",
            )
        observed = sum(item.element_count for item in self.base_tensor_blueprints())
        if observed != self.base_parameter_count:
            raise SchemaValidationError(
                "phase10.architecture.base_parameter_count",
                f"tensor graph contains {observed} parameters",
            )

    @property
    def architecture_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def base_tensor_blueprints(self) -> Sequence[TensorBlueprint]:
        result: list[TensorBlueprint] = [
            TensorBlueprint("model.final_norm.weight", (self.model_width,)),
            TensorBlueprint(
                "model.token_embedding.weight",
                (self.vocabulary_size, self.model_width),
            ),
        ]
        for layer_index in range(self.layer_count):
            prefix = f"model.layers.{layer_index:02d}"
            result.extend(
                (
                    TensorBlueprint(f"{prefix}.attn_norm.weight", (self.model_width,)),
                    TensorBlueprint(
                        f"{prefix}.attn_output.weight",
                        (self.model_width, self.model_width),
                    ),
                    TensorBlueprint(
                        f"{prefix}.attn_qkv.weight",
                        (3 * self.model_width, self.model_width),
                    ),
                    TensorBlueprint(
                        f"{prefix}.mlp_down.weight",
                        (self.model_width, self.mlp_hidden_width),
                    ),
                    TensorBlueprint(
                        f"{prefix}.mlp_gate.weight",
                        (self.mlp_hidden_width, self.model_width),
                    ),
                    TensorBlueprint(f"{prefix}.mlp_norm.weight", (self.model_width,)),
                    TensorBlueprint(
                        f"{prefix}.mlp_up.weight",
                        (self.mlp_hidden_width, self.model_width),
                    ),
                )
            )
        return tuple(sorted(result, key=lambda item: item.name.encode("utf-8")))

    def graph_json(self) -> dict[str, object]:
        blocks = []
        for layer_index in range(self.layer_count):
            blocks.append(
                {
                    "index": layer_index,
                    "pre_attention_norm": "rms_norm",
                    "attention": "causal_scaled_dot_product",
                    "attention_projection": "fused_qkv",
                    "residual_after_attention": True,
                    "pre_mlp_norm": "rms_norm",
                    "mlp": "silu_gated",
                    "residual_after_mlp": True,
                }
            )
        return {
            "input": "token_ids",
            "embedding": "token_embedding",
            "position_encoding": self.position_encoding,
            "blocks": blocks,
            "final_norm": self.normalization,
            "output_head": "tied_token_embedding_transpose",
            "output": "next_token_logits",
        }

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "architecture_id": self.architecture_id,
            "model_family": self.model_family,
            "tokenizer_id": self.tokenizer_id,
            "context_length": self.context_length,
            "vocabulary_size": self.vocabulary_size,
            "layer_count": self.layer_count,
            "model_width": self.model_width,
            "head_count": self.head_count,
            "head_width": self.head_width,
            "mlp_hidden_width": self.mlp_hidden_width,
            "normalization": self.normalization,
            "activation": self.activation,
            "attention": self.attention,
            "position_encoding": self.position_encoding,
            "tied_token_embeddings": self.tied_token_embeddings,
            "tensor_dtype": self.tensor_dtype,
            "tensor_byte_order": self.tensor_byte_order,
            "quantization_scale_numerator": self.quantization_scale_numerator,
            "quantization_scale_denominator": self.quantization_scale_denominator,
            "base_parameter_count": self.base_parameter_count,
            "graph": self.graph_json(),
        }

    @classmethod
    def from_json(cls, value: object) -> "CompactTransformerArchitecture":
        fields = {
            "schema_id",
            "contract_version",
            "architecture_id",
            "model_family",
            "tokenizer_id",
            "context_length",
            "vocabulary_size",
            "layer_count",
            "model_width",
            "head_count",
            "head_width",
            "mlp_hidden_width",
            "normalization",
            "activation",
            "attention",
            "position_encoding",
            "tied_token_embeddings",
            "tensor_dtype",
            "tensor_byte_order",
            "quantization_scale_numerator",
            "quantization_scale_denominator",
            "base_parameter_count",
            "graph",
        }
        obj = strict_object(value, "phase10.architecture", fields)
        require_schema(obj["schema_id"], cls.schema_id, "phase10.architecture.schema_id")
        result = cls(
            contract_version=require_exact_string(
                obj["contract_version"], PHASE10_CONTRACT_VERSION, "phase10.architecture.contract_version"
            ),
            architecture_id=require_exact_string(
                obj["architecture_id"], ARCHITECTURE_ID, "phase10.architecture.architecture_id"
            ),
            model_family=require_exact_string(
                obj["model_family"], MODEL_FAMILY, "phase10.architecture.model_family"
            ),
            tokenizer_id=require_exact_string(
                obj["tokenizer_id"], TOKENIZER_ID, "phase10.architecture.tokenizer_id"
            ),
            context_length=require_exact_integer(
                obj["context_length"], CONTEXT_LENGTH, "phase10.architecture.context_length"
            ),
            vocabulary_size=require_exact_integer(
                obj["vocabulary_size"], VOCAB_SIZE, "phase10.architecture.vocabulary_size"
            ),
            layer_count=require_exact_integer(
                obj["layer_count"], LAYER_COUNT, "phase10.architecture.layer_count"
            ),
            model_width=require_exact_integer(
                obj["model_width"], MODEL_WIDTH, "phase10.architecture.model_width"
            ),
            head_count=require_exact_integer(
                obj["head_count"], HEAD_COUNT, "phase10.architecture.head_count"
            ),
            head_width=require_exact_integer(
                obj["head_width"], HEAD_WIDTH, "phase10.architecture.head_width"
            ),
            mlp_hidden_width=require_exact_integer(
                obj["mlp_hidden_width"], MLP_HIDDEN_WIDTH, "phase10.architecture.mlp_hidden_width"
            ),
            normalization=require_exact_string(
                obj["normalization"], "rms_norm", "phase10.architecture.normalization"
            ),
            activation=require_exact_string(
                obj["activation"], "silu_gated", "phase10.architecture.activation"
            ),
            attention=require_exact_string(
                obj["attention"], "causal_scaled_dot_product", "phase10.architecture.attention"
            ),
            position_encoding=require_exact_string(
                obj["position_encoding"], "rotary_v1", "phase10.architecture.position_encoding"
            ),
            tied_token_embeddings=require_boolean(
                obj["tied_token_embeddings"], "phase10.architecture.tied_token_embeddings"
            ),
            tensor_dtype=require_exact_string(
                obj["tensor_dtype"], TENSOR_DTYPE, "phase10.architecture.tensor_dtype"
            ),
            tensor_byte_order=require_exact_string(
                obj["tensor_byte_order"], TENSOR_BYTE_ORDER, "phase10.architecture.tensor_byte_order"
            ),
            quantization_scale_numerator=require_exact_integer(
                obj["quantization_scale_numerator"],
                QUANTIZATION_SCALE_NUMERATOR,
                "phase10.architecture.quantization_scale_numerator",
            ),
            quantization_scale_denominator=require_exact_integer(
                obj["quantization_scale_denominator"],
                QUANTIZATION_SCALE_DENOMINATOR,
                "phase10.architecture.quantization_scale_denominator",
            ),
            base_parameter_count=require_exact_integer(
                obj["base_parameter_count"], BASE_PARAMETER_COUNT, "phase10.architecture.base_parameter_count"
            ),
        )
        if obj["graph"] != result.graph_json():
            raise SchemaValidationError("phase10.architecture.graph", "graph does not match selected architecture")
        return result


__all__ = ["CompactTransformerArchitecture", "TensorBlueprint"]
