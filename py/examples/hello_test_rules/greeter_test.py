import unittest

from examples.hello_test_rules.greeter import Greeter


class TestGreeter(unittest.TestCase):
    def test_identity(self):
        self.assertIsInstance(Greeter("World"), Greeter)
