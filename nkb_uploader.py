#!/usr/bin/env python3
"""
NKBIP-01 Compliant Document Uploader
Converts AsciiDoc documents to Nostr events following NKBIP-01 specification
"""

import sys
import argparse
import json
import os
import re
from typing import Dict, List, Optional, Tuple
import warnings
from pprint import pprint

# Import modules
from modules.adoc_parser import parse_adoc_file
from modules.nkbip01_tags import NKBIP01Tags, PublicationType
from modules.tag_utils import clean_tag, add_reference_to_index, fetch_doi_metadata
from modules.key_utils import read_encrypted_key
from modules.event_creator import create_event
from modules.event_verifier import verify_event
from modules.event_encoder import encode_event_id
from modules.event_publisher import publish_event
from modules.event_utils import print_event_summary
from modules.nak_utils import nak_decode


class NKBIPDocument:
    """Represents a document to be published following NKBIP-01"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.metadata = {}
        self.sections = []
        self.title = ""
        self.publication_type = "book"  # default
        
    def extract_metadata(self) -> Dict[str, str]:
        """Extract metadata from the AsciiDoc preamble"""
        with open(self.file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract document title
        title_match = re.search(r"^=\s+(.+?)$", content, re.MULTILINE)
        if not title_match:
            raise ValueError("No document title found")

        self.title = title_match.group(1).strip()

        # Find metadata section (between title and first section)
        title_pos = title_match.start()
        first_section_match = re.search(r"^==\s+.+?$", content, re.MULTILINE)
        first_section_pos = first_section_match.start() if first_section_match else len(content)
        metadata_section = content[title_match.end():first_section_pos].strip()

        # Extract image
        image_match = re.search(r"image::([^\[]+)", metadata_section)
        if image_match:
            self.metadata["image"] = image_match.group(1).strip()

        # Extract AsciiDoc attributes
        for match in re.finditer(r"^:([^:]+):\s+(.+?)$", metadata_section, re.MULTILINE):
            key = match.group(1).strip().lower()
            value = match.group(2).strip()
            
            # Map common attributes to NKBIP-01 fields
            if key == "author":
                self.metadata["author"] = value
            elif key == "published":
                self.metadata["published_on"] = value
            elif key == "publisher":
                self.metadata["published_by"] = value
            elif key == "tags" or key == "keywords":
                self.metadata["tags"] = [tag.strip() for tag in value.split(",")]
            elif key == "language":
                self.metadata["language"] = value
            elif key == "type":
                self.publication_type = value
            elif key == "doi":
                self.metadata["doi"] = value
            elif key == "isbn":
                self.metadata["isbn"] = value
            elif key == "source":
                self.metadata["source"] = value
            elif key == "version":
                self.metadata["version"] = value
            else:
                # Store other attributes as-is
                self.metadata[key] = value

        # Extract summary (non-attribute text)
        summary_lines = []
        for line in metadata_section.split("\n"):
            line = line.strip()
            if line and not line.startswith(":") and not line.startswith("image::"):
                summary_lines.append(line)
        
        if summary_lines:
            self.metadata["summary"] = " ".join(summary_lines)

        return self.metadata

    def parse_document(self):
        """Parse the AsciiDoc document"""
        doc = parse_adoc_file(self.file_path)
        self.sections = doc["sections"]
        if not self.title:
            self.title = doc["title"]
        return doc


def create_nkbip_content_event(
    content: str,
    title: str,
    d_tag: str,
    key: str,
    author: Optional[str] = None,
    language: str = "en",
    decrypt: bool = True
) -> Dict:
    """Create a NKBIP-01 compliant 30041 content event"""
    
    # Create NKBIP-01 compliant tags
    tags = NKBIP01Tags.create_content_tags(
        title=title,
        d_tag=d_tag,
        content_type="asciidoc",
        language=language
    )
    
    # Extract and add images
    images = re.findall(r'image::([^\[]+)', content)
    for image in images:
        tags.append(["image", image.strip()])
    
    # Add author if provided
    if author:
        tags.append(["author", author])
    
    # Create and verify event
    event = create_event(30041, content, tags, key, decrypt=decrypt)
    if not verify_event(event):
        raise ValueError("Content event verification failed!")
    
    return event


def create_nkbip_index_event(
    title: str,
    d_tag: str,
    section_events: List[Dict],
    key: str,
    primary_relay: str,
    document: NKBIPDocument,
    author_pubkey: Optional[str] = None,
    external: bool = False,
    decrypt: bool = True
) -> Dict:
    """Create a NKBIP-01 compliant 30040 index event"""
    
    # Get metadata
    metadata = document.metadata.copy()
    author = metadata.pop("author", None)
    language = metadata.pop("language", "en")
    version = metadata.pop("version", "1")
    
    # Create NKBIP-01 compliant tags
    tags = NKBIP01Tags.create_index_tags(
        title=title,
        d_tag=d_tag,
        author=author,
        publication_type=document.publication_type,
        language=language,
        version=version,
        external=external,
        metadata=metadata
    )
    
    # Add derivative work tags if author_pubkey provided
    if author_pubkey and external:
        tags = NKBIP01Tags.add_derivative_work_tags(
            tags,
            original_author_pubkey=author_pubkey,
            original_event_id="",  # Would need original event ID
            relay_url=primary_relay
        )
    
    # Add section references
    for section in section_events:
        tags = add_reference_to_index(
            tags, 
            section["event"], 
            section["d_tag"], 
            primary_relay
        )
    
    # Create and verify event
    event = create_event(30040, "", tags, key, decrypt=decrypt)
    if not verify_event(event):
        raise ValueError("Index event verification failed!")
    
    # Validate NKBIP-01 compliance
    from validate_nkbip01 import NKBIP01Validator
    validator = NKBIP01Validator()
    is_valid, errors, warnings = validator.validate_event(event)
    
    if not is_valid:
        print("NKBIP-01 validation errors:")
        for error in errors:
            print(f"  - {error}")
        raise ValueError("Index event is not NKBIP-01 compliant!")
    
    if warnings:
        print("NKBIP-01 validation warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    
    return event


def organize_sections_hierarchical(sections: List[Dict]) -> List[Dict]:
    """Organize sections into hierarchical structure"""
    organized = []
    current_l1 = None
    
    for section in sections:
        if section["level"] == 1:
            if current_l1:
                organized.append(current_l1)
            current_l1 = {
                "title": section["title"],
                "content": section["content"],
                "subsections": []
            }
        elif section["level"] == 2 and current_l1:
            current_l1["subsections"].append({
                "title": section["title"],
                "content": section["content"],
                "level": section["level"]
            })
        elif section["level"] > 2 and current_l1 and current_l1["subsections"]:
            # Append to last L2 section
            last_l2 = current_l1["subsections"][-1]
            heading = "=" * section["level"] + " " + section["title"]
            last_l2["content"] += f"\n\n{heading}\n{section['content']}"
    
    if current_l1:
        organized.append(current_l1)
    
    return organized


def main():
    parser = argparse.ArgumentParser(
        description="NKBIP-01 compliant document uploader for Nostr"
    )
    parser.add_argument("--nsec", required=True, help="ncryptsec key or file path")
    parser.add_argument("--relays", required=True, nargs="+", help="Relay URLs")
    parser.add_argument("--file", required=True, help="AsciiDoc file to upload")
    parser.add_argument("--author-pubkey", help="Author public key (for attribution)")
    parser.add_argument("--type", choices=["book", "academic", "documentation", "blog", "magazine"], 
                       default="book", help="Publication type")
    parser.add_argument("--external", action="store_true", help="Mark as external content")
    parser.add_argument("--doi", help="DOI identifier")
    parser.add_argument("--validate-only", action="store_true", help="Only validate, don't publish")
    
    args = parser.parse_args()
    
    # Read key
    key = read_encrypted_key(args.nsec) if args.nsec.startswith("/") else args.nsec
    
    # Create document instance
    print(f"Loading document: {args.file}")
    document = NKBIPDocument(args.file)
    
    # Extract metadata
    print("\nExtracting metadata...")
    metadata = document.extract_metadata()
    document.publication_type = args.type
    
    # Add DOI if provided
    if args.doi:
        document.metadata["doi"] = args.doi
        if args.external:
            # Fetch DOI metadata
            doi_tags = fetch_doi_metadata(args.doi)
            # Merge DOI metadata
            for tag in doi_tags:
                if tag[0] == "title" and not document.title:
                    document.title = tag[1]
                elif tag[0] == "author" and "author" not in document.metadata:
                    document.metadata["author"] = tag[1]
                elif tag[0] == "summary" and "summary" not in document.metadata:
                    document.metadata["summary"] = tag[1]
    
    print("\nDocument metadata:")
    print(f"  Title: {document.title}")
    print(f"  Type: {document.publication_type}")
    for k, v in document.metadata.items():
        print(f"  {k}: {v}")
    
    # Parse document
    print("\nParsing document structure...")
    doc = document.parse_document()
    
    # Organize sections
    organized = organize_sections_hierarchical(doc["sections"])
    print(f"\nFound {len(organized)} top-level sections")
    
    # Track all events
    all_events = []
    section_events = []
    primary_relay = args.relays[0]
    
    # Create content events for each section
    for l1_section in organized:
        for l2_section in l1_section["subsections"]:
            print(f"\nCreating content event for: {l2_section['title']}")
            
            # Create d-tag
            d_tag = f"{clean_tag(document.title)}-{clean_tag(l2_section['title'])}"
            
            event = create_nkbip_content_event(
                content=l2_section["content"],
                title=l2_section["title"],
                d_tag=d_tag,
                key=key,
                author=document.metadata.get("author"),
                language=document.metadata.get("language", "en")
            )
            
            section_events.append({
                "event": event,
                "title": l2_section["title"],
                "d_tag": d_tag
            })
            all_events.append(("Content", event))
    
    # Create index event
    print(f"\nCreating index event for: {document.title}")
    index_d_tag = clean_tag(document.title)
    
    # Process author pubkey if needed
    if args.author_pubkey and "npub" in args.author_pubkey:
        print("Converting npub to hex...")
        args.author_pubkey = nak_decode(args.author_pubkey)["pubkey"]
    
    index_event = create_nkbip_index_event(
        title=document.title,
        d_tag=index_d_tag,
        section_events=section_events,
        key=key,
        primary_relay=primary_relay,
        document=document,
        author_pubkey=args.author_pubkey,
        external=args.external
    )
    all_events.append(("Index", index_event))
    
    # Print summary
    print("\n=== NKBIP-01 Events Summary ===")
    for event_type, event in all_events:
        print(f"\n{event_type}:")
        print_event_summary(event)
    
    if args.validate_only:
        print("\nValidation complete. Not publishing (--validate-only flag set)")
        return
    
    # Confirm publication
    if input("\nPublish these events? (y/N): ").lower() != "y":
        print("Publication cancelled.")
        return
    
    # Publish events
    print(f"\nPublishing to relays: {', '.join(args.relays)}")
    
    success = True
    for event_type, event in all_events:
        print(f"\nPublishing {event_type}...")
        if not publish_event(event, args.relays):
            print(f"Failed to publish {event_type}!")
            success = False
    
    if success:
        print("\n✅ All events published successfully!")
        
        # Show references
        nevent = encode_event_id(index_event, args.relays, note_format=True)
        naddr = encode_event_id(index_event, args.relays, note_format=False)
        
        print(f"\nPublication references:")
        print(f"nevent: {nevent}")
        print(f"naddr:  {naddr}")
    else:
        print("\n❌ Some events failed to publish")


if __name__ == "__main__":
    main()