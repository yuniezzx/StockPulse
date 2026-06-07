"""Scorecard 子系统的核心类型契约。
提供:
- 三个 pydantic 模型：DimensionScore / Scorecard / TrackConfig
- 一个 dataclass：PickContext
- 两个 Protocol：DimensionScorer / Filter
详细契约见 docs/scorecard.md §4 / §5 / §9 / §10。
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Protocol
import pandas as pd
from pydantic import BaseModel, Field, model_validator

# --- Constants ---
SCORECARD_VERSION = "1.0"
WEIGHT_TOLERANCE = 1e-6


# --- Type Aliases ---
DimensionKind = Literal["signal", "risk"]


# --- Pydantic Models ---
class DimensionScore(BaseModel):
    """单个 dimension 的打分结果
    
    score 统一遵循「越高越好」语义（contract §5.3）。
    risk 类维度需由实现者反向归一化为「越高越安全」。
    """

    score: float = Field(..., ge=0.0, le=100.0, description="归一化后的分数，范围 [0.0, 100.0]")
    kind: DimensionKind 


class Scorecard(BaseModel):
    """一只票一日的通用打分卡（contract §4）。
    
    """

    version: Literal["1.0"] = SCORECARD_VERSION
    dimensions: dict[str, DimensionScore]

    @model_validator(mode="after")
    def _require_risk_dimension(self) -> "Scorecard":
        if not any(d.kind == "risk" for d in self.dimensions.values()):
            raise ValueError(
                "scorecard must contain at least one kind='risk' dimension"
            )
        return self


class TrackConfig(BaseModel):
    """tracks/{track}.yaml 解析后的 pydantic 模型。
    
    """
