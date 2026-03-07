from deliberation.api.app import routes


def test_normalize_vote_choice():
    assert routes._normalize_vote_choice("agree") == 1
    assert routes._normalize_vote_choice("disagree") == -1
    assert routes._normalize_vote_choice("pass") == 0
    assert routes._normalize_vote_choice("unknown") is None


def test_normalize_optional_bool():
    assert routes._normalize_optional_bool("true") is True
    assert routes._normalize_optional_bool("0") is False
    assert routes._normalize_optional_bool("invalid") is None


def test_normalize_optional_timestamp():
    assert routes._normalize_optional_timestamp("2024-01-01T10:00:00Z") == "2024-01-01T10:00:00+00:00"
    assert routes._normalize_optional_timestamp("2024-01-01T10:00:00+02:00") == "2024-01-01T10:00:00+02:00"
    assert routes._normalize_optional_timestamp("not-a-date") is None
