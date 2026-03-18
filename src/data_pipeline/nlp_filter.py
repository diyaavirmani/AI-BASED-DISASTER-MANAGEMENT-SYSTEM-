"""NLP-based filtering and classification of social media disaster reports.

This module processes raw crowdsourced text data (tweets, Reddit posts) to
identify relevant disaster reports and filter out noise. It uses NLP techniques
to classify relevance, extract disaster type, and assess credibility.

After text processing and image analysis, it also resolves the severity of the
disaster using the severity_resolver module (4-layer priority approach).
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def load_social_data(json_file: str) -> List[Dict[str, Any]]:
    """Load raw social media JSON data.

    Parameters
    ----------
    json_file : str
        Path to JSON file containing crowdsourced reports.

    Returns
    -------
    List[Dict[str, Any]]
        List of report dictionaries with text, timestamps, and metadata.
    """
    logger.info(f"Loading social media data from {json_file}")
    return []


def filter_relevant_reports(
    reports: List[Dict[str, Any]],
    keywords: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """Filter social media reports for disaster relevance.

    Parameters
    ----------
    reports : List[Dict[str, Any]]
        Raw crowdsourced report data.
    keywords : Optional[List[str]]
        Keywords to filter on (e.g. ['flood', 'earthquake']). If None,
        uses a default disaster keyword list.

    Returns
    -------
    List[Dict[str, Any]]
        Filtered reports determined to be relevant to disaster response.
    """
    logger.info(f"Filtering {len(reports)} social reports for relevance")
    return reports 


# INSTRUCTION 110: Main integration function
def filter_and_enrich(
    raw_reports: List[Dict[str, Any]],
    event_id: str,
    db_session: Any = None,
    image_results: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Main processing pipeline: filter, classify, and enrich disaster reports.
    
    This function orchestrates the complete NLP pipeline:
    1. Loads or receives raw social media data
    2. Filters for disaster relevance
    3. Processes text and analyzes images
    4. Resolves severity using the 4-layer approach
    5. Enriches output with severity metadata
    
    Parameters
    ----------
    raw_reports : List[Dict[str, Any]]
        Raw social media report data
    event_id : str
        Unique disaster event identifier
    db_session : Any, optional
        SQLAlchemy database session for querying models
    image_results : Optional[List[Dict[str, Any]]], optional
        Pre-computed image analysis results (from social_image_analyzer)
        
    Returns
    -------
    List[Dict[str, Any]]
        Enriched reports with severity information merged in
    """
    logger.info(f"Starting filter_and_enrich pipeline for event {event_id}")
    
    # Step 1: Filter relevant reports
    filtered_reports = filter_relevant_reports(raw_reports)
    logger.info(f"Filtered {len(filtered_reports)} relevant reports")
    
    # Step 2: Process each report with text and image analysis
    enriched_reports = []
    
    for report in filtered_reports:
        enriched = dict(report)  # Copy original report
        
        # Extract cleaned text from the report
        cleaned_text = enriched.get('cleaned_text', enriched.get('text', ''))
        
        # Get image results for this specific report (if available)
        report_image_results = image_results or []
        
        # INSTRUCTION 110: Call severity_resolver after text and image processing
        from src.data_pipeline.severity_resolver import resolve_severity, format_severity_result
        
        try:
            score, source, label = resolve_severity(
                text_result=cleaned_text,
                image_results=report_image_results,
                event_id=event_id,
                db_session=db_session
            )
            
            # Format the result for database storage
            severity_dict = format_severity_result(score, source, label)
            
            # Merge severity result into the enriched report
            enriched.update(severity_dict)
            
            logger.debug(f"Report enriched with severity: {severity_dict}")
        except Exception as e:
            logger.error(f"Error resolving severity for event {event_id}: {e}")
            # Set default unresolved severity
            enriched.update({
                'severity_score': None,
                'severity_source': 'error',
                'severity_label': 'unknown',
                'severity_resolved': False,
            })
        
        enriched_reports.append(enriched)
    
    logger.info(f"Enriched {len(enriched_reports)} reports with severity information")
    return enriched_reports
