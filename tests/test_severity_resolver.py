import pytest

from src.data_pipeline.severity_resolver import resolve_severity


def test_empty_reports_returns_zero():
    assert resolve_severity([]) == 0


def test_average_of_integers():
    assert resolve_severity([1, 3, 5]) == 3


def test_average_of_floats():
    assert resolve_severity([2.2, 3.8]) == 3


def test_single_value():
    assert resolve_severity([7]) == 7


if __name__ == "__main__":
    pytest.main([__file__])
