import asyncio
import unittest
from unittest.mock import Mock, AsyncMock, patch
from mud_client import MUDClient, Trigger, Variable


class TestANSIParsing(unittest.TestCase):
    def setUp(self):
        self.client = MUDClient()

    def test_strip_ansi(self):
        text = "\x1b[31mHello\x1b[0m World"
        result = self.client.strip_ansi(text)
        self.assertEqual(result, "Hello World")

    def test_strip_ansi_complex(self):
        text = "\x1b[1;31mRed\x1b[0m \x1b[32mGreen\x1b[0m"
        result = self.client.strip_ansi(text)
        self.assertEqual(result, "Red Green")

    def test_parse_ansi(self):
        text = "\x1b[31mRed\x1b[0m"
        result = self.client.parse_ansi(text)
        self.assertEqual(result["plain"], "Red")
        self.assertIsInstance(result["segments"], list)

    def test_parse_ansi_no_codes(self):
        text = "Plain text"
        result = self.client.parse_ansi(text)
        self.assertEqual(result["plain"], "Plain text")
        self.assertEqual(result["raw"], "Plain text")


class TestTriggers(unittest.TestCase):
    def setUp(self):
        self.client = MUDClient()
        self.trigger_called = False
        self.trigger_text = None

    def trigger_callback(self, text):
        self.trigger_called = True
        self.trigger_text = text

    def test_add_trigger(self):
        self.client.add_trigger(r"hello", self.trigger_callback)
        self.assertEqual(len(self.client.triggers), 1)

    def test_remove_trigger(self):
        self.client.add_trigger(r"hello", self.trigger_callback)
        self.client.remove_trigger(r"hello")
        self.assertEqual(len(self.client.triggers), 0)

    def test_trigger_fires(self):
        self.client.add_trigger(r"test", self.trigger_callback)
        self.client.check_triggers("This is a test line")
        self.assertTrue(self.trigger_called)
        self.assertEqual(self.trigger_text, "This is a test line")

    def test_trigger_not_fires(self):
        self.client.add_trigger(r"hello", self.trigger_callback)
        self.client.check_triggers("This is a test line")
        self.assertFalse(self.trigger_called)


class TestVariables(unittest.TestCase):
    def setUp(self):
        self.client = MUDClient()

    def test_set_variable(self):
        self.client.set_variable("health", 100)
        result = self.client.get_variable("health")
        self.assertEqual(result, 100)

    def test_get_nonexistent_variable(self):
        result = self.client.get_variable("nonexistent")
        self.assertIsNone(result)

    def test_set_variable_different_types(self):
        self.client.set_variable("name", "Player", "string")
        self.client.set_variable("level", 5, "int")
        self.client.set_variable("alive", True, "bool")

        self.assertEqual(self.client.get_variable("name"), "Player")
        self.assertEqual(self.client.get_variable("level"), 5)
        self.assertTrue(self.client.get_variable("alive"))


if __name__ == "__main__":
    unittest.main()
