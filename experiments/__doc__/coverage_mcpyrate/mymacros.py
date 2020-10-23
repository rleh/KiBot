from ast import (Assign, Name, Attribute, Expr, Num, Str, NameConstant, copy_location, walk)
from mcpyrate.quotes import macros, q, u, n, a   # noqa: F401
from mcpyrate.astfixers import fix_locations
import mcpyrate  # noqa: F401


def document(tree, **kw):
    """ This macro takes literal strings and converts them into:
        _help_ID = type_hint+STRING
        where:
        ID is the first target of the last assignment.
        type_hint is the assigned type and default value (only works for a few types)
        STRING is the literal string """
    # Simplify it just to show the problem isn't related to the content of the macro
    # Note: This triggers another issue, Expr nodes can be optimized out if not assigned to a target
    # return tree
    for index in range(len(tree)):
        s = tree[index]
        if not index:
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
            if isinstance(target, Name):
                name = target.id
                is_attr = False
            elif isinstance(target, Attribute):
                name = target.attr
                is_attr = True
            # Create a _help_ID
            doc_id = '_help_'+name
            # Create the type hint for numbers, strings and booleans
            type_hint = ''
            if isinstance(value, Num):
                type_hint = '[number={}]'.format(value.n)
            elif isinstance(value, Str):
                type_hint = "[string='{}']".format(value.s)
            elif isinstance(value, NameConstant) and isinstance(value.value, bool):
                type_hint = '[boolean={}]'.format(str(value.value).lower())
            # Transform the string into an assign for _help_ID
            name = 'self.'+doc_id if is_attr else doc_id
            with q as quoted:
                n[name] = u[type_hint + s.value.s.rstrip()]
            tree[index] = quoted[0]
            fix_locations(tree[index], s, mode="overwrite")
        prev = s
    # Return the modified AST
    return tree
