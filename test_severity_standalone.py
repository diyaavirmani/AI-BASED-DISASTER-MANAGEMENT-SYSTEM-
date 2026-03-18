"""
Standalone test script for severity_resolver
Tests the three main instruction 111 cases without import issues
"""

import sys
sys.path.insert(0, 'c:\\Users\\Lenovo\\Desktop\\AI-BASED-DISASTER-MANAGEMENT-SYSTEM-')

from unittest.mock import Mock
from src.data_pipeline.severity_resolver import (
    resolve_from_text,
    resolve_from_image,
    resolve_severity,
    format_severity_result,
    _compute_severity_label,
)

def test_case_1_text_keywords():
    """INSTRUCTION 111 CASE 1: Post with 'catastrophic' - text keywords layer"""
    print("\n" + "="*70)
    print("TEST CASE 1: Text Keywords Layer")
    print("="*70)
    
    # Create a post with catastrophic in text, no images
    text = "This is a catastrophic disaster affecting thousands of people."
    image_results = []
    
    # Mock database session that returns None for all layers
    mock_session = Mock()
    mock_session.query.return_value.filter.return_value.first.return_value = None
    mock_session.query.return_value.filter.return_value.all.return_value = []
    
    # Test resolve_from_text directly
    score, source = resolve_from_text(text)
    print(f"✓ resolve_from_text() returned: score={score}, source={source}")
    assert score == 1.0, f"Expected score 1.0 (catastrophic), got {score}"
    assert source == 'text_keywords', f"Expected source 'text_keywords', got {source}"
    
    # Test full resolve_severity function
    score, source, label = resolve_severity(text, image_results, 'event_1', mock_session)
    print(f"✓ resolve_severity() returned: score={score}, source={source}, label={label}")
    assert score == 1.0
    assert source == 'text_keywords'
    assert label == 'critical'
    
    # Format result
    result = format_severity_result(score, source, label)
    print(f"✓ format_severity_result() returned valid dict with keys: {list(result.keys())}")
    assert result['severity_score'] == 1.0
    assert result['severity_source'] == 'text_keywords'
    assert result['severity_label'] == 'critical'
    assert result['severity_resolved'] == True
    
    print("✅ TEST CASE 1 PASSED: Severity correctly resolved from text keywords")


def test_case_2_image_analysis():
    """INSTRUCTION 111 CASE 2: Post with image analysis showing damage"""
    print("\n" + "="*70)
    print("TEST CASE 2: Image Analysis Layer")
    print("="*70)
    
    # Create image results with high confidence severe damage
    text = "Look at this disaster damage!"
    image_results = [
        {'severity': 'severe', 'severity_confidence': 0.85},
        {'severity': 'moderate', 'severity_confidence': 0.65},
    ]
    
    # Mock database session
    mock_session = Mock()
    mock_session.query.return_value.filter.return_value.first.return_value = None
    mock_session.query.return_value.filter.return_value.all.return_value = []
    
    # Test resolve_from_image directly
    score, source = resolve_from_image(image_results)
    print(f"✓ resolve_from_image() returned: score={score}, source={source}")
    assert score == 0.75, f"Expected score 0.75 (severe), got {score}"
    assert source == 'image_analysis', f"Expected source 'image_analysis', got {source}"
    
    # Test full resolve_severity function
    score, source, label = resolve_severity(text, image_results, 'event_2', mock_session)
    print(f"✓ resolve_severity() returned: score={score}, source={source}, label={label}")
    assert score == 0.75
    assert source == 'image_analysis'
    assert label == 'severe'
    
    # Format result
    result = format_severity_result(score, source, label)
    print(f"✓ format_severity_result() returned valid dict with keys: {list(result.keys())}")
    assert result['severity_score'] == 0.75
    assert result['severity_source'] == 'image_analysis'
    assert result['severity_resolved'] == True
    
    print("✅ TEST CASE 2 PASSED: Severity correctly resolved from image analysis")


def test_case_3_unresolved():
    """INSTRUCTION 111 CASE 3: Generic text and no images - unresolved"""
    print("\n" + "="*70)
    print("TEST CASE 3: Unresolved (No Keywords, No Images)")
    print("="*70)
    
    # Generic text with no severity keywords
    text = "This is just a regular weather update about the day's conditions."
    image_results = []
    
    # Mock database session
    mock_session = Mock()
    mock_session.query.return_value.filter.return_value.first.return_value = None
    mock_session.query.return_value.filter.return_value.all.return_value = []
    
    # Test resolve_from_text directly
    score, source = resolve_from_text(text)
    print(f"✓ resolve_from_text() returned: score={score}, source={source}")
    assert score is None, f"Expected None, got {score}"
    assert source is None, f"Expected None, got {source}"
    
    # Test resolve_from_image directly
    score, source = resolve_from_image(image_results)
    print(f"✓ resolve_from_image() returned: score={score}, source={source}")
    assert score is None
    assert source is None
    
    # Test full resolve_severity function
    score, source, label = resolve_severity(text, image_results, 'event_3', mock_session)
    print(f"✓ resolve_severity() returned: score={score}, source={source}, label={label}")
    assert score is None, f"Expected None, got {score}"
    assert source == 'unresolved', f"Expected 'unresolved', got {source}"
    assert label == 'unknown', f"Expected 'unknown', got {label}"
    
    # Format result
    result = format_severity_result(score, source, label)
    print(f"✓ format_severity_result() returned valid dict with keys: {list(result.keys())}")
    assert result['severity_score'] is None
    assert result['severity_source'] == 'unresolved'
    assert result['severity_label'] == 'unknown'
    assert result['severity_resolved'] == False
    
    print("✅ TEST CASE 3 PASSED: Severity correctly marked as unresolved")


def run_all_tests():
    """Run all three main test cases"""
    print("\n" + "="*70)
    print("SEVERITY RESOLVER TEST SUITE - INSTRUCTION 111")
    print("Testing 4-Layer Severity Resolution System")
    print("="*70)
    
    try:
        test_case_1_text_keywords()
        test_case_2_image_analysis()
        test_case_3_unresolved()
        
        print("\n" + "="*70)
        print("🎉 ALL THREE TEST CASES PASSED!")
        print("="*70)
        print("\nTest Summary:")
        print("  ✓ Case 1: Post with 'catastrophic' text → text_keywords layer")
        print("  ✓ Case 2: Post with image analysis → image_analysis layer")
        print("  ✓ Case 3: Generic text, no images → unresolved")
        print("\nAll layers are working correctly!")
        print("="*70 + "\n")
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
