def has_letter(value: str) -> bool:
    """A descriptive name must contain at least one Unicode letter."""
    return isinstance(value, str) and any(character.isalpha() for character in value)


def has_only_letters_and_spaces(value: str) -> bool:
    """Accept names made of Unicode letters separated by spaces."""
    if not isinstance(value, str):
        return False
    normalized = value.strip()
    return bool(normalized) and all(character.isalpha() or character == " " for character in normalized) and has_letter(normalized)
