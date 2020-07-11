from macros import macros, test_macro  # noqa: F401


@test_macro
class d(object):
    def __init__(self):
        super().__init__()
        print('d constructor')
        self.a = 1


print('Test for decorator')
a = d()
