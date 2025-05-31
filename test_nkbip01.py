#!/usr/bin/env python3
"""
Test script for NKBIP-01 implementation
Tests tag generation and validation without publishing
"""

import json
import sys
from modules.nkbip01_tags import NKBIP01Tags
from validate_nkbip01 import NKBIP01Validator

def test_index_tags():
    """Test index tag generation"""
    print("Testing Index Tag Generation...")
    
    metadata = {
        "image": "https://example.com/cover.jpg",
        "summary": "A test publication",
        "published_on": "2024-01-01",
        "published_by": "Test Publisher",
        "tags": ["test", "nkbip", "validation"],
        "doi": "10.1234/test"
    }
    
    tags = NKBIP01Tags.create_index_tags(
        title="Test Publication",
        d_tag="test-publication",
        author="Test Author",
        publication_type="book",
        metadata=metadata
    )
    
    print("\nGenerated Index Tags:")
    for tag in tags:
        print(f"  {tag}")
    
    # Create mock event
    event = {
        "id": "test123",
        "pubkey": "testpubkey",
        "created_at": 1234567890,
        "kind": 30040,
        "content": "",
        "tags": tags + [["a", "30041:testpubkey:chapter-1", "wss://relay.test", "eventid1"]],
        "sig": "testsig"
    }
    
    # Validate
    validator = NKBIP01Validator()
    is_valid, errors, warnings = validator.validate_event(event)
    
    print(f"\nValidation Result: {'✅ PASS' if is_valid else '❌ FAIL'}")
    if errors:
        print("Errors:")
        for error in errors:
            print(f"  - {error}")
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    
    return is_valid


def test_content_tags():
    """Test content tag generation"""
    print("\n\nTesting Content Tag Generation...")
    
    tags = NKBIP01Tags.create_content_tags(
        title="Chapter 1: Introduction",
        d_tag="test-publication-chapter-1",
        content_type="asciidoc"
    )
    
    print("\nGenerated Content Tags:")
    for tag in tags:
        print(f"  {tag}")
    
    # Create mock event
    event = {
        "id": "content123",
        "pubkey": "testpubkey",
        "created_at": 1234567890,
        "kind": 30041,
        "content": "This is the chapter content...",
        "tags": tags,
        "sig": "testsig"
    }
    
    # Validate
    validator = NKBIP01Validator()
    is_valid, errors, warnings = validator.validate_event(event)
    
    print(f"\nValidation Result: {'✅ PASS' if is_valid else '❌ FAIL'}")
    if errors:
        print("Errors:")
        for error in errors:
            print(f"  - {error}")
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    
    return is_valid


def test_external_content():
    """Test external content with attribution"""
    print("\n\nTesting External Content Tags...")
    
    metadata = {
        "doi": "10.1234/external",
        "source": "https://doi.org/10.1234/external",
        "summary": "External content test"
    }
    
    tags = NKBIP01Tags.create_index_tags(
        title="External Publication",
        d_tag="external-publication",
        publication_type="academic",
        external=True,
        metadata=metadata
    )
    
    # Add derivative work tags
    tags = NKBIP01Tags.add_derivative_work_tags(
        tags,
        original_author_pubkey="originalpubkey123",
        original_event_id="originalevent123",
        relay_url="wss://original.relay"
    )
    
    print("\nGenerated External Content Tags:")
    for tag in tags:
        print(f"  {tag}")
    
    # Check for required external tags
    tag_dict = {tag[0]: tag for tag in tags}
    checks = [
        ("external" in tag_dict, "Has 'external' tag"),
        ("i" in tag_dict, "Has identifier tag"),
        ("k" in tag_dict, "Has identifier type tag"),
        ("source" in tag_dict, "Has source URL"),
        ("p" in tag_dict, "Has original author pubkey"),
        ("E" in tag_dict, "Has original event reference")
    ]
    
    print("\nExternal Content Checks:")
    for check, desc in checks:
        print(f"  {desc}: {'✅' if check else '❌'}")
    
    return all(check[0] for check in checks)


def main():
    """Run all tests"""
    print("NKBIP-01 Implementation Test Suite")
    print("=" * 50)
    
    results = []
    
    # Run tests
    results.append(("Index Tag Generation", test_index_tags()))
    results.append(("Content Tag Generation", test_content_tags()))
    results.append(("External Content", test_external_content()))
    
    # Summary
    print("\n\nTest Summary")
    print("=" * 50)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + ("All tests passed! 🎉" if all_passed else "Some tests failed! ❌"))
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())