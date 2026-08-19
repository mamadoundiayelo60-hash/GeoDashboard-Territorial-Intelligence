"""Tests du langage de champs calculés."""

import pandas as pd
import pytest

from geodashboard_api.services.expressions import ExpressionError, calculate


def test_calculates_numeric_and_text_fields() -> None:
    frame = pd.DataFrame({"population": [100, 250], "name": ["Calais", "Marck"]})
    assert calculate("round(population / 3, 1)", frame).tolist() == [33.3, 83.3]
    assert calculate("upper(name)", frame).tolist() == ["CALAIS", "MARCK"]


@pytest.mark.parametrize(
    "expression",
    ["__import__('os').system('id')", "population.__class__", "open('/etc/passwd')"],
)
def test_rejects_hostile_expressions(expression: str) -> None:
    with pytest.raises(ExpressionError):
        calculate(expression, pd.DataFrame({"population": [100]}))
