from app.openf1.schemas import SessionResult


def test_classification_flags_become_an_outcome() -> None:
    assert SessionResult(driver_number=1).outcome is None
    assert SessionResult(driver_number=1, dnf=True).outcome == "DNF"
    assert SessionResult(driver_number=1, dns=True).outcome == "DNS"
    # A disqualified car may also be flagged as finishing; the DSQ is what matters
    assert SessionResult(driver_number=1, dnf=True, dsq=True).outcome == "DSQ"
