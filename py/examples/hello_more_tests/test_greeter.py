import unittest

from examples.hello_more_tests.greeter import Greeter


class TestGreeter(unittest.TestCase):
    def test_identity(self):
        self.assertIsInstance(Greeter("World"), Greeter)
