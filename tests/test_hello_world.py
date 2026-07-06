from src.hello_world import greeting, main


def test_greeting_text_is_exact() -> None:
    assert greeting() == "Hello world"


def test_main_prints_hello_world(capsys) -> None:
    main()
    captured = capsys.readouterr()
    assert captured.out == "Hello world\n"
