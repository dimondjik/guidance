import pytest
from unittest.mock import patch

from guidance import char_set, one_or_more, select, string, zero_or_more
from guidance._grammar import Byte, ByteRange, Select, Join
from guidance._parser import EarleyCommitParser


def test_one_or_more():
    g = one_or_more("a")
    parser = EarleyCommitParser(g)
    assert parser.valid_next_bytes() == set([Byte(b"a")])
    parser.consume_byte(b"a")
    assert parser.valid_next_bytes() == set([Byte(b"a")])


def test_zero_or_more_and_one_or_more():
    g = zero_or_more("a") + one_or_more("b")
    parser = EarleyCommitParser(g)
    assert parser.valid_next_bytes() == set([Byte(b"a"), Byte(b"b")])
    parser.consume_byte(b"a")
    assert parser.valid_next_bytes() == set([Byte(b"a"), Byte(b"b")])
    parser.consume_byte(b"b")
    assert parser.valid_next_bytes() == set([Byte(b"b")])

    parser = EarleyCommitParser(g)
    assert parser.valid_next_bytes() == set([Byte(b"a"), Byte(b"b")])
    parser.consume_byte(b"b")
    assert parser.valid_next_bytes() == set([Byte(b"b")])
    parser.consume_byte(b"b")
    assert parser.valid_next_bytes() == set([Byte(b"b")])


def test_zero_or_more_and_one_or_more_mixed():
    g = zero_or_more("a") + "test" + one_or_more("b")
    parser = EarleyCommitParser(g)
    assert parser.valid_next_bytes() == set([Byte(b"a"), Byte(b"t")])
    parser.consume_byte(b"t")
    parser.consume_byte(b"e")
    parser.consume_byte(b"s")
    assert parser.valid_next_bytes() == set([Byte(b"t")])
    parser.consume_byte(b"t")
    assert parser.valid_next_bytes() == set([Byte(b"b")])


def test_select():
    g = select(["bob", "bill", "sue"])
    parser = EarleyCommitParser(g)
    assert parser.valid_next_bytes() == set([Byte(b"b"), Byte(b"s")])
    parser.consume_byte(b"s")
    assert parser.valid_next_bytes() == set([Byte(b"u")])
    parser.consume_byte(b"u")
    assert parser.valid_next_bytes() == set([Byte(b"e")])


def test_select_nested():
    g = select(["bob", "bill", select(["mark", "mary"])])
    parser = EarleyCommitParser(g)
    assert parser.valid_next_bytes() == set([Byte(b"b"), Byte(b"m")])
    parser.consume_byte(b"m")
    assert parser.valid_next_bytes() == set([Byte(b"a")])
    parser.consume_byte(b"a")
    assert parser.valid_next_bytes() == set([Byte(b"r")])
    parser.consume_byte(b"r")
    assert parser.valid_next_bytes() == set([Byte(b"k"), Byte(b"y")])


def test_select_joined():
    g = select(["bob", "bill"]) + select(["mark", "mary"])
    parser = EarleyCommitParser(g)
    assert parser.valid_next_bytes() == set([Byte(b"b")])
    parser.consume_byte(b"b")
    assert parser.valid_next_bytes() == set([Byte(b"o"), Byte(b"i")])
    parser.consume_byte(b"i")
    assert parser.valid_next_bytes() == set([Byte(b"l")])
    parser.consume_byte(b"l")
    assert parser.valid_next_bytes() == set([Byte(b"l")])
    parser.consume_byte(b"l")
    assert parser.valid_next_bytes() == set([Byte(b"m")])
    parser.consume_byte(b"m")
    assert parser.valid_next_bytes() == set([Byte(b"a")])
    parser.consume_byte(b"a")
    assert parser.valid_next_bytes() == set([Byte(b"r")])
    parser.consume_byte(b"r")
    assert parser.valid_next_bytes() == set([Byte(b"k"), Byte(b"y")])


def test_char_set():
    g = char_set("b-f")
    parser = EarleyCommitParser(g)
    assert parser.valid_next_bytes() == set([ByteRange(b"bf")])
    parser.consume_byte(b"b")


def test_byte_mask_char_set():
    g = char_set("b-f")
    parser = EarleyCommitParser(g)
    m = parser.next_byte_mask()
    for i in range(256):
        if ord(b"b") <= i <= ord(b"f"):
            assert m[i]
        else:
            assert not m[i]


def test_byte_mask_char_set2():
    g = char_set("bf")
    parser = EarleyCommitParser(g)
    m = parser.next_byte_mask()
    for i in range(256):
        if i == ord(b"b") or i == ord(b"f"):
            assert m[i]
        else:
            assert not m[i]


def test_char_set_one_or_more():
    g = one_or_more(char_set("b-f"))
    parser = EarleyCommitParser(g)
    assert parser.valid_next_bytes() == set([ByteRange(b"bf")])
    parser.consume_byte(b"b")
    assert parser.valid_next_bytes() == set([ByteRange(b"bf")])
    parser.consume_byte(b"b")
    assert parser.valid_next_bytes() == set([ByteRange(b"bf")])
    parser.consume_byte(b"f")
    assert parser.valid_next_bytes() == set([ByteRange(b"bf")])


def test_string_utf8():
    b = bytes("¶", encoding="utf8")
    g = string("¶")
    parser = EarleyCommitParser(g)
    assert parser.valid_next_bytes() == set([Byte(b[:1])])
    parser.consume_byte(b[:1])
    assert parser.valid_next_bytes() == set([Byte(b[1:])])
    parser.consume_byte(b[1:])


class TestRecursiveNullableGrammars:
    """
    Computing parse tree of recursive nullable grammars will cause an infinite
    loop if not handled correctly
    """

    @pytest.mark.timeout(5)
    def test_no_infinite_loop(self):
        """
        A -> A
        A ->

        Loop occurs because `A -> A` is a nullable rule
        """
        # Note that we get a different grammar if we made `A = select([''], recurse=True)`
        A = Select([], recursive=True)
        A.values = [A, ""]
        parser = EarleyCommitParser(A)
        # Test that computing the parse tree doesn't hang
        parser.parse_tree()

    @pytest.mark.timeout(5)
    def test_no_infinite_loop_with_terminal(self):
        """
        A -> A B
        A ->
        B -> 'x'
        B ->

        Loop occurs because `A -> A B` is a nullable rule
        """
        B = select(["x", ""])
        A = select([B, ""], recurse=True)
        parser = EarleyCommitParser(A)
        # Test that computing the parse tree doesn't hang
        parser.parse_tree()

    @pytest.mark.timeout(5)
    def test_no_infinite_loop_extra_indirection(self):
        """
        A -> A C
        A -> B
        A ->
        B -> A
        C -> 'x'

        Loop occurs because `A -> B`, `B -> A` are nullable rules
        """
        C = Join(["x"])
        # Initialize as nullable -- quirk in how nullability is determined in Select
        B = Select([""])
        # Initialize as nullable -- quirk in how nullability is determined in Select
        A = Select([""])
        B.values = [A]
        A.values = [A + C, B, ""]
        assert A.nullable
        assert B.nullable
        parser = EarleyCommitParser(A)
        # Test that computing the parse tree doesn't hang
        parser.parse_tree()

    @pytest.mark.timeout(5)
    def test_captures_from_root(self):
        B = select(["x", "y", ""], name="B")
        A = select([B, ""], recurse=True, name="A")
        parser = EarleyCommitParser(A)

        with patch.object(
            parser,
            "_record_captures_from_root",
            wraps=parser._record_captures_from_root,
        ) as mock:
            parser.consume_byte(b"x")
            captures, _ = parser.get_captures()
            assert mock.call_count == 1
            assert captures == {"B": b"x", "A": b"x"}

            parser.consume_byte(b"y")
            captures, _ = parser.get_captures()
            assert mock.call_count == 2
            assert captures == {"B": b"y", "A": b"xy"}

            parser.consume_byte(b"x")
            captures, _ = parser.get_captures()
            assert mock.call_count == 3
            assert captures == {"B": b"x", "A": b"xyx"}

    @pytest.mark.timeout(5)
    def test_partial_captures(self):
        B = select(["x", "y", ""], name="B")
        A = select([B, ""], recurse=True, name="A")
        C = A + "z"
        parser = EarleyCommitParser(C)

        with patch.object(
            parser,
            "_record_captures_partial",
            wraps=parser._record_captures_partial,
        ) as mock:
            parser.consume_byte(b"x")
            captures, _ = parser.get_captures()
            assert mock.call_count == 1
            assert captures == {"B": b"", "A": b"x"}

            parser.consume_byte(b"y")
            captures, _ = parser.get_captures()
            assert mock.call_count == 2
            assert captures == {"B": b"", "A": b"xy"}

            # No new call to _record_captures_partial, but make sure that the captures are updated
            # when finally called from root
            parser.consume_byte(b"z")
            captures, _ = parser.get_captures()
            assert mock.call_count == 2  # no new call
            assert captures == {"B": b"y", "A": b"xy"}
