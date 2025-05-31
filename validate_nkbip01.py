#!/usr/bin/env python3
"""
NKBIP-01 Validation Script
Validates that Nostr events comply with NKBIP-01 specification
"""

import json
import sys
from typing import List, Dict, Tuple, Optional
from pathlib import Path

class NKBIP01Validator:
    """Validator for NKBIP-01 compliant events"""
    
    # Required tags for each event kind
    REQUIRED_TAGS = {
        30040: {  # Index
            "required": ["d", "title", "auto-update", "m", "M"],
            "must_have_references": True,
            "mime_type": "application/json",
            "m_tag_values": ["meta-data/index/replaceable", "external-content/index/replaceable"]
        },
        30041: {  # Content
            "required": ["d", "title"],
            "must_have_references": False,
            "mime_type": None,  # Can vary
            "m_tag_values": ["article/publication-content/replaceable"]
        }
    }
    
    # Valid values for certain tags
    VALID_VALUES = {
        "auto-update": ["yes", "ask", "no"],
        "type": ["book", "illustrated", "magazine", "documentation", "academic", "blog"],
        "reading-direction": ["left-to-right, top-to-bottom", "right-to-left, top-to-bottom"]
    }
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate_event(self, event: Dict) -> Tuple[bool, List[str], List[str]]:
        """
        Validate a single event
        Returns: (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        # Check event kind
        kind = event.get("kind")
        if kind not in self.REQUIRED_TAGS:
            self.errors.append(f"Invalid event kind: {kind}. Must be 30040 or 30041")
            return False, self.errors, self.warnings
        
        # Validate tags
        tags = event.get("tags", [])
        self._validate_tags(tags, kind)
        
        # Validate content field
        if kind == 30040:
            if event.get("content", "").strip():
                self.errors.append("Index events (30040) must have empty content field")
        elif kind == 30041:
            if not event.get("content", "").strip():
                self.warnings.append("Content events (30041) should have non-empty content")
        
        # Check for proper p/E tag ordering
        self._validate_derivative_tags(tags)
        
        return len(self.errors) == 0, self.errors, self.warnings
    
    def _validate_tags(self, tags: List[List[str]], kind: int):
        """Validate tags according to NKBIP-01 requirements"""
        tag_dict = {tag[0]: tag[1:] for tag in tags if tag}
        requirements = self.REQUIRED_TAGS[kind]
        
        # Check required tags
        for req_tag in requirements["required"]:
            if req_tag not in tag_dict:
                self.errors.append(f"Missing required tag: {req_tag}")
        
        # Check for references if required
        if requirements["must_have_references"]:
            has_references = any(tag[0] == "a" for tag in tags if tag)
            if not has_references:
                self.errors.append("Index must include at least one 'a' tag reference")
        
        # Validate specific tag values
        self._validate_tag_values(tag_dict, kind)
        
        # Check tag formats
        self._validate_tag_formats(tag_dict, tags)
    
    def _validate_tag_values(self, tag_dict: Dict, kind: int):
        """Validate specific tag values"""
        requirements = self.REQUIRED_TAGS[kind]
        
        # Check MIME type
        if "m" in tag_dict:
            if requirements["mime_type"] and tag_dict["m"][0] != requirements["mime_type"]:
                self.errors.append(f"Invalid MIME type: {tag_dict['m'][0]}. Expected: {requirements['mime_type']}")
        
        # Check M tag
        if "M" in tag_dict:
            if tag_dict["M"][0] not in requirements["m_tag_values"]:
                self.errors.append(f"Invalid M tag value: {tag_dict['M'][0]}")
        
        # Check auto-update
        if "auto-update" in tag_dict:
            if tag_dict["auto-update"][0] not in self.VALID_VALUES["auto-update"]:
                self.errors.append(f"Invalid auto-update value: {tag_dict['auto-update'][0]}")
        
        # Check type
        if "type" in tag_dict:
            if tag_dict["type"][0] not in self.VALID_VALUES["type"]:
                self.warnings.append(f"Non-standard type value: {tag_dict['type'][0]}")
        
        # Check language format
        if "l" in tag_dict:
            lang_value = tag_dict["l"][0]
            if "ISO-639-1" not in lang_value:
                self.warnings.append(f"Language tag should include ISO-639-1 designation: {lang_value}")
    
    def _validate_tag_formats(self, tag_dict: Dict, tags: List[List[str]]):
        """Validate tag formats"""
        # Check 'a' tag format
        for tag in tags:
            if tag and tag[0] == "a":
                if len(tag) < 4:
                    self.errors.append(f"Invalid 'a' tag format: {tag}. Expected: ['a', 'kind:pubkey:dtag', 'relay_hint', 'event_id']")
                else:
                    # Validate the reference format
                    ref = tag[1]
                    parts = ref.split(":")
                    if len(parts) != 3:
                        self.errors.append(f"Invalid 'a' tag reference format: {ref}. Expected: kind:pubkey:dtag")
        
        # Check identifier tags
        if "i" in tag_dict:
            i_value = tag_dict["i"][0]
            if ":" not in i_value:
                self.warnings.append(f"Identifier 'i' tag should use format 'type:value': {i_value}")
            
            # Check for corresponding k tag
            if "k" not in tag_dict:
                self.warnings.append("'i' tag present but no 'k' tag found")
    
    def _validate_derivative_tags(self, tags: List[List[str]]):
        """Validate p and E tag ordering for derivative works"""
        p_indices = [i for i, tag in enumerate(tags) if tag and tag[0] == "p"]
        e_indices = [i for i, tag in enumerate(tags) if tag and tag[0] == "E"]
        
        for p_idx in p_indices:
            # Check if there's an E tag immediately after
            if p_idx + 1 not in e_indices:
                self.errors.append(f"'p' tag at position {p_idx} must be immediately followed by 'E' tag")

def validate_file(filepath: str) -> Tuple[bool, List[str], List[str]]:
    """Validate a JSON file containing a Nostr event"""
    try:
        with open(filepath, 'r') as f:
            event = json.load(f)
        
        validator = NKBIP01Validator()
        return validator.validate_event(event)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"], []
    except Exception as e:
        return False, [f"Error reading file: {e}"], []

def main():
    """Main validation function"""
    if len(sys.argv) < 2:
        print("Usage: python validate_nkbip01.py <event.json> [event2.json ...]")
        print("       python validate_nkbip01.py --example")
        sys.exit(1)
    
    if sys.argv[1] == "--example":
        # Show example valid events
        example_index = {
            "id": "1234567890abcdef",
            "pubkey": "abcdef1234567890",
            "created_at": 1234567890,
            "kind": 30040,
            "content": "",
            "tags": [
                ["d", "my-publication"],
                ["title", "My Publication"],
                ["auto-update", "yes"],
                ["type", "book"],
                ["m", "application/json"],
                ["M", "meta-data/index/replaceable"],
                ["l", "en, ISO-639-1"],
                ["reading-direction", "left-to-right, top-to-bottom"],
                ["version", "1"],
                ["author", "John Doe"],
                ["summary", "A great publication"],
                ["a", "30041:abcdef1234567890:chapter-1", "wss://relay.nostr.com", "eventid123"]
            ],
            "sig": "signature"
        }
        
        example_content = {
            "id": "eventid123",
            "pubkey": "abcdef1234567890",
            "created_at": 1234567890,
            "kind": 30041,
            "content": "Chapter 1 content here...",
            "tags": [
                ["d", "chapter-1"],
                ["title", "Chapter 1"],
                ["m", "text/asciidoc"],
                ["M", "article/publication-content/replaceable"],
                ["l", "en, ISO-639-1"]
            ],
            "sig": "signature"
        }
        
        print("Example NKBIP-01 compliant index event:")
        print(json.dumps(example_index, indent=2))
        print("\nExample NKBIP-01 compliant content event:")
        print(json.dumps(example_content, indent=2))
        return
    
    # Validate files
    all_valid = True
    for filepath in sys.argv[1:]:
        print(f"\nValidating: {filepath}")
        print("-" * 50)
        
        is_valid, errors, warnings = validate_file(filepath)
        
        if is_valid:
            print("✅ Valid NKBIP-01 event")
        else:
            print("❌ Invalid NKBIP-01 event")
            all_valid = False
        
        if errors:
            print("\nErrors:")
            for error in errors:
                print(f"  - {error}")
        
        if warnings:
            print("\nWarnings:")
            for warning in warnings:
                print(f"  - {warning}")
    
    sys.exit(0 if all_valid else 1)

if __name__ == "__main__":
    main()