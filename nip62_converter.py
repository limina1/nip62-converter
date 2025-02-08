#!/usr/bin/env python3

import sys
import argparse
import json
import os

from modules.adoc_parser import parse_adoc_file
from modules.tag_utils import (
    clean_tag, create_section_tags, create_index_tags,
    add_reference_to_index
)
from modules.key_utils import read_encrypted_key
from modules.event_creator import create_event
from modules.event_verifier import verify_event
from modules.event_encoder import encode_event_id
from modules.event_publisher import publish_event
from modules.event_utils import print_event_summary, get_title_from_tags

def main():
    parser = argparse.ArgumentParser(description='Convert AsciiDoc to NIP-62 Nostr events')
    parser.add_argument('--nsec', required=True, help='ncryptsec key or file path')
    parser.add_argument('--relays', required=True, nargs='+', help='Relay URLs to publish to')
    parser.add_argument('--adoc-file', required=True, help='AsciiDoc file to convert')
    parser.add_argument('--author', help='Author name to include in tags')
    
    args = parser.parse_args()
    
    print(f"\nStarting conversion process...")
    print(f"Input file: {args.adoc_file}")
    print(f"Relays: {args.relays}")
    if args.author:
        print(f"Author: {args.author}")
    
    # Read the key
    key = read_encrypted_key(args.nsec) if args.nsec.startswith('/') else args.nsec
    
    # Parse the AsciiDoc file
    doc = parse_adoc_file(args.adoc_file)
    
    # Create content events for each section
    section_events = []
    print("\nCreating section events...")
    
    for section in doc['sections']:
        if not section['title']:
            print(f"Debug: Skipping section with no title")
            continue
            
        tags = create_section_tags(doc['title'], section['title'])
        if args.author:
            tags.append(['author', args.author])
        
        print(f"\nProcessing section: {section['title']}")
        print(f"Debug: Created tags: {json.dumps(tags, indent=2)}")
        
        event = create_event(30041, section['content'], tags, key)
        
        if verify_event(event):
            print(f"Event verified: {event['id']}")
            section_events.append({
                'event': event,
                'level': section['level'],
                'd_tag': next(tag[1] for tag in tags if tag[0] == 'd'),
                'title': section['title']
            })
        else:
            print(f"Event verification failed!")
            sys.exit(1)
    
    # Create the index event
    print("\nCreating index event...")
    index_tags = create_index_tags(doc['title'])
    if args.author:
        index_tags.append(['author', args.author])
    
    # Add references to all sections
    primary_relay = args.relays[0]
    for section in section_events:
        index_tags = add_reference_to_index(
            index_tags,
            section['event'],
            section['d_tag'],
            primary_relay
        )
    
    print(f"Debug: Created index tags: {json.dumps(index_tags, indent=2)}")
    index_event = create_event(30040, "", index_tags, key)
    
    if not verify_event(index_event):
        print("Index event verification failed!")
        sys.exit(1)
    
    # Print summary of all events
    print("\n=== Events Summary ===")
    print("\nSection Events:")
    for section in section_events:
        print_event_summary(section['event'])
    
    print("\nIndex Event:")
    print_event_summary(index_event)
    
    # Get user confirmation
    if input("\nReady to publish these events? (y/N): ").lower() != 'y':
        print("Publication cancelled.")
        sys.exit(0)
    
    # Publish events
    print(f"\nPublishing events to relays: {', '.join(args.relays)}")
    
    all_success = True
    
    # Publish section events first
    for section in section_events:
        print(f"\nPublishing section: {section['title']}")
        if not publish_event(section['event'], args.relays):
            print(f"Failed to publish section event!")
            all_success = False
    
    # Publish index event
    print("\nPublishing index event...")
    if not publish_event(index_event, args.relays):
        print("Failed to publish index event!")
        all_success = False
    
    if all_success:
        print("\nAll events published successfully!")
        
        # Get nevent format (specific event)
        nevent = encode_event_id(index_event, args.relays, note_format=True)
        print(f"\nPublication references:")
        print(f"nevent: {nevent}")
        
        # Get naddr format (replaceable event)
        naddr = encode_event_id(index_event, args.relays, note_format=False)
        print(f"naddr:  {naddr}")
    else:
        print("\nSome events failed to publish.")

if __name__ == "__main__":
    main()