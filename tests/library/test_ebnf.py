import pytest
import json

from guidance import ebnf


@pytest.fixture(scope="module")
def azure_guidance_model(selected_model, selected_model_name):
    if selected_model_name in ["azure_guidance"]:
        return selected_model
    else:
        pytest.skip("Requires Azure Guidance model")


class TestJson:
    grammar_def = r"""
    value: dict
         | list
         | ESCAPED_STRING
         | SIGNED_NUMBER
         | "true" | "false" | "null"

    list : "[" [value ("," value)*] "]"

    dict : "{" [pair ("," pair)*] "}"
    pair : ESCAPED_STRING ":" value

    // Can't import common.ESCAPED_STRING because it uses a lookaround
    ESCAPED_STRING: /"(\\(["\\\/bfnrt]|u[a-fA-F0-9]{4})|[^"\\\x00-\x1F\x7F]+)*"/

    %import common.SIGNED_NUMBER
    %import common.WS
    %ignore WS

    """
    def test_dict(self, azure_guidance_model):
        capture_name = "json"
        grammar = ebnf(name=capture_name, grammar=self.grammar_def, start="dict")
        m = azure_guidance_model + "Here's a simple json object: " + grammar
        o = json.loads(m['json'])
        assert isinstance(o, dict)

    def test_array(self, azure_guidance_model):
        capture_name = "json"
        grammar = ebnf(name=capture_name, grammar=self.grammar_def, start="list")
        m = azure_guidance_model + "Here's a simple json object: " + grammar
        o = json.loads(m['json'])
        assert isinstance(o, list)