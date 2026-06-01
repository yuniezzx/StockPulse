from __future__ import annotations

import pytest

from pulse_core.screener.filters.universal.low_liquidity_filter import LowLiquidityFilter
from pulse_core.screener.filters.universal.new_stock_filter import NewStockFilter
from pulse_core.screener.filters.universal.st_filter import STFilter
from pulse_core.screener.registry import (
    UNIVERSAL_FILTERS,
    get_filter,
    get_strategy,
)


class TestUniversalFilters:
    def test_universal_filters_contains_three_layer1_classes(self):
        assert set(UNIVERSAL_FILTERS) == {STFilter, NewStockFilter, LowLiquidityFilter}

    def test_universal_filter_names_are_snake_case(self):
        for cls in UNIVERSAL_FILTERS:
            assert cls.name == cls.name.lower()
            assert "_" in cls.name or cls.name.isalnum()

    def test_universal_filter_layer_is_one(self):
        for cls in UNIVERSAL_FILTERS:
            assert cls.layer == 1


class TestGetFilter:
    def test_unregistered_raises_key_error(self):
        with pytest.raises(KeyError, match="未注册"):
            get_filter("nonexistent_filter")


class TestGetStrategy:
    def test_unregistered_raises_key_error(self):
        with pytest.raises(KeyError, match="未注册"):
            get_strategy("nonexistent_strategy")
