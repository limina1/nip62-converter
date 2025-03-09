#!/usr/bin/env python3

import sys
import argparse
import os
from typing import Dict, List, Optional, Tuple

from nip62_converter import (
    create_event,
    verify_event,
    create_section_tags,
    create_index_tags,
    add_reference_to_index,
    print_event_summary,
    encode_event_id,
    publish_event,
    read_encrypted_key
)
from modules.adoc_parser import parse_adoc_file

def find_main_doc(folder_path: str, project_name: str) -> Optional[str]:
    """Find the main documentation file based on project name"""
    main_file = f"{project_name}.adoc"
    main_path = os.path.join(folder_path, main_file)
    return main_path if os.path.exists(main_path) else None

def parse_docs_folder(folder_path: str, project_name: str) -> List[Dict]:
    """Parse all .adoc files, preserving paths for naming"""
    docs = []
    main_doc = f"{project_name}.adoc"
    
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.adoc'):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, folder_path)
                try:
                    doc = parse_adoc_file(full_path)
                    # Store full document details
                    docs.append({
                        'content': doc.get('content', ''),
                        'file_path': full_path,
                        'rel_path': rel_path,
                        'sections': doc.get('sections', []),
                        'is_main': file == main_doc
                    })
                except Exception as e:
                    print(f"Warning: Failed to parse {full_path}: {e}")
    
    return docs

def get_event_name(project_name: str, rel_path: str) -> str:
    """Create event name from project and relative path"""
    # Remove .adoc extension
    base_path = os.path.splitext(rel_path)[0]
    filename = os.path.basename(base_path)
    
    # Special handling for main project file
    if filename == project_name:
        return f"main_{project_name}"
    
    # For other files
    parts = base_path.split(os.sep)
    if len(parts) == 1:
        return f"{project_name}-{parts[0]}"
    else:
        return f"{project_name}-{parts[0]}-{parts[-1]}"

def create_content_event(
    doc: Dict, project_name: str, key: str, author: Optional[str] = None
) -> Dict:
    # Get event name from path
    event_name = get_event_name(project_name, doc["rel_path"])
    filename = os.path.basename(doc["file_path"])
    name_without_ext = os.path.splitext(filename)[0]

    # Special handling for main project file
    if doc.get('is_main'):
        content = [f"= Main: {project_name}"]
    else:
        content = [f"= {name_without_ext}"]

    # Add sections
    for section in doc["sections"]:
        heading = "=" * section["level"] + " " + section["title"]
        content.append(heading)
        if section["content"].strip():
            content.append(section["content"].strip())
        content.append("")  # Add blank line between sections

    # Create event
    tags = create_section_tags(project_name, event_name)
    if author:
        tags.append(["author", author])

    event = create_event(30041, "\n".join(content).strip(), tags, key)
    if verify_event(event):
        print(f"Created 30041 for {event_name}")
        return {
            "event": event,
            "title": event_name,
            "d_tag": next(tag[1] for tag in tags if tag[0] == "d"),
        }
    else:
        print(f"Failed to verify event for {event_name}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Create NIP-62 events from docs')
    parser.add_argument('--docs-dir', required=True, help='Docs directory to process')
    parser.add_argument('--nsec', required=True, help='ncryptsec key or file path')
    parser.add_argument('--relays', required=True, nargs='+', help='Relay URLs to publish to')
    parser.add_argument('--author', help='Author name to include in tags')
    parser.add_argument('--project', help='Project name (default: docs dir name)')
    
    args = parser.parse_args()
    
    # Determine project name
    if args.project:
        project_name = args.project
    else:
        project_name = os.path.basename(os.path.abspath(args.docs_dir))
    
    print(f"Project name: {project_name}")
    
    # Verify main project doc exists
    main_doc = find_main_doc(args.docs_dir, project_name)
    if not main_doc:
        print(f"Error: Main project doc {project_name}.adoc not found!")
        sys.exit(1)
    
    # Read key
    key = read_encrypted_key(args.nsec) if args.nsec.startswith('/') else args.nsec
    primary_relay = args.relays[0]
    
    # Parse all docs
    print(f"\nScanning docs folder: {args.docs_dir}")
    docs = parse_docs_folder(args.docs_dir, project_name)
    
    if not docs:
        print("Error: No .adoc files found!")
        sys.exit(1)
    
    # Separate main doc and other docs
    main_doc = next((doc for doc in docs if doc.get('is_main')), None)
    other_docs = [doc for doc in docs if not doc.get('is_main')]
    
    # Track all events and references
    all_events = []
    all_references = []
    
    # 1. Process main project doc first
    print(f"\nProcessing {project_name}.adoc...")
    if main_doc:
        main_event = create_content_event(main_doc, project_name, key, args.author)
        all_events.append(('Main Content', main_event))
        all_references.append(main_event)
        print(f"Created main event: {main_event['title']}")
    
    # 2. Process all other docs
    for doc in other_docs:
        event = create_content_event(doc, project_name, key, args.author)
        all_events.append(('Content', event))
        all_references.append(event)
    
    # Create root index with main event first
    print("\nCreating root index...")
    root_tags = create_index_tags(project_name)
    if args.author:
        root_tags.append(['author', args.author])
    
    # Add all references (main event will be first as it's first in all_references)
    for ref in all_references:
        root_tags = add_reference_to_index(
            root_tags,
            ref['event'],
            ref['d_tag'],
            primary_relay
        )
    
    root_index = create_event(30040, "", root_tags, key)
    if verify_event(root_index):
        print(f"Created root 30040 index")
        all_events.append(('Root Index', {
            'event': root_index,
            'title': project_name
        }))
    else:
        print("Failed to verify root index!")
        sys.exit(1)
    
    # Print summary
    print("\n=== Events Summary ===")
    for event_type, event in all_events:
        print(f"\n{event_type}:")
        print_event_summary(event['event'])
    
    # Get confirmation
    if input("\nReady to publish these events? (y/N): ").lower() != 'y':
        print("Publication cancelled.")
        sys.exit(0)
    
    # Publish events in order: main -> others -> root
    print(f"\nPublishing events to relays: {', '.join(args.relays)}")
    all_success = True
    
    for event_type, event in all_events:
        print(f"\nPublishing {event_type}...")
        if not publish_event(event['event'], args.relays):
            print(f"Failed to publish {event_type}!")
            all_success = False
    
    if all_success:
        print("\nAll events published successfully!")
        
        nevent = encode_event_id(root_index, args.relays, note_format=True)
        print(f"\nPublication references:")
        print(f"nevent: {nevent}")
        
        naddr = encode_event_id(root_index, args.relays, note_format=False)
        print(f"naddr:  {naddr}")
    else:
        print("\nSome events failed to publish.")

if __name__ == "__main__":
    main()