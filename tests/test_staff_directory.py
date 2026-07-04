import logging

from duty_bot.staff_directory import load_staff_directory, resolve_mention


def test_loads_directory_from_yaml(tmp_path):
    path = tmp_path / "staff_directory.yml"
    path.write_text('staff:\n  "Simran Kaur": "<@U234567890>"\n')
    directory = load_staff_directory(path)
    assert directory == {"Simran Kaur": "<@U234567890>"}


def test_missing_directory_file_gives_empty_mapping(tmp_path):
    assert load_staff_directory(tmp_path / "nope.yml") == {}


def test_resolves_known_name_to_mention():
    directory = {"Simran Kaur": "<@U234567890>"}
    assert resolve_mention(directory, "Simran Kaur") == "<@U234567890>"


def test_unknown_name_falls_back_to_raw_name_with_warning(caplog):
    with caplog.at_level(logging.WARNING):
        assert resolve_mention({}, "Mystery Person") == "Mystery Person"
    assert "Mystery Person" in caplog.text
