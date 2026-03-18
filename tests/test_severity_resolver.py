"""
Test suite for severity_resolver.py

Tests the 4-layer severity resolution system with comprehensive cases.
Instruction 111: Creates three main test cases to verify correct layer usage.
"""

import unittest
from unittest.mock import Mock, MagicMock

from src.data_pipeline.severity_resolver import (
    SEVERITY_KEYWORDS,
    resolve_from_gdacs,
    resolve_from_satellite,
    resolve_from_image,
    resolve_from_text,
    resolve_severity,
    format_severity_result,
    _compute_severity_label,
)


class TestSeverityKeywords(unittest.TestCase):
    """Test the SEVERITY_KEYWORDS constant."""
    
    def test_keywords_exist(self):
        """SEVERITY_KEYWORDS should contain expected keywords."""
        self.assertIn('catastrophic', SEVERITY_KEYWORDS)
        self.assertIn('severe', SEVERITY_KEYWORDS)
        self.assertIn('negligible', SEVERITY_KEYWORDS)
        
    def test_keyword_values(self):
        """SEVERITY_KEYWORDS values should be in 0-1 range."""
        for keyword, score in SEVERITY_KEYWORDS.items():
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)
    
    def test_catastrophic_score(self):
        """Catastrophic should have highest score."""
        self.assertEqual(SEVERITY_KEYWORDS['catastrophic'], 1.0)
        self.assertEqual(SEVERITY_KEYWORDS['apocalyptic'], 1.0)


class TestResolveFromGDACS(unittest.TestCase):
    """Test Layer 1: GDACS resolution."""
    
    def test_gdacs_score_exists(self):
        """Should return score and 'gdacs' when gdacs_alert_score exists."""
        # Mock database session and DisasterEvent
        mock_session = Mock()
        mock_event = Mock()
        mock_event.gdacs_alert_score = 0.85
        
        mock_session.query.return_value.filter.return_value.first.return_value = mock_event
        
        score, source = resolve_from_gdacs('event_123', mock_session)
        
        self.assertEqual(score, 0.85)
        self.assertEqual(source, 'gdacs')
    
    def test_gdacs_score_none(self):
        """Should return (None, None) when gdacs_alert_score is None."""
        mock_session = Mock()
        mock_event = Mock()
        mock_event.gdacs_alert_score = None
        
        mock_session.query.return_value.filter.return_value.first.return_value = mock_event
        
        score, source = resolve_from_gdacs('event_123', mock_session)
        
        self.assertIsNone(score)
        self.assertIsNone(source)
    
    def test_gdacs_event_not_found(self):
        """Should return (None, None) when event not found."""
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        score, source = resolve_from_gdacs('nonexistent', mock_session)
        
        self.assertIsNone(score)
        self.assertIsNone(source)


class TestResolveFromSatellite(unittest.TestCase):
    """Test Layer 2: Satellite imagery resolution."""
    
    def test_satellite_assessments_exist(self):
        """Should compute score from major_damage and destroyed pixels."""
        mock_session = Mock()
        mock_assessment = Mock()
        mock_assessment.major_damage_pixels = 100
        mock_assessment.destroyed_pixels = 50
        mock_assessment.total_pixels = 1000
        
        mock_session.query.return_value.filter.return_value.all.return_value = [mock_assessment]
        
        score, source = resolve_from_satellite('event_123', mock_session)
        
        # (100 + 50) / 1000 = 0.15
        self.assertEqual(score, 0.15)
        self.assertEqual(source, 'satellite_model')
    
    def test_satellite_no_assessments(self):
        """Should return (None, None) when no assessments found."""
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.all.return_value = []
        
        score, source = resolve_from_satellite('event_123', mock_session)
        
        self.assertIsNone(score)
        self.assertIsNone(source)
    
    def test_satellite_score_clamped(self):
        """Score should be clamped to 0-1 range."""
        mock_session = Mock()
        mock_assessment = Mock()
        mock_assessment.major_damage_pixels = 2000
        mock_assessment.destroyed_pixels = 1000
        mock_assessment.total_pixels = 1000  # Results in 3.0
        
        mock_session.query.return_value.filter.return_value.all.return_value = [mock_assessment]
        
        score, source = resolve_from_satellite('event_123', mock_session)
        
        self.assertEqual(score, 1.0)  # Clamped to max


class TestResolveFromImage(unittest.TestCase):
    """Test Layer 3: Social media image analysis resolution."""
    
    def test_case_1_high_confidence_severe(self):
        """INSTRUCTION 111 CASE 2: Image with high confidence 'severe' rating."""
        image_results = [
            {
                'severity': 'severe',
                'severity_confidence': 0.8,
                'source': 'CLIP_model'
            }
        ]
        
        score, source = resolve_from_image(image_results)
        
        self.assertEqual(score, 0.75)
        self.assertEqual(source, 'image_analysis')
    
    def test_low_confidence_filtered(self):
        """Should filter out results with confidence <= 0.6."""
        image_results = [
            {
                'severity': 'severe',
                'severity_confidence': 0.5,  # Below threshold
                'source': 'CLIP_model'
            }
        ]
        
        score, source = resolve_from_image(image_results)
        
        self.assertIsNone(score)
        self.assertIsNone(source)
    
    def test_multiple_images_highest(self):
        """Should return highest score from multiple images."""
        image_results = [
            {'severity': 'moderate', 'severity_confidence': 0.65},
            {'severity': 'severe', 'severity_confidence': 0.75},
            {'severity': 'minor', 'severity_confidence': 0.70},
        ]
        
        score, source = resolve_from_image(image_results)
        
        self.assertEqual(score, 0.75)  # Severe > moderate > minor
        self.assertEqual(source, 'image_analysis')
    
    def test_catastrophic_label(self):
        """Should handle catastrophic label."""
        image_results = [
            {'severity': 'catastrophic', 'severity_confidence': 0.9}
        ]
        
        score, source = resolve_from_image(image_results)
        
        self.assertEqual(score, 1.0)
        self.assertEqual(source, 'image_analysis')
    
    def test_empty_results(self):
        """Should handle empty results list."""
        score, source = resolve_from_image([])
        
        self.assertIsNone(score)
        self.assertIsNone(source)


class TestResolveFromText(unittest.TestCase):
    """Test Layer 4: Text keyword resolution."""
    
    def test_case_1_catastrophic_text(self):
        """INSTRUCTION 111 CASE 1: Text with 'catastrophic' keyword."""
        text = "This is a catastrophic disaster with massive destruction."
        
        score, source = resolve_from_text(text)
        
        self.assertEqual(score, 1.0)  # catastrophic = 1.0
        self.assertEqual(source, 'text_keywords')
    
    def test_multiple_keywords_highest(self):
        """Should return highest score from multiple matches."""
        text = "There was severe damage and minor flooding in the area."
        
        score, source = resolve_from_text(text)
        
        # severe=0.75, minor=0.25 -> max=0.75
        self.assertEqual(score, 0.75)
        self.assertEqual(source, 'text_keywords')
    
    def test_case_3_generic_text_no_keywords(self):
        """INSTRUCTION 111 CASE 3: Generic text with no severity keywords."""
        text = "This is just regular text about the weather."
        
        score, source = resolve_from_text(text)
        
        self.assertIsNone(score)
        self.assertIsNone(source)
    
    def test_case_insensitive_matching(self):
        """Keywords should match case-insensitively."""
        text = "The CATASTROPHIC event caused widespread damage."
        
        score, source = resolve_from_text(text)
        
        self.assertEqual(score, 1.0)
        self.assertEqual(source, 'text_keywords')
    
    def test_phrase_matching(self):
        """Should match multi-word keywords."""
        text = "There was complete destruction of the buildings."
        
        score, source = resolve_from_text(text)
        
        # 'completely destroyed' = 0.9 (phrase match)
        self.assertIsNotNone(score)
        self.assertGreater(score, 0.0)
    
    def test_empty_text(self):
        """Should handle empty text."""
        score, source = resolve_from_text("")
        
        self.assertIsNone(score)
        self.assertIsNone(source)


class TestResolveSeverity(unittest.TestCase):
    """Test the main orchestrator function."""
    
    def test_layer_1_prioritized(self):
        """Layer 1 (GDACS) should override other layers."""
        mock_session = Mock()
        mock_event = Mock()
        mock_event.gdacs_alert_score = 0.9
        mock_session.query.return_value.filter.return_value.first.return_value = mock_event
        
        # Provide text that would match Layer 4
        text = "This is catastrophic"
        image_results = []
        
        score, source, label = resolve_severity(text, image_results, 'event_1', mock_session)
        
        self.assertEqual(score, 0.9)
        self.assertEqual(source, 'gdacs')  # GDACS takes priority
        self.assertEqual(label, 'critical')
    
    def test_case_1_text_keywords_layer(self):
        """INSTRUCTION 111 CASE 1: Post with catastrophic - text layer."""
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_session.query.return_value.filter.return_value.all.return_value = []
        
        text = "This is a catastrophic disaster."
        image_results = []
        
        score, source, label = resolve_severity(text, image_results, 'event_1', mock_session)
        
        self.assertEqual(score, 1.0)
        self.assertEqual(source, 'text_keywords')
        self.assertEqual(label, 'critical')
    
    def test_case_2_image_analysis_layer(self):
        """INSTRUCTION 111 CASE 2: Post with image analysis - image layer."""
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_session.query.return_value.filter.return_value.all.return_value = []
        
        text = "Check out this damage"
        image_results = [
            {'severity': 'severe', 'severity_confidence': 0.85}
        ]
        
        score, source, label = resolve_severity(text, image_results, 'event_1', mock_session)
        
        self.assertEqual(score, 0.75)
        self.assertEqual(source, 'image_analysis')
        self.assertEqual(label, 'severe')
    
    def test_case_3_unresolved(self):
        """INSTRUCTION 111 CASE 3: Generic text, no images - unresolved."""
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_session.query.return_value.filter.return_value.all.return_value = []
        
        text = "Just a generic post about weather."
        image_results = []
        
        score, source, label = resolve_severity(text, image_results, 'event_1', mock_session)
        
        self.assertIsNone(score)
        self.assertEqual(source, 'unresolved')
        self.assertEqual(label, 'unknown')
    
    def test_layer_priority_order(self):
        """Verify layer priority order: GDACS > Satellite > Image > Text."""
        mock_session = Mock()
        
        # Set up so satellite and text would match, but not GDACS
        mock_event = Mock()
        mock_event.gdacs_alert_score = None
        mock_session.query.return_value.filter.return_value.first.return_value = mock_event
        
        # Satellite layer has data
        mock_assess = Mock()
        mock_assess.major_damage_pixels = 100
        mock_assess.destroyed_pixels = 50
        mock_assess.total_pixels = 1000
        mock_session.query.return_value.filter.return_value.all.return_value = [mock_assess]
        
        text = "catastrophic"  # Would match Layer 4
        image_results = []
        
        score, source, label = resolve_severity(text, image_results, 'event_1', mock_session)
        
        # Should use Layer 2 (Satellite), not Layer 4 (Text)
        self.assertEqual(source, 'satellite_model')


class TestComputeSeverityLabel(unittest.TestCase):
    """Test severity score to label conversion."""
    
    def test_critical_label(self):
        """Score >= 0.8 should be critical."""
        self.assertEqual(_compute_severity_label(0.8), 'critical')
        self.assertEqual(_compute_severity_label(1.0), 'critical')
        self.assertEqual(_compute_severity_label(0.95), 'critical')
    
    def test_severe_label(self):
        """Score 0.6-0.8 should be severe."""
        self.assertEqual(_compute_severity_label(0.6), 'severe')
        self.assertEqual(_compute_severity_label(0.75), 'severe')
        self.assertEqual(_compute_severity_label(0.79), 'severe')
    
    def test_moderate_label(self):
        """Score 0.4-0.6 should be moderate."""
        self.assertEqual(_compute_severity_label(0.4), 'moderate')
        self.assertEqual(_compute_severity_label(0.5), 'moderate')
        self.assertEqual(_compute_severity_label(0.59), 'moderate')
    
    def test_minor_label(self):
        """Score 0.2-0.4 should be minor."""
        self.assertEqual(_compute_severity_label(0.2), 'minor')
        self.assertEqual(_compute_severity_label(0.3), 'minor')
        self.assertEqual(_compute_severity_label(0.39), 'minor')
    
    def test_minimal_label(self):
        """Score < 0.2 should be minimal."""
        self.assertEqual(_compute_severity_label(0.0), 'minimal')
        self.assertEqual(_compute_severity_label(0.1), 'minimal')
        self.assertEqual(_compute_severity_label(0.19), 'minimal')
    
    def test_unknown_label(self):
        """None score should be unknown."""
        self.assertEqual(_compute_severity_label(None), 'unknown')


class TestFormatSeverityResult(unittest.TestCase):
    """Test formatting of severity result for database storage."""
    
    def test_resolved_result(self):
        """Should format resolved result correctly."""
        result = format_severity_result(0.85, 'gdacs', 'critical')
        
        self.assertEqual(result['severity_score'], 0.85)
        self.assertEqual(result['severity_source'], 'gdacs')
        self.assertEqual(result['severity_label'], 'critical')
        self.assertTrue(result['severity_resolved'])
    
    def test_unresolved_result(self):
        """Should format unresolved result correctly."""
        result = format_severity_result(None, 'unresolved', 'unknown')
        
        self.assertIsNone(result['severity_score'])
        self.assertEqual(result['severity_source'], 'unresolved')
        self.assertEqual(result['severity_label'], 'unknown')
        self.assertFalse(result['severity_resolved'])
    
    def test_text_keywords_result(self):
        """Should format text_keywords result correctly."""
        result = format_severity_result(0.75, 'text_keywords', 'severe')
        
        self.assertEqual(result['severity_score'], 0.75)
        self.assertEqual(result['severity_source'], 'text_keywords')
        self.assertEqual(result['severity_label'], 'severe')
        self.assertTrue(result['severity_resolved'])


if __name__ == '__main__':
    unittest.main()
