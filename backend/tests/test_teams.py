from app.teams import seasons, team_key


def test_renamed_teams_share_one_key() -> None:
    assert team_key("RB") == team_key("Racing Bulls") == "racing-bulls"
    assert team_key("Kick Sauber") == team_key("Audi") == "audi"


def test_unknown_teams_get_a_slug() -> None:
    assert team_key("Andretti Global") == "andretti-global"


def test_lineage_lists_each_season_name() -> None:
    assert seasons("racing-bulls")[2024] == "RB"
    assert 2023 not in seasons("racing-bulls")
    assert seasons("audi")[2024] == "Kick Sauber"
    assert seasons("nope") == {}
