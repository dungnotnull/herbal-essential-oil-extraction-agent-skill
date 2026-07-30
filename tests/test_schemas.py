import unittest
from tests._bootstrap import ROOT  # noqa: F401
from herbal_oil.core.schemas import validate, is_valid, load_schema
from herbal_oil.core.errors import SchemaValidationError


class TestSchemas(unittest.TestCase):
    def test_valid_instance(self):
        schema = load_schema(ROOT / "assets" / "schemas" / "requirements.schema.json")
        ok = {"object": "lavender oil", "analysis_type": "combined", "language": "en"}
        validate(ok, schema)  # no raise

    def test_missing_required(self):
        schema = load_schema(ROOT / "assets" / "schemas" / "requirements.schema.json")
        with self.assertRaises(SchemaValidationError):
            validate({"object": "x"}, schema)

    def test_enum_violation(self):
        schema = {"type": "object", "properties": {"x": {"type": "string", "enum": ["a", "b"]}}}
        with self.assertRaises(SchemaValidationError):
            validate({"x": "c"}, schema)

    def test_nested_array_items(self):
        schema = {"type": "array", "items": {"type": "integer", "minimum": 0}}
        validate([0, 1, 2], schema)
        with self.assertRaises(SchemaValidationError):
            validate([0, -1, 2], schema)

    def test_is_valid(self):
        self.assertTrue(is_valid({"x": 1}, {"type": "object", "required": ["x"]}))
        self.assertFalse(is_valid({}, {"type": "object", "required": ["x"]}))


if __name__ == "__main__":
    unittest.main()