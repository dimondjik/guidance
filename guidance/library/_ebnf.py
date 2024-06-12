from collections import defaultdict
from typing import Callable, Union

from lark import Lark
from lark.grammar import NonTerminal, Rule, Terminal

from .._grammar import GrammarFunction, Join
from .._guidance import guidance
from . import capture, regex, select


class EBNF:
    def __init__(self, grammar: str, start: str):
        self.start = start
        self.parser = Lark(grammar, start=start)  # kwds?

        # grammars for nonterminals -- regex seems to be the simplest solution
        self.terminal_grammars: dict[Terminal, GrammarFunction] = {
            Terminal(terminal.name): regex(pattern=terminal.pattern.to_regexp())
            for terminal in self.parser.terminals
        }

        # Collect rules by nonterminal such that we can easily `select` over
        # the corresponding grammars
        self.rules_by_nonterminal: dict[NonTerminal, list[Rule]] = defaultdict(list)
        for rule in self.parser.rules:
            self.rules_by_nonterminal[rule.origin].append(rule)

        # Callables to produce grammars for nonterminals
        # They need to be callables rather than literal grammars to avoid
        # infinite recursion (taking advantage of late binding)
        self.nonterminal_grammar_callables: dict[
            Terminal, Callable[[], GrammarFunction]
        ] = {}

    def build_term(self, term: Union[Terminal, NonTerminal]) -> GrammarFunction:
        if isinstance(term, Terminal):
            return self.terminal_grammars[term]
        if isinstance(term, NonTerminal):
            grammar_callable = self.nonterminal_grammar_callables.setdefault(
                term, self.build_nonterminal(term)
            )
            return grammar_callable()
        raise TypeError(
            f"term must be one of type Union[Terminal, NonTerminal], got {type(term)}"
        )

    def build_rule(self, rule: Rule) -> GrammarFunction:
        terms = [self.build_term(term) for term in rule.expansion]
        if len(terms) == 1 and rule.alias is None:
            # Unwrap unnamed singletons
            return terms[0]
        else:
            return Join(terms, name=rule.alias)

    def build_nonterminal(
        self, nonterminal: NonTerminal
    ) -> Callable[[], GrammarFunction]:
        # No-arg function to be wrapped in guidance decorator.
        #   - Associated with exactly one nonterminal
        #   - Needs to be no-arg to allow for mutual recursion via `Placeholder`s
        #   - Wrap in guidance decorator later so that we can set the __name__ first
        def inner(lm):
            # Options to select over (one for each rule associated with a nonterminal)
            options = [
                self.build_rule(rule) for rule in self.rules_by_nonterminal[nonterminal]
            ]
            return lm + select(options)

        # Set name and wrap
        inner.__name__ = nonterminal.name
        return guidance(inner, stateless=True, dedent=False, cache=True)

    def build(self) -> GrammarFunction:
        # Trigger recursive build of grammar using start nonterminal
        return self.build_term(NonTerminal(self.start))


@guidance(stateless=True)
def ebnf(lm, name=None, *, grammar: str, start: str):
    return lm + capture(EBNF(grammar, start).build(), name=name)