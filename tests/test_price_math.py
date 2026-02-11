"""
Unit tests for PriceMath / StockMath static utility methods.
"""
import pytest
from core.context import PriceMath, StockMath


class TestCalculateQuantityFromCash:
    def test_normal(self):
        qty = PriceMath.calculate_quantity_from_cash(1000.0, 50.0)
        assert qty == pytest.approx(20.0)

    def test_fractional(self):
        qty = PriceMath.calculate_quantity_from_cash(100.0, 33.33)
        assert qty == pytest.approx(100.0 / 33.33)

    def test_zero_cash(self):
        assert PriceMath.calculate_quantity_from_cash(0.0, 50.0) == 0.0

    def test_zero_price(self):
        assert PriceMath.calculate_quantity_from_cash(1000.0, 0.0) == 0.0

    def test_negative_cash(self):
        assert PriceMath.calculate_quantity_from_cash(-100.0, 50.0) == 0.0

    def test_negative_price(self):
        assert PriceMath.calculate_quantity_from_cash(100.0, -50.0) == 0.0

    def test_both_negative(self):
        assert PriceMath.calculate_quantity_from_cash(-100.0, -50.0) == 0.0

    def test_very_small_price(self):
        qty = PriceMath.calculate_quantity_from_cash(1000.0, 0.001)
        assert qty == pytest.approx(1_000_000.0)

    def test_very_large_values(self):
        qty = PriceMath.calculate_quantity_from_cash(1e12, 1e6)
        assert qty == pytest.approx(1e6)


class TestCalculateCashFromQuantity:
    def test_normal(self):
        cash = PriceMath.calculate_cash_from_quantity(20.0, 50.0)
        assert cash == pytest.approx(1000.0)

    def test_zero_quantity(self):
        assert PriceMath.calculate_cash_from_quantity(0.0, 50.0) == 0.0

    def test_zero_price(self):
        assert PriceMath.calculate_cash_from_quantity(20.0, 0.0) == 0.0

    def test_negative_quantity(self):
        assert PriceMath.calculate_cash_from_quantity(-10.0, 50.0) == 0.0

    def test_negative_price(self):
        assert PriceMath.calculate_cash_from_quantity(10.0, -50.0) == 0.0


class TestAliases:
    """StockMath is an alias for PriceMath; share_units methods delegate."""

    def test_stock_math_is_price_math(self):
        assert StockMath is PriceMath

    def test_share_units_from_money(self):
        result = PriceMath.calculate_share_units_from_money(500.0, 25.0)
        assert result == pytest.approx(20.0)

    def test_money_from_share_units(self):
        result = PriceMath.calculate_money_from_share_units(20.0, 25.0)
        assert result == pytest.approx(500.0)
