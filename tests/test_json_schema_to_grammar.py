import json

import pytest
from jsonschema import validate, ValidationError

from guidance import models
from guidance._grammar import GrammarFunction
from guidance._json_schema_to_grammar import json_schema_to_grammar
from guidance._parser import ParserException


def to_compact_json(target: any) -> str:
    # See 'Compact Encoding':
    # https://docs.python.org/3/library/json.html
    # Since this is ultimately about the generated
    # output, we don't need to worry about pretty printing
    # and whitespace
    return json.dumps(target, separators=(",", ":"))


def check_string_with_grammar(input_string: str, grammar: GrammarFunction):
    print(f"Checking {input_string}")
    matches = grammar.match(input_string.encode(), raise_exceptions=True)
    assert matches.partial == False


@pytest.mark.parametrize(
    "simple_json_string",
    [
        to_compact_json(x)
        for x in [
            "with_underscore",
            "ALLCAPS",
            "with a space",
            "MiXeD cAsInG",
            "with-hyphen",
            "Mix case_underscore-hyphens",
            "with a comma, in the string",
            "A full stop.",
            """How about
            a
            multiline string?""",
            "A \t tab \t between \t words",
            r"End with backslash \ ",
            "Have a forward / slash",
            "Include [the] odd {brace} and (parentheses)",
            "Some more symbols: ; are useful!",
        ]
    ],
)
def test_string_schema(simple_json_string):
    schema = """{ "type": "string" }"""

    # First sanity check what we're setting up
    schema_obj = json.loads(schema)
    validate(instance=simple_json_string, schema=schema_obj)

    # Now set up the actual conversion
    grammar = json_schema_to_grammar(schema)
    check_string_with_grammar(simple_json_string, grammar)


@pytest.mark.parametrize(
    "json_int",
    [to_compact_json(x) for x in [0, 1, 100, 9876543210, 99, 737, 858, -1, -10, -20]],
)
def test_integer_schema(json_int):
    schema = """{ "type": "integer" }"""

    # First sanity check what we're setting up
    schema_obj = json.loads(schema)
    validate(instance=json.loads(json_int), schema=schema_obj)

    # Now set up the actual conversion
    grammar = json_schema_to_grammar(schema)
    check_string_with_grammar(json_int, grammar)


@pytest.mark.parametrize(
    ["bad_obj", "fail_byte"],
    [
        (0.1, b"."),
        ("some string", b'"'),
        (dict(a=1), b"{"),
        ([], b"["),
        ([1], b"["),
        (["si tacuisses, philosophus mansisses"], b"["),
    ],
)
def test_integer_schema_invalid(bad_obj, fail_byte):
    schema = """{ "type": "integer" }"""
    grammar = json_schema_to_grammar(schema)

    bad_string = to_compact_json(bad_obj)
    with pytest.raises(ParserException) as pe:
        _ = grammar.match(bad_string.encode(), raise_exceptions=True)
    assert pe.value.current_byte == fail_byte


def test_simple_object():
    schema = """{
        "type": "object",
        "properties": {
            "name" : {
                "type": "string"
            },
            "productId": {
                "description": "The unique identifier for a product",
                "type": "integer"
            }
        }
    }
"""
    target_obj = dict(name="my product", productId=123)

    # First sanity check what we're setting up
    schema_obj = json.loads(schema)
    validate(instance=target_obj, schema=schema_obj)

    grammar = json_schema_to_grammar(schema)

    target_string = to_compact_json(target_obj)
    check_string_with_grammar(target_string, grammar)


@pytest.mark.parametrize(
    ["bad_obj", "fail_byte"],
    [
        (0, b"0"),
        (1.1, b"1"),
        ("some string", b'"'),
        (dict(a=1), b"a"),
        ([], b"["),
        ([1], b"["),
        (["Per ardua ad astra"], b"["),
    ],
)
def test_simple_object_bad_input(bad_obj, fail_byte):
    schema = """{
        "type": "object",
        "properties": {
            "name" : {
                "type": "string"
            },
            "productId": {
                "description": "The unique identifier for a product",
                "type": "integer"
            }
        }
    }
"""
    grammar = json_schema_to_grammar(schema)

    bad_string = to_compact_json(bad_obj)
    with pytest.raises(ParserException) as pe:
        _ = grammar.match(bad_string.encode(), raise_exceptions=True)
    assert pe.value.current_byte == fail_byte


def test_nested_object():
    schema = """{
        "type": "object",
        "properties": {
            "name" : {
                "type": "string"
            },
            "info": {
                "type": "object",
                "properties" : {
                    "a" : {
                        "type" : "integer"
                    },
                    "b" : {
                        "type" : "integer"
                    }
                }
            }
        }
    }
"""
    target_obj = dict(name="my product", info=dict(a=1, b=2))

    # First sanity check what we're setting up
    schema_obj = json.loads(schema)
    validate(instance=target_obj, schema=schema_obj)

    grammar = json_schema_to_grammar(schema)

    target_string = to_compact_json(target_obj)
    check_string_with_grammar(target_string, grammar)


@pytest.mark.parametrize("target_list", [[], [0], [34, 56], [1, 2, 3], [9, 8, 7, 6]])
def test_integer_list(target_list):
    schema = """{
    "type" : "array",
    "items" : {
            "type" : "integer"
        }
    }
"""

    # First sanity check what we're setting up
    schema_obj = json.loads(schema)
    validate(instance=target_list, schema=schema_obj)

    grammar = json_schema_to_grammar(schema)

    target_string = to_compact_json(target_list)
    check_string_with_grammar(target_string, grammar)


@pytest.mark.parametrize("target_list", [[], ["a"], ["b c", "d, e"]])
def test_string_list(target_list):
    schema = """{
    "type" : "array",
    "items" : {
            "type" : "string"
        }
    }
"""

    # First sanity check what we're setting up
    schema_obj = json.loads(schema)
    validate(instance=target_list, schema=schema_obj)

    grammar = json_schema_to_grammar(schema)

    target_string = to_compact_json(target_list)
    check_string_with_grammar(target_string, grammar)


@pytest.mark.parametrize(
    "target_list",
    [[], [dict(a=1)], [dict(a=2), dict(a=3)], [dict(a=4), dict(a=5), dict(a=6)]],
)
def test_object_list(target_list):
    schema = """{
    "type" : "array",
    "items" : {
            "type" : "object",
            "properties" : {
                "a" : {
                    "type": "integer"
                }
            }
        }
    }
"""

    # First sanity check what we're setting up
    schema_obj = json.loads(schema)
    validate(instance=target_list, schema=schema_obj)

    grammar = json_schema_to_grammar(schema)

    target_string = to_compact_json(target_list)
    check_string_with_grammar(target_string, grammar)


def test_object_containing_list():
    schema = """{
    "type": "object",
    "properties" : {
            "a" : { "type" : "string" },
            "b list" : {
                "type": "array",
                "items" : {"type": "integer" }
            }
        }
    }
"""

    target_obj = {
        "a": "some lengthy string of characters",
        "b list": [1, 2, 3, 2312, 123],
    }

    # First sanity check what we're setting up
    schema_obj = json.loads(schema)
    validate(instance=target_obj, schema=schema_obj)

    grammar = json_schema_to_grammar(schema)

    target_string = to_compact_json(target_obj)
    check_string_with_grammar(target_string, grammar)


@pytest.mark.parametrize(
    ["bad_list", "unexpected_char"],
    [
        ("[,]", b","),
        ("[,1]", b","),
        ("[1,]", b"]"),
        ("[1,2,]", b"]"),
        ("[0,1,2,3,]", b"]"),
        ("[0,,1]", b","),
        ("[0,1,,,1,2]", b","),
        ("[0,1.2]", b"."),
    ],
)
def test_bad_int_list(bad_list: str, unexpected_char):
    schema = """{
    "type" : "array",
    "items" : {
            "type" : "integer"
        }
    }
"""

    # First sanity check what we're setting up
    schema_obj = json.loads(schema)
    validate(instance=[1, 2, 3], schema=schema_obj)

    grammar = json_schema_to_grammar(schema)
    with pytest.raises(ParserException) as pe:
        _ = grammar.match(bad_list.encode(), raise_exceptions=True)
    assert pe.value.current_byte == unexpected_char


@pytest.mark.parametrize("target_bool", [True, False])
def test_boolean(target_bool):
    schema = """{"type": "boolean" }"""

    # First sanity check what we're setting up
    schema_obj = json.loads(schema)
    validate(instance=target_bool, schema=schema_obj)

    grammar = json_schema_to_grammar(schema)

    target_string = to_compact_json(target_bool)
    check_string_with_grammar(target_string, grammar)


@pytest.mark.parametrize(
    "target_number",
    # It appears that Inf and NaN are not actually part of the JSON spec
    [0, 1, -1, 134, -234762, 0.1, 1.0, -10.33, 452.342, 1.23e23, -1.2e-22],
)
def test_number(target_number):
    schema = """{"type": "number" }"""

    # First sanity check what we're setting up
    schema_obj = json.loads(schema)
    validate(instance=target_number, schema=schema_obj)

    grammar = json_schema_to_grammar(schema)

    target_string = to_compact_json(target_number)
    check_string_with_grammar(target_string, grammar)


@pytest.mark.parametrize(
    ["bad_obj", "fail_byte"],
    [
        ("hic sunt dracones", b'"'),
        (dict(a=1), b"{"),
        ([], b"["),
        ([1], b"["),
        (["Gallia est omnis divisa in partes tres"], b"["),
    ],
)
def test_number_schema_invalid(bad_obj, fail_byte):
    schema = """{ "type": "number" }"""
    grammar = json_schema_to_grammar(schema)

    bad_string = to_compact_json(bad_obj)
    with pytest.raises(ParserException) as pe:
        _ = grammar.match(bad_string.encode(), raise_exceptions=True)
    assert pe.value.current_byte == fail_byte


def test_null():
    schema = """{"type": "null" }"""

    target_obj = None

    # First sanity check what we're setting up
    schema_obj = json.loads(schema)
    validate(instance=target_obj, schema=schema_obj)

    grammar = json_schema_to_grammar(schema)

    target_string = to_compact_json(target_obj)
    check_string_with_grammar(target_string, grammar)


@pytest.mark.parametrize(
    "target_obj",
    [
        dict(all_cats=[]),
        dict(all_cats=[dict(name="Kasha")]),
        dict(all_cats=[dict(name="Dawon"), dict(name="Barong")]),
    ],
)
def test_simple_ref(target_obj):
    schema = """{
  "$defs": {
    "Cat": {
      "properties": {
        "name": {
          "title": "Name",
          "type": "string"
        }
      },
      "required": [
        "name"
      ],
      "title": "Cat",
      "type": "object"
    }
  },
  "properties": {
    "all_cats": {
      "items": {
        "$ref": "#/$defs/Cat"
      },
      "title": "All Cats",
      "type": "array"
    }
  },
  "required": [
    "all_cats"
  ],
  "title": "CatList",
  "type": "object"
}
"""
    # First sanity check what we're setting up
    schema_obj = json.loads(schema)
    validate(instance=target_obj, schema=schema_obj)

    grammar = json_schema_to_grammar(schema)

    target_string = to_compact_json(target_obj)
    check_string_with_grammar(target_string, grammar)


def test_nested_ref():
    schema = """{
  "$defs": {
    "A": {
      "properties": {
        "name": {
          "title": "Name",
          "type": "string"
        }
      },
      "required": [
        "name"
      ],
      "title": "A",
      "type": "object"
    },
    "B": {
      "properties": {
        "other_str": {
          "title": "Other Str",
          "type": "string"
        },
        "my_A": {
          "$ref": "#/$defs/A"
        }
      },
      "required": [
        "other_str",
        "my_A"
      ],
      "title": "B",
      "type": "object"
    }
  },
  "properties": {
    "my_B": {
      "$ref": "#/$defs/B"
    }
  },
  "required": [
    "my_B"
  ],
  "title": "C",
  "type": "object"
}
    """

    target_obj = dict(my_B=dict(other_str="some string", my_A=dict(name="my name")))

    # First sanity check what we're setting up
    schema_obj = json.loads(schema)
    validate(instance=target_obj, schema=schema_obj)

    grammar = json_schema_to_grammar(schema)

    target_string = to_compact_json(target_obj)
    check_string_with_grammar(target_string, grammar)


@pytest.mark.parametrize("target_obj", [123, True])
def test_anyOf_simple(target_obj):
    schema = """{
    "anyOf": [
                {
                    "type": "integer"
                },
                {
                    "type": "boolean"
                }
            ]
}
"""
    # First sanity check what we're setting up
    schema_obj = json.loads(schema)
    validate(instance=target_obj, schema=schema_obj)

    grammar = json_schema_to_grammar(schema)

    target_string = to_compact_json(target_obj)
    check_string_with_grammar(target_string, grammar)


@pytest.mark.parametrize(
    "target_obj",
    [
        dict(my_val=dict(my_int=1)),
        dict(my_val=dict(my_str="Some long string or other")),
    ],
)
def test_anyOf_objects(target_obj):
    schema = """{
  "$defs": {
    "A": {
      "properties": {
        "my_str": {
          "default": "me",
          "title": "My Str",
          "type": "string"
        }
      },
      "title": "A",
      "type": "object"
    },
    "B": {
      "properties": {
        "my_int": {
          "default": 1,
          "title": "My Int",
          "type": "integer"
        }
      },
      "title": "B",
      "type": "object"
    }
  },
  "properties": {
    "my_val": {
      "anyOf": [
        {
          "$ref": "#/$defs/A"
        },
        {
          "$ref": "#/$defs/B"
        }
      ],
      "title": "My Val"
    }
  },
  "title": "C",
  "type": "object"
}
"""
    # First sanity check what we're setting up
    schema_obj = json.loads(schema)
    validate(instance=target_obj, schema=schema_obj)

    grammar = json_schema_to_grammar(schema)

    target_string = to_compact_json(target_obj)
    check_string_with_grammar(target_string, grammar)

@pytest.mark.parametrize("target_obj", [{}, {'a': 1}, {'a':1, 'b':2}])
def test_simple_additional_properties(target_obj):
    schema = """{
    "type": "object",
    "additionalProperties": {
            "type" : "integer"
        }
    }
"""
    # First sanity check what we're setting up
    schema_obj = json.loads(schema)
    validate(instance=target_obj, schema=schema_obj)

    grammar = json_schema_to_grammar(schema)

    target_string = to_compact_json(target_obj)
    check_string_with_grammar(target_string, grammar)

@pytest.mark.parametrize("target_obj", [{}, {'a': 1}, {'a': '2'}, {'a':1, 'b':'2'}])
def test_anyOf_additional_properties(target_obj):
    schema = """{
    "type": "object",
    "additionalProperties": {
            "anyOf": [
                {"type" : "string"},
                {"type": "integer"}
            ]
        }
    }
"""
    # First sanity check what we're setting up
    schema_obj = json.loads(schema)
    validate(instance=target_obj, schema=schema_obj)

    grammar = json_schema_to_grammar(schema)

    target_string = to_compact_json(target_obj)
    check_string_with_grammar(target_string, grammar)

@pytest.mark.parametrize("target_obj", [{'mystr': 'hello'}, {'mystr': 'hello', 'a': 1}, {'mystr': 'hello', 'a':1, 'b':2}])
def test_properties_and_additional_properties(target_obj):
    schema = """{
    "type": "object",
    "properties": {
        "mystr": {"type": "string"}
    },
    "additionalProperties": {
        "type": "integer"
    }
}
"""
    # First sanity check what we're setting up
    schema_obj = json.loads(schema)
    validate(instance=target_obj, schema=schema_obj)

    grammar = json_schema_to_grammar(schema)

    target_string = to_compact_json(target_obj)
    check_string_with_grammar(target_string, grammar)

@pytest.mark.parametrize("target_obj", [1,"2",3])
def test_enum(target_obj):
    schema = """{
    "enum": [1,"2",3]
}
"""
    # First sanity check what we're setting up
    schema_obj = json.loads(schema)
    validate(instance=target_obj, schema=schema_obj)

    grammar = json_schema_to_grammar(schema)

    target_string = to_compact_json(target_obj)
    check_string_with_grammar(target_string, grammar)

@pytest.mark.parametrize("target_obj", [4, '5', True])
def test_enum_negative_examples(target_obj):
    schema = """{
    "enum": [1,"2",3]
}
"""
    # First sanity check what we're setting up
    schema_obj = json.loads(schema)
    with pytest.raises(ValidationError):
        validate(instance=target_obj, schema=schema_obj)

    grammar = json_schema_to_grammar(schema)

    target_string = to_compact_json(target_obj)
    with pytest.raises(ParserException):
        check_string_with_grammar(target_string, grammar)

def test_with_mock_model():
    schema = """{
    "type": "object",
    "properties" : {
            "a" : { "type" : "string" },
            "b_list" : {
                "type": "array",
                "items" : {"type": "integer" }
            }
        }
    }
"""
    sample_obj = dict(
        a="a.\nlong string containing many\tthings! Because it's good to have variety",
        b_list=[0, -1, 20, -2313, 98012478623],
    )

    # First sanity check what we're setting up
    schema_obj = json.loads(schema)
    validate(instance=sample_obj, schema=schema_obj)

    prepared_string = f"<s>{to_compact_json(sample_obj)}"
    lm = models.Mock(prepared_string.encode())

    # Run with the mock model
    lm += json_schema_to_grammar(schema)

    # Make sure the round trip works
    loaded_obj = json.loads(str(lm))
    assert sample_obj == loaded_obj
