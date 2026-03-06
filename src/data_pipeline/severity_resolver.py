"""
Determines the final severity score for a disaster 
report by checking multiple sources in priortiy 



This module contains helper routines used by the
pipeline to merge external severity estimates and
produce a canonical integer score.
"""

import logging


def resolve_severity(reports: list) -> int:
    """Compute a combined severity score from multiple
    input reports.  The current implementation is a
    simple average, but the signature leaves room for
    more sophisticated logic.

    Args:
        reports (list): List of numeric severity values.

    Returns:
        int: Rounded severity score.
    """
    logging.debug(f"Resolving severity for {len(reports)} reports")
    if not reports:
        logging.warning("No reports provided to resolve_severity")
        return 0
    return round(sum(reports) / len(reports))
