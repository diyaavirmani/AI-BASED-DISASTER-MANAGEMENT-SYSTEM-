"""
Determines the final severity score for a disaster 
report by checking multiple sources in priortiy 



This module contains helper routines used by the
pipeline to merge external severity estimates and
produce a canonical integer score.
"""

import logging


from typing import Iterable


def resolve_severity(reports: Iterable[float]) -> int:
    """Compute a combined severity score from multiple input reports.

    The algorithm currently averages the provided values and returns the
    nearest integer.  Passing an empty iterator results in a score of 0.

    Parameters
    ----------
    reports : Iterable[float]
        Numeric severity values obtained from external sources.

    Returns
    -------
    int
        Rounded severity score.
    """
    logging.debug(f"Resolving severity for {len(list(reports))} reports")
    if not reports:
        logging.warning("No reports provided to resolve_severity")
        return 0
    return round(sum(reports) / len(reports))
