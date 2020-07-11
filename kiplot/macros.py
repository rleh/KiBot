from macropy.core import (parse_stmt)
from macropy.core.macros import Macros
from ast import (Assign, Name, Attribute, Expr, Num, Str, NameConstant, Load, Store, UnaryOp, USub, ClassDef)

macros = Macros()


@macros.block
def document(tree, **kw):
    """ This macro takes literal strings and converts them into:
        _help_ID = type_hint+STRING
        where:
        ID is the first target of the last assignment.
        type_hint is the assigned type and default value (only works for a few types)
        STRING is the literal string """
    for n in range(len(tree)):
        s = tree[n]
        if not n:
            prev = s
            continue
        # The whole sentence is a string?
        if (isinstance(s, Expr) and isinstance(s.value, Str) and
           # and the previous is an assign
           isinstance(prev, Assign)):  # noqa: E128
            # Apply it to the first target
            target = prev.targets[0]
            value = prev.value
            # Extract its name
            # variables and attributes are supported
            if isinstance(target, Name):  # pragma: no cover
                # Note: The support for variables isn't currently used
                name = target.id
                is_attr = False
            elif isinstance(target, Attribute):
                name = target.attr
                is_attr = True
            else:
                # Just in case we put anything other than an attr/var assignment
                continue  # pragma: no cover
            # Remove starting underscore
            if name[0] == '_':
                name = name[1:]
            # Create a _help_ID
            doc_id = '_help_'+name
            # Create the type hint for numbers, strings and booleans
            type_hint = ''
            if isinstance(value, Num):
                type_hint = '[number={}]'.format(value.n)
            elif isinstance(value, UnaryOp) and isinstance(value.operand, Num) and isinstance(value.op, USub):
                # -Num
                type_hint = '[number={}]'.format(-value.operand.n)
            elif isinstance(value, Str):
                type_hint = "[string='{}']".format(value.s)
            elif isinstance(value, NameConstant) and isinstance(value.value, bool):
                type_hint = '[boolean={}]'.format(str(value.value).lower())
            # Transform the string into an assign for _help_ID
            if is_attr:
                target = Attribute(value=Name(id='self', ctx=Load()), attr=doc_id, ctx=Store())
            else:  # pragma: no cover
                target = Name(id=doc_id, ctx=Store())
            tree[n] = Assign(targets=[target], value=Str(s=type_hint+s.value.s))
        prev = s
    # Return the modified AST
    return tree


def _do_wrap_class_register(tree, mod, base_class):
    if isinstance(tree, ClassDef):
        # Create the register call
        name = tree.name
        reg_name = name.lower()
        do_import = parse_stmt("from kiplot.{} import {}".format(mod, base_class))
        do_register = parse_stmt("{}.register('{}', {})".format(base_class, reg_name, name))
        return [tree, do_import, do_register]
    # Just in case somebody applies it to anything other than a class
    return tree  # pragma: no cover


@macros.decorator
def output_class(tree, **kw):
    """A decorator to wrap a class with:

       ... Class definition
       BaseOutput.register(CLASS_NAME_LOWER_STRING, CLASS_NAME)

       Allowing to register the class as an output. """
    return _do_wrap_class_register(tree, 'out_base', 'BaseOutput')


@macros.decorator
def pre_class(tree, **kw):
    """A decorator to wrap a class with:

       ... Class definition
       BasePreFlight.register(CLASS_NAME_LOWER_STRING, CLASS_NAME)

       Allowing to register the class as an output. """
    return _do_wrap_class_register(tree, 'pre_base', 'BasePreFlight')
