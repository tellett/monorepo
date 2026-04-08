class Greeter:
    def name():
        doc = """Name of the person to greet."""

        def fget(self):
            return self._name

        def fset(self, value):
            self._name = value

        def fdel(self):
            del self._name

        return locals()

    name = property(**name())

    def __init__(self, name):
        self._name = name

    def Greet(self):
        return f"Hello {self.name}"
