"""Code-owned writing requirements shared by quotes, prompt assist and execution.

The upstream supports custom strings, not a closed set of writing scenarios.
Legacy length/count are kept for immutable historical task snapshots.
"""

from collections.abc import Mapping

TEXT_STRING_PARAMETERS = frozenset({
    "copy_type", "platform", "audience", "tone", "language", "extra_instructions",
})
TEXT_PARAMETERS = TEXT_STRING_PARAMETERS | {"max_chars", "length", "count"}


def validate_text_parameters(parameters):
    if not isinstance(parameters, Mapping) or parameters.keys() - TEXT_PARAMETERS:
        raise ValueError("Unsupported text parameters")
    for key in TEXT_STRING_PARAMETERS & parameters.keys():
        if not isinstance(parameters[key], str):
            raise ValueError("Copy requirements must be strings")
    maximum = parameters.get("max_chars")
    if maximum is not None and (type(maximum) is not int or maximum < 1):
        raise ValueError("Maximum characters must be a positive integer")
    if type(parameters.get("count", 1)) is not int or parameters.get("count", 1) != 1:
        raise ValueError("Text generation returns one result")
    length = parameters.get("length")
    if length is not None and not (
        isinstance(length, str) or type(length) is int and length > 0
    ):
        raise ValueError("Invalid legacy text length")
