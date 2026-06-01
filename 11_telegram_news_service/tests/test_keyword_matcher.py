from app.services.keyword_matcher import match_keywords


KEYWORDS = [
    {"keyword": "Nvidia", "group_name": "반도체", "weight": 25, "alert_enabled": 1, "enabled": 1},
    {"keyword": "AI chip", "group_name": "반도체", "weight": 20, "alert_enabled": 1, "enabled": 1},
    {"keyword": "Redis", "group_name": "Database", "weight": 10, "alert_enabled": 0, "enabled": 0},
    {"keyword": "CPI", "group_name": "미국시장", "weight": 16, "alert_enabled": 1, "enabled": 1},
]


def test_case_insensitive_match():
    result = match_keywords("nvidia announces a new platform", KEYWORDS)
    assert result["local_keyword_score"] == 25
    assert result["matched_keywords"][0]["keyword"] == "Nvidia"


def test_multiple_keywords_score_once_each():
    result = match_keywords("Nvidia AI chip and another NVIDIA note", KEYWORDS)
    assert result["local_keyword_score"] == 45
    assert [item["keyword"] for item in result["matched_keywords"]] == ["Nvidia", "AI chip"]


def test_disabled_keyword_excluded():
    result = match_keywords("Redis releases new module", KEYWORDS)
    assert result["local_keyword_score"] == 0
    assert result["matched_keywords"] == []


def test_alert_enabled_flag():
    result = match_keywords("Latest CPI report", KEYWORDS)
    assert result["alert_keyword_matched"] is True


def test_short_keyword_uses_word_boundary():
    result = match_keywords("The word recipient should not match CPI", KEYWORDS)
    assert result["local_keyword_score"] == 16
