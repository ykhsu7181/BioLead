from literature_agent.main import INITIALIZATION_MESSAGE, main


def test_main_prints_initialization_message(capsys) -> None:
    main()

    captured = capsys.readouterr()

    assert captured.out == f"{INITIALIZATION_MESSAGE}\n"
    assert captured.err == ""
