import pytest

from app.extras import _mean_angle, _zones


def test_drs_zones_are_runs_of_open_flap() -> None:
    flags = [False] * 3 + [True] * 5 + [False] * 4 + [True] * 6 + [False] * 2
    assert _zones(flags) == [(3, 7), (12, 17)]


def test_zone_crossing_the_line_is_joined() -> None:
    flags = [True] * 4 + [False] * 10 + [True] * 5
    assert _zones(flags) == [(14, 3)]


def test_telemetry_blips_are_ignored() -> None:
    flags = [False] * 5 + [True, True] + [False] * 5
    assert _zones(flags) == []


def test_wind_direction_averages_across_north() -> None:
    assert _mean_angle([350.0, 10.0]) == pytest.approx(0.0, abs=0.5)
    assert _mean_angle([]) is None


def test_sensor_dropouts_are_not_readings() -> None:
    from app.extras import _reading

    assert _reading(0.0) is None
    assert _reading(None) is None
    assert _reading(41.5) == 41.5
