import pytest
from src.data_pipeline.nlp_filter import load_social_data, filter_relevant_reports


def test_load_social_data_returns_list():
    result = load_social_data("data/raw/crowdsourced/test.json")
    assert isinstance(result, list)


def test_filter_relevant_reports_empty():
    result = filter_relevant_reports([])
    assert result == []


def test_filter_relevant_reports_with_keywords():
    reports = [
        {"text": "flood in the city", "id": 1},
        {"text": "weather is nice", "id": 2},
    ]
    result = filter_relevant_reports(reports, keywords=["flood"])
    assert isinstance(result, list)


def test_filter_relevant_reports_default_keywords():
    reports = [
        {"text": "earthquake detected", "id": 1},
        {"text": "morning coffee", "id": 2},
    ]
    result = filter_relevant_reports(reports)
    assert isinstance(result, list)


if __name__ == "__main__":
    pytest.main([__file__])
