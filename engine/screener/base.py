from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class Pick:
    ts_code: str
    score: float
    signals: dict[str, Any] = field(default_factory=dict)


class Screener(ABC):
    name: str  # 策略名（子类必须定义，如 "breakout"）

    @abstractmethod
    async def run(self, trade_date: date) -> list[Pick]:
        """跑策略，返回当日选出的股票列表（顺序无所谓，runner 会排序）"""
