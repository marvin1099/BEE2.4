"""The Operation result allows executing math on instvars."""
from typing import Any, Container, Dict, List, NoReturn
import ast

from precomp import conditions
from srctools import Keyvalues, Vec, Entity, conv_bool
import srctools.logger


COND_MOD_NAME = 'Python'

LOGGER = srctools.logger.get_logger(__name__)

# Functions we allow the result to call.
FUNC_GLOBALS = {
    'int': int,

    'bool': conv_bool,
    'boolean': conv_bool,

    'string': str,
    'str': str,

    'float': float,

    'vector': Vec.from_str,
    'vec': Vec.from_str,

    'Vec': Vec,

    # Don't give other globals, they aren't needed.
    '__builtins__': None,
}

BANNED_COMPS = {
    ast.Is: 'is',
    ast.IsNot: 'is not',
    ast.In: 'in',
    ast.NotIn: 'not in',
}


class Checker(ast.NodeVisitor):
    """Scans through the AST, and checks all nodes to ensure they're allowed."""
    def __init__(self, var_names: Container[str]) -> None:
        self.var_names = var_names

    def generic_visit(self, node: ast.AST) -> NoReturn:
        """All other nodes are invalid."""
        raise ValueError(f'A {type(node).__name__} is not permitted!')

    def visit_Name(self, node: ast.Name) -> None:
        """A variable name."""
        if node.id not in self.var_names:
            raise NameError(f'Invalid variable name "{node.id}"')
        if not isinstance(node.ctx, ast.Load):
            raise ValueError('Only reading variables is supported!')

    def safe_visit(self, node: ast.AST) -> None:
        """These are safe, we don't care about them - just contents."""
        super().generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        """and, or, etc"""
        for val in node.values:
            self.visit(val)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        """Math operators, etc."""
        # Don't visit the operator.
        self.visit(node.left)
        self.visit(node.right)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> None:
        """-a, +a, not a, ~a."""
        self.visit(node.operand)

    def visit_Compare(self, node: ast.Compare) -> None:
        """ < comps etc."""
        try:
            ops = node.ops
        except AttributeError:
            ops = [node.op]  # type: ignore
        for op in ops:
            if isinstance(op, tuple(BANNED_COMPS)):
                raise Exception(f"The {BANNED_COMPS[type(op)]} operator is not allowed!")

        self.visit(node.left)
        for right in node.comparators:
            self.visit(right)

    visit_IfExp = safe_visit  # a if x else b

    # Objects
    visit_Slice = safe_visit  # allow  string[1:2]
    visit_Index = safe_visit  # allow vec['x']
    visit_Num = safe_visit
    visit_Str = safe_visit
    visit_NameConstant = safe_visit  # True, False, None
    visit_Constant = safe_visit


@conditions.make_result('Python', 'Operation')
def res_python_setup(res: Keyvalues) -> conditions.ResultCallable:
    """Apply a function to a fixup."""
    variables = {}
    variable_order = []
    code = None
    result_var = None
    for child in res:
        if child.name.startswith('$'):
            if child.value.casefold() not in FUNC_GLOBALS:
                raise Exception(f'Invalid variable type! ({child.value})')
            variables[child.name[1:]] = child.value.casefold()
            variable_order.append(child.name[1:])
        elif child.name == 'op':
            code = child.value
        elif child.name == 'resultvar':
            result_var = child.value
        else:
            raise Exception(f'Invalid key "{child.real_name}"')
    if not code:
        raise Exception('No operation specified!')
    if not result_var:
        raise Exception('No destination specified!')

    for name in variables:
        if name.startswith('_'):
            raise Exception(f'"{name}" is not permitted as a variable name!')

    # Allow $ in the variable names..
    code = code.replace('$', '')

    # Now process the code to convert it into a function taking variables
    # and returning them.
    # We also need to whitelist operations for security.
    expression = ast.parse(
        code,
        '<bee2_op>',
        mode='eval',
    ).body

    Checker(variable_order).visit(expression)

    # For each variable, do
    # var = func(_fixup['var'])
    statements: List[ast.AST] = [
        ast.Assign(
            targets=[ast.Name(id=var_name, ctx=ast.Store())],
            value=ast.Call(
                func=ast.Name(id=variables[var_name], ctx=ast.Load()),
                args=[
                    ast.Subscript(
                        value=ast.Name(id='_fixup', ctx=ast.Load()),
                        slice=ast.Index(value=ast.Str(s=var_name)),
                        ctx=ast.Load(),
                    ),
                ],
                keywords=[],
                starargs=None,
                kwargs=None,
            )
        )
        for var_name in variable_order
    ]
    # The last statement returns the target expression.
    statements.append(ast.Return(expression))

    args = ast.arguments(
        vararg=None, 
        kwonlyargs=[], 
        kw_defaults=[], 
        kwarg=None, 
        defaults=[],
        posonlyargs=[ast.arg('_fixup', None)],
        args=[]
    )

    func = ast.Module([
            ast.FunctionDef(
                name='_bee2_generated_func',
                args=args,
                body=statements,
                decorator_list=[],
            ),
        ],
        type_ignores=[],
    )

    # Fill in lineno and col_offset
    ast.fix_missing_locations(func)

    ns: Dict[str, Any] = {}
    eval(compile(func, '<bee2_op>', mode='exec'), FUNC_GLOBALS, ns)
    compiled_func = ns['_bee2_generated_func']
    compiled_func.__name__ = '<bee2_func>'

    def apply_operation(inst: Entity) -> None:
        result = compiled_func(inst.fixup)
        if isinstance(result, bool):
            result = int(result)
        inst.fixup[result_var] = str(result)
    return apply_operation
