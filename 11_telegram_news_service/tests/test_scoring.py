from app.services.scoring import calculate_final_score


def test_final_score_without_ai():
    result = calculate_final_score(local_keyword_score=25, source_name="GDELT", title="Valid market title")
    assert result.final_score == 30


def test_final_score_with_ai():
    result = calculate_final_score(local_keyword_score=25, ai_score=80, source_name="GDELT", title="Valid AI title")
    assert result.final_score == 70


def test_max_100_clamp():
    result = calculate_final_score(local_keyword_score=90, ai_score=100, source_name="SEC EDGAR", source_type="sec", title="Major filing")
    assert result.final_score == 100


def test_duplicate_penalty():
    result = calculate_final_score(local_keyword_score=50, duplicate_suspected=True, title="Valid title")
    assert result.final_score == 30
