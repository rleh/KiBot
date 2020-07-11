from macropy.core import parse_stmt
from macropy.core.macros import Macros
from ast import ClassDef

macros = Macros()


@macros.decorator
def test_macro(tree, **kw):
    print(tree)
    if isinstance(tree, ClassDef) and len(tree.bases) == 1:
        pre = parse_stmt("from base_class import BaseClass")
        tree.bases[0].id = 'BaseClass'
        post = parse_stmt("print('Hola')")
        return [pre, tree, post]
    return tree
