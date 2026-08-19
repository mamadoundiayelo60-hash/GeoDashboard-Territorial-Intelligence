"""Langage minimal de champs calculés, sans eval ni accès système."""

import ast
import operator
from collections.abc import Callable
from typing import Any

import pandas as pd


class ExpressionError(ValueError):
    """Expression non autorisée ou incompatible."""


_BINARY: dict[type[ast.operator], Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
}
_UNARY: dict[type[ast.unaryop], Callable[[Any], Any]] = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def calculate(expression: str, frame: pd.DataFrame) -> pd.Series:
    """Évalue récursivement un arbre syntaxique explicitement autorisé."""
    try:
        tree = ast.parse(expression, mode="eval")
        result = _evaluate(tree.body, frame)
        series = (
            result
            if isinstance(result, pd.Series)
            else pd.Series([result] * len(frame), index=frame.index)
        )
        return series.replace([float("inf"), float("-inf")], pd.NA)
    except ExpressionError:
        raise
    except Exception as exc:
        raise ExpressionError("L'expression n'est pas compatible avec les données.") from exc


def _evaluate(node: ast.AST, frame: pd.DataFrame) -> Any:
    if isinstance(node, ast.Constant) and isinstance(
        node.value, (str, int, float, bool, type(None))
    ):
        return node.value
    if isinstance(node, ast.Name):
        geometry = getattr(frame, "geometry", None)
        geometry_name = getattr(geometry, "name", None)
        if node.id not in frame.columns or node.id == geometry_name:
            raise ExpressionError(f"Champ inconnu : {node.id}")
        return frame[node.id]
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        return _BINARY[type(node.op)](_evaluate(node.left, frame), _evaluate(node.right, frame))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_evaluate(node.operand, frame))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        args = [_evaluate(argument, frame) for argument in node.args]
        if node.keywords:
            raise ExpressionError("Les arguments nommés ne sont pas autorisés.")
        return _call(node.func.id, args)
    raise ExpressionError("Cette construction n'est pas autorisée.")


def _call(name: str, args: list[Any]) -> Any:
    if name == "abs" and len(args) == 1:
        return abs(args[0])
    if name == "round" and len(args) in {1, 2}:
        return args[0].round(int(args[1])) if isinstance(args[0], pd.Series) else round(*args)
    if name in {"upper", "lower", "length"} and len(args) == 1 and isinstance(args[0], pd.Series):
        strings = args[0].astype("string")
        return {"upper": strings.str.upper, "lower": strings.str.lower, "length": strings.str.len}[
            name
        ]()
    if name == "coalesce" and len(args) == 2:
        return (
            args[0].fillna(args[1])
            if isinstance(args[0], pd.Series)
            else (args[0] if args[0] is not None else args[1])
        )
    raise ExpressionError(f"Fonction non autorisée ou arguments invalides : {name}")
