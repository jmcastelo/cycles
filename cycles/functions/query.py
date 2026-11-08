"""
Queries: a condition on the subcycles of a level, such as ``trend > 0.5 and dharma < 0.4``, evaluated at once over
the whole level (numpy arrays).

The language is a small part of Python's expressions, checked node by node before it runs: numbers; names (the
measures, and the ones below); ``and``, ``or``, ``not``; comparisons, also chained (``0.2 < trend <= 0.6``);
``+ - * /`` and parentheses; and the functions ``count(age)`` (how many digits of that age the address has) and
``abs(x)``. Nothing else is accepted: no attributes, no indexing, no other calls.

Names besides the measures (``measure.MEASURES``):

* ``duration`` and ``start``: as fractions of the whole cycle; ``year`` (of the start) and ``years`` (the length),
  with a cycle model;
* ``index``: the time-order index in the level; ``depth``;
* ``a1``, ``a2``, …: the age of each level of the address (0 Satya … 3 Kali), ``first`` and ``last`` (the outermost
  and the innermost);
* the ages by name: ``Satya``, ``Treta``, ``Dvapara``, ``Kali`` (and ``Golden``, ``Silver``, ``Bronze``,
  ``Iron``), 0 to 3, so that ``last == Kali`` or ``count(Satya) >= 2`` read naturally.
"""

import ast

import numpy as np

AGES = {'Satya': 0, 'Treta': 1, 'Dvapara': 2, 'Kali': 3, 'Golden': 0, 'Silver': 1, 'Bronze': 2, 'Iron': 3}
OTHER_NAMES = ('duration', 'start', 'year', 'years', 'index', 'depth', 'first', 'last')
FUNCTIONS = ('count', 'abs')
_COMPARE = {ast.Lt: np.less, ast.LtE: np.less_equal, ast.Gt: np.greater, ast.GtE: np.greater_equal,
            ast.Eq: np.equal, ast.NotEq: np.not_equal}
_ARITHMETIC = {ast.Add: np.add, ast.Sub: np.subtract, ast.Mult: np.multiply, ast.Div: np.divide}


class QueryError(ValueError):
    """A query that cannot be read or evaluated, with a message for the user."""


def parse(text: str) -> ast.Expression:
    """The syntax tree of the query ``text``, checked to hold only what the language allows (``QueryError``)."""
    text = text.strip()
    if not text:
        raise QueryError('empty query')
    try:
        tree = ast.parse(text, mode='eval')
    except SyntaxError as error:
        raise QueryError(f"cannot read the query: {error.msg}") from None
    allowed = (ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not, ast.USub, ast.UAdd, ast.Compare,
               ast.BinOp, ast.Name, ast.Load, ast.Constant, ast.Call, *_COMPARE, *_ARITHMETIC)
    for node in ast.walk(tree):
        if not isinstance(node, allowed):
            raise QueryError(f"not allowed in a query: {type(node).__name__.lower()}")
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)) or \
                isinstance(node, ast.Constant) and isinstance(node.value, bool):
            raise QueryError(f"only numbers can be written in a query, not {node.value!r}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in FUNCTIONS or node.keywords \
                    or len(node.args) != 1:
                raise QueryError(f"the functions of a query are {', '.join(f + '(x)' for f in FUNCTIONS)}")
    return tree


def names_in(tree: ast.Expression) -> set[str]:
    """The names a query uses (its functions and the ages left out)."""
    functions = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call)}
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} - functions - set(AGES)


def evaluate(tree: ast.Expression, values: dict, lcoords: np.ndarray) -> np.ndarray:
    """
    The subcycles of a level that satisfy the query ``tree``: a boolean array (N,). ``values`` gives an array (N,)
    (or a number) for every name of ``names_in(tree)``; ``lcoords`` (N, depth) are the addresses, for ``count``.
    """
    n = len(lcoords)

    def walk(node):
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if node.id in AGES:
                return AGES[node.id]
            if node.id not in values:
                raise QueryError(f"unknown name in the query: {node.id}")
            return values[node.id]
        if isinstance(node, ast.BoolOp):
            parts = [np.asarray(walk(v), dtype=bool) for v in node.values]
            combine = np.logical_and if isinstance(node.op, ast.And) else np.logical_or
            result = parts[0]
            for part in parts[1:]:
                result = combine(result, part)
            return result
        if isinstance(node, ast.UnaryOp):
            operand = walk(node.operand)
            if isinstance(node.op, ast.Not):
                return np.logical_not(np.asarray(operand, dtype=bool))
            return -operand if isinstance(node.op, ast.USub) else operand
        if isinstance(node, ast.Compare):
            result, left = True, walk(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                right = walk(comparator)
                result = np.logical_and(result, _COMPARE[type(op)](left, right))
                left = right
            return result
        if isinstance(node, ast.BinOp):
            with np.errstate(divide='ignore', invalid='ignore'):
                return _ARITHMETIC[type(node.op)](walk(node.left), walk(node.right))
        if isinstance(node, ast.Call):
            argument = walk(node.args[0])
            if node.func.id == 'abs':
                return np.abs(argument)
            return (np.asarray(lcoords) == argument).sum(axis=1) if np.ndim(argument) == 0 else \
                (np.asarray(lcoords) == np.asarray(argument)[:, None]).sum(axis=1)
        raise QueryError(f"not allowed in a query: {type(node).__name__.lower()}")

    result = walk(tree)
    if np.ndim(result) == 0:
        return np.full(n, bool(result))
    result = np.asarray(result)
    if result.dtype != bool:
        raise QueryError('the query must be a condition (a comparison), not a number')
    return result


def age_names(depth: int) -> list[str]:
    """The names of the digits of an address of ``depth``: a1, a2, …"""
    return [f"a{k}" for k in range(1, depth + 1)]
