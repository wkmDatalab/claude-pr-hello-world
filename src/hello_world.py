"""Case 1: a file with a clear defect (its test fails).

The agent should find two problems and propose the smallest fix:
1. The greeting text is wrong: "H world" should be "Hello world".
2. Python has print(...), not printf(...).
"""


def greeting() -> str:
    """Return the greeting that should be printed by the app."""
    return "He world"


def main() -> None:
    """Print the greeting."""
    printf(greeting())


if __name__ == "__main__":
    main()
