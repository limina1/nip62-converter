#!/usr/bin/env python3

import sys
import argparse
import json
import os
import re
from typing import Dict, List, Optional, Tuple

from modules.adoc_parser import parse_adoc_file
from modules.tag_utils import (
    clean_tag,
    create_section_tags,
    create_index_tags,
    add_reference_to_index,
)
from modules.key_utils import read_encrypted_key
from modules.event_creator import create_event
from modules.event_verifier import verify_event
from modules.event_encoder import encode_event_id
from modules.event_publisher import publish_event
from modules.event_utils import print_event_summary, get_title_from_tags
from modules.nak_utils import nak_decode
import warnings


def extract_metadata(file_path: str) -> Dict[str, str]:
    """
    Extract metadata from the section between title and first section.
    Returns a dictionary with metadata keys and values.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract document title
    title_match = re.search(r"^=\s+(.+?)$", content, re.MULTILINE)
    if not title_match:
        print("Error: No document title found")
        return {}

    title = title_match.group(1).strip()

    # Find the position of the title and the first section heading
    title_pos = title_match.start()
    first_section_match = re.search(r"^==\s+.+?$", content, re.MULTILINE)
    first_section_pos = (
        first_section_match.start() if first_section_match else len(content)
    )

    # Extract the metadata section
    metadata_section = content[title_match.end() : first_section_pos].strip()

    # Initialize metadata dictionary with title
    metadata = {"title": title}

    # Extract image if it exists (usually right after title)
    image_match = re.search(r"image::([^\[]+)", metadata_section)
    if image_match:
        metadata["image"] = image_match.group(1).strip()

    # Extract author information
    author_match = re.search(r"^:author:\s+(.+?)$", metadata_section, re.MULTILINE)
    if author_match:
        metadata["author"] = author_match.group(1).strip()

    # Extract summary - usually a paragraph before the first section
    # Look for a paragraph that's not attribute definition
    summary_lines = []
    for line in metadata_section.split("\n"):
        line = line.strip()
        if line and not line.startswith(":") and not line.startswith("image::"):
            summary_lines.append(line)

    if summary_lines:
        metadata["summary"] = " ".join(summary_lines)

    # Extract other AsciiDoc attributes
    for match in re.finditer(r"^:([^:]+):\s+(.+?)$", metadata_section, re.MULTILINE):
        key = match.group(1).strip().lower()
        value = match.group(2).strip()
        metadata[key] = value

    # Extract tags (could be specified in different ways)
    tags = []
    tags_match = re.search(r"^:tags:\s+(.+?)$", metadata_section, re.MULTILINE)
    if tags_match:
        tags = [tag.strip() for tag in tags_match.group(1).split(",")]

    # Some documents use keywords instead of tags
    keywords_match = re.search(r"^:keywords:\s+(.+?)$", metadata_section, re.MULTILINE)
    if keywords_match:
        tags.extend([tag.strip() for tag in keywords_match.group(1).split(",")])

    if tags:
        metadata["tags"] = tags

    return metadata


def extract_title_image(file_path: str) -> str:
    """Extract the title image from an AsciiDoc file."""
    metadata = extract_metadata(file_path)
    return metadata.get("image", "")


def extract_images(content: str) -> List[str]:
    """Extract all images from the content."""
    images = []
    for line in content.split("\n"):
        if line.startswith("image::"):
            image = line.split("::")[1].strip()
            image = image.split("[")[0].strip()
            images.append(image)

    return images


def organize_sections(doc_title: str, sections: List[Dict]) -> List[Dict]:
    """Organize sections into L1 groups with their L2 sections.
    Uses document title as root section if no L1 sections exist.
    """
    # If no L1 sections, create virtual root section from document title
    has_l1_sections = any(s["level"] == 1 for s in sections)
    if not has_l1_sections:
        return [
            {
                "title": doc_title,
                "content": "",  # No content before first L2
                "is_root": True,
                "l2_sections": _group_l2_sections(sections),
            }
        ]

    # Normal processing for documents with L1 sections
    organized = []
    current_l1 = None
    current_l2 = None
    first_l1 = True

    for section in sections:
        if section["level"] == 1:
            if current_l1:
                if current_l2:
                    current_l1["l2_sections"].append(current_l2)
                organized.append(current_l1)

            current_l1 = {
                "title": section["title"],
                "content": section["content"],
                "is_root": first_l1,
                "l2_sections": [],
            }
            current_l2 = None
            first_l1 = False

        elif section["level"] == 2 and current_l1:
            if current_l2:
                current_l1["l2_sections"].append(current_l2)

            current_l2 = {"title": section["title"], "content": section["content"]}

        elif section["level"] > 2 and current_l2:
            heading = "=" * section["level"] + " " + section["title"]
            current_l2["content"] += f"\n\n{heading}\n{section['content']}"

    if current_l1:
        if current_l2:
            current_l1["l2_sections"].append(current_l2)
        organized.append(current_l1)

    return organized


def _group_l2_sections(sections: List[Dict]) -> List[Dict]:
    """Group level 2 sections and their subsections"""
    l2_sections = []
    current_section = None

    for section in sections:
        if section["level"] == 2:
            if current_section:
                l2_sections.append(current_section)
            current_section = {"title": section["title"], "content": section["content"]}
        elif section["level"] > 2 and current_section:
            heading = "=" * section["level"] + " " + section["title"]
            current_section["content"] += f"\n\n{heading}\n{section['content']}"

    if current_section:
        l2_sections.append(current_section)

    return l2_sections


def create_content_event(
    content: str,
    title: str,
    parent_title: str,
    key: str,
    author: Optional[str] = None,
    decrypt=True,
) -> Dict:
    """Create a 30041 event for a section"""
    tags = create_section_tags(parent_title, title)
    images = extract_images(content)

    if images:
        for image in images:
            tags.append(["image", image])

    tags.append(["m", "text/asciidoc"])
    if author:
        tags.append(["author", author])

    event = create_event(30041, content, tags, key, decrypt=decrypt)
    if verify_event(event):
        print(f"Event verified: {event['id']}")
        return event
    else:
        print("Event verification failed!")
        sys.exit(1)


def create_index_event(
    title: str,
    section_events: List[Dict],
    key: str,
    primary_relay: str,
    metadata: Optional[Dict] = None,
    author: Optional[str] = None,
    author_pubkey: Optional[str] = None,
    decrypt=True,
) -> Dict:
    """Create a 30040 event linking to section events with metadata"""
    index_tags = create_index_tags(title)

    # Add metadata tags
    if metadata:
        # Add image
        if "image" in metadata:
            index_tags.append(["image", metadata["image"]])

        # Add summary
        if "summary" in metadata:
            index_tags.append(["summary", metadata["summary"]])

        # Add tags
        if "tags" in metadata:
            for tag in metadata["tags"]:
                index_tags.append(["t", tag])

        # Add published date
        if "published" in metadata:
            index_tags.append(["published_on", metadata["published"]])

        # Add publisher
        if "publisher" in metadata:
            index_tags.append(["published_by", metadata["publisher"]])

        # Add language
        if "language" in metadata:
            index_tags.append(["l", metadata["language"]])

        # Add any other metadata as tags
        for key, value in metadata.items():
            if key not in [
                "image",
                "summary",
                "tags",
                "published",
                "publisher",
                "language",
                "title",
                "author",
            ]:
                # Convert multi-word keys to kebab-case
                tag_key = key.replace("_", "-")
                index_tags.append([tag_key, value])

    # Add author
    if author:
        index_tags.append(["author", author])

    # Add author pubkey
    if author_pubkey:
        index_tags.append(["p", author_pubkey])

    # Add section references
    for section in section_events:
        index_tags = add_reference_to_index(
            index_tags, section["event"], section["d_tag"], primary_relay
        )

    event = create_event(30040, "", index_tags, key, decrypt=decrypt)
    if verify_event(event):
        print(f"Event verified: {event['id']}")
        return event
    else:
        print("Index event verification failed!")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Convert AsciiDoc to NIP-62 Nostr events"
    )
    parser.add_argument("--nsec", required=True, help="ncryptsec key or file path")
    parser.add_argument(
        "--relays", required=True, nargs="+", help="Relay URLs to publish to"
    )
    parser.add_argument("--adoc-file", required=True, help="AsciiDoc file to convert")
    parser.add_argument("--author", help="Author name to include in tags")
    parser.add_argument("--author-pubkey", help="Author public key to include in tags")

    args = parser.parse_args()

    print("\nStarting conversion process...")
    print(f"Input file: {args.adoc_file}")
    print(f"Relays: {args.relays}")
    if args.author:
        print(f"Author: {args.author}")

    # Read the key
    key = read_encrypted_key(args.nsec) if args.nsec.startswith("/") else args.nsec

    # Extract metadata from the document
    metadata = extract_metadata(args.adoc_file)
    print("\nExtracted metadata:")
    for k, v in metadata.items():
        print(f"  {k}: {v}")

    # Parse the AsciiDoc file
    doc = parse_adoc_file(args.adoc_file)

    # Use metadata author if not provided in command line
    if not args.author and "author" in metadata:
        args.author = metadata["author"]
        print(f"Using author from document: {args.author}")

    # Organize sections using document title as root if needed
    organized = organize_sections(doc["title"], doc["sections"])
    if not organized:
        print("Error: No sections found in document")
        sys.exit(1)

    # Track all events for summary and publishing
    all_events = []
    primary_relay = args.relays[0]
    root_references = []  # Track everything to link in root 30040

    for l1_section in organized:
        section_events = []

        # Handle L2 sections under this L1
        for l2_section in l1_section["l2_sections"]:
            event = create_content_event(
                l2_section["content"],
                l2_section["title"],
                l1_section["title"],
                key,
                args.author,
            )

            section_events.append(
                {
                    "event": event,
                    "title": l2_section["title"],
                    "d_tag": next(tag[1] for tag in event["tags"] if tag[0] == "d"),
                }
            )
            all_events.append(("Content", event))

        # Create 30040 index for this L1 section only if it's not the root
        if not l1_section["is_root"] and section_events:
            # Each L1 section gets its own index, but without the full metadata
            l1_index = create_index_event(
                l1_section["title"],
                section_events,
                key,
                primary_relay,
                author=args.author,
                author_pubkey=args.author_pubkey,
            )
            all_events.append(("Index", l1_index))
            root_references.append(
                {
                    "event": l1_index,
                    "title": l1_section["title"],
                    "d_tag": next(tag[1] for tag in l1_index["tags"] if tag[0] == "d"),
                }
            )
        elif l1_section["is_root"]:
            # For root section, add its L2 sections directly to root references
            root_references.extend(section_events)

    # Create root index event linking everything with full metadata
    root_title = next(s["title"] for s in organized if s["is_root"])
    print("\nCreating root index event...")

    # Process author pubkey if provided
    if args.author_pubkey and "npub" in args.author_pubkey:
        warnings.warn("Author pubkey in npub format. Converting to pubkey...")
        args.author_pubkey = nak_decode(args.author_pubkey)["pubkey"]

    # Create the root index with full metadata
    root_index = create_index_event(
        root_title,
        root_references,
        key,
        primary_relay,
        metadata=metadata,
        author=args.author,
        author_pubkey=args.author_pubkey,
    )
    all_events.append(("Root Index", root_index))

    # Print summary of all events
    print("\n=== Events Summary ===")
    for event_type, event in all_events:
        print(f"\n{event_type}:")
        print_event_summary(event)

    # Get user confirmation
    if input("\nReady to publish these events? (y/N): ").lower() != "y":
        print("Publication cancelled.")
        sys.exit(0)

    # Publish events in order: content -> indexes -> root
    print(f"\nPublishing events to relays: {', '.join(args.relays)}")

    all_success = True
    for event_type, event in all_events:
        print(f"\nPublishing {event_type}...")
        if not publish_event(event, args.relays):
            print(f"Failed to publish {event_type} event!")
            all_success = False

    if all_success:
        print("\nAll events published successfully!")

        # Get nevent format (specific event)
        nevent = encode_event_id(root_index, args.relays, note_format=True)
        print(f"\nPublication references:")
        print(f"nevent: {nevent}")

        # Get naddr format (replaceable event)
        naddr = encode_event_id(root_index, args.relays, note_format=False)
        print(f"naddr:  {naddr}")
    else:
        print("\nSome events failed to publish.")


if __name__ == "__main__":
    main()
