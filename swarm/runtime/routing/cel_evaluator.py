"""Simple CEL-like evaluator for routing conditions."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional, Tuple

from .base import EdgeCondition

logger = logging.getLogger(__name__)


class CELEvaluator:
    """Simple CEL-like expression evaluator."""

    def __init__(self):
        self._operators = {
            "equals": lambda a, b: a == b,
            "not_equals": lambda a, b: a != b,
            "in": lambda a, b: a in b if isinstance(b, (list, tuple, set)) else False,
            "not_in": lambda a, b: a not in b if isinstance(b, (list, tuple, set)) else True,
            "contains": lambda a, b: b in a if isinstance(a, str) else False,
            "gt": lambda a, b: a > b if a is not None and b is not None else False,
            "lt": lambda a, b: a < b if a is not None and b is not None else False,
            "gte": lambda a, b: a >= b if a is not None and b is not None else False,
            "lte": lambda a, b: a <= b if a is not None and b is not None else False,
            "matches": lambda a, b: bool(re.search(b, a)) if isinstance(a, str) else False,
        }

    def evaluate_condition(
        self,
        condition: EdgeCondition,
        context: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """Evaluate an edge condition against context."""
        try:
            if condition.expression:
                return self._evaluate_expression(condition.expression, context)

            if condition.field is None:
                return True, None

            field_value = self._resolve_field(condition.field, context)
            operator = condition.operator
            expected_value = condition.value

            if operator not in self._operators:
                return False, f"Unknown operator: {operator}"

            op_func = self._operators[operator]
            result = op_func(field_value, expected_value)
            return result, None

        except Exception as e:
            logger.debug("Condition evaluation error: %s", e)
            return False, str(e)

    def _resolve_field(self, field_path: str, context: Dict[str, Any]) -> Any:
        """Resolve a field path in the context."""
        parts = field_path.split(".")
        value: Any = context

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif hasattr(value, part):
                value = getattr(value, part)
            elif hasattr(value, "get"):
                value = value.get(part)
            else:
                return None

            if value is None:
                return None

        return value

    def _evaluate_expression(
        self,
        expression: str,
        context: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """Evaluate a CEL-like expression."""
        try:
            expr = expression.strip()

            if "||" in expr:
                parts = [p.strip() for p in expr.split("||")]
                for part in parts:
                    result, err = self._evaluate_simple_expression(part, context)
                    if err is None and result:
                        return True, None
                return False, None

            if "&&" in expr:
                parts = [p.strip() for p in expr.split("&&")]
                for part in parts:
                    result, err = self._evaluate_simple_expression(part, context)
                    if err is not None or not result:
                        return False, err
                return True, None

            return self._evaluate_simple_expression(expr, context)

        except Exception as e:
            return False, str(e)

    def _evaluate_simple_expression(
        self,
        expr: str,
        context: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """Evaluate a simple comparison expression."""
        operators_re = r"(==|!=|>=|<=|>|<)"
        match = re.split(operators_re, expr)

        if len(match) != 3:
            return False, f"Invalid expression: {expr}"

        left = match[0].strip()
        operator = match[1]
        right = match[2].strip()

        left_value = self._resolve_value(left, context)
        right_value = self._resolve_value(right, context)

        if operator == "==":
            return left_value == right_value, None
        if operator == "!=":
            return left_value != right_value, None
        if operator == ">=":
            return left_value >= right_value, None
        if operator == "<=":
            return left_value <= right_value, None
        if operator == ">":
            return left_value > right_value, None
        if operator == "<":
            return left_value < right_value, None

        return False, f"Unknown operator: {operator}"

    def _resolve_value(self, value_str: str, context: Dict[str, Any]) -> Any:
        """Resolve a value from string representation or context."""
        value_str = value_str.strip()

        if (value_str.startswith("'") and value_str.endswith("'")) or (
            value_str.startswith('"') and value_str.endswith('"')
        ):
            return value_str[1:-1]

        if value_str.lower() == "true":
            return True
        if value_str.lower() == "false":
            return False

        try:
            if "." in value_str:
                return float(value_str)
            return int(value_str)
        except ValueError:
            pass

        return self._resolve_field(value_str, context)
