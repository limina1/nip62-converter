#!/usr/bin/env python3

import sys
import argparse
import json
from modules.key_utils import read_encrypted_key
from modules.event_creator import create_event
from modules.event_verifier import verify_event
from modules.event_publisher import publish_event
from modules.event_utils import print_event_summary

def create_deletion_event(event_ids: list[str], reason: str, key: str) -> dict:
    """Create a kind 5 deletion event for the given event IDs.
    
    Args:
        event_ids: List of event IDs to delete
        reason: Reason for deletion
        key: Private key for signing
        
    Returns:
        The deletion event
    """
    # Create tags for each event ID
    tags = [["e", event_id] for event_id in event_ids]
    
    # Create and verify the event
    event = create_event(5, reason, tags, key)
    
    if verify_event(event):
        print(f"Created deletion event: {event['id']}")
        return event
    else:
        print("Failed to verify deletion event!")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Create NIP-09 deletion events')
    parser.add_argument('--nsec', required=True, help='ncryptsec key or file path')
    parser.add_argument('--relays', required=True, nargs='+', help='Relay URLs to publish to')
    parser.add_argument('--event-ids', required=True, nargs='+', help='Event IDs to delete')
    parser.add_argument('--reason', default='', help='Optional reason for deletion')
    
    args = parser.parse_args()
    
    print(f"\nStarting deletion process...")
    print(f"Events to delete: {args.event_ids}")
    print(f"Relays: {args.relays}")
    if args.reason:
        print(f"Reason: {args.reason}")
    
    # Read the key
    key = read_encrypted_key(args.nsec) if args.nsec.startswith('/') else args.nsec
    
    # Create deletion event
    event = create_deletion_event(args.event_ids, args.reason, key)
    
    # Print event summary
    print("\nDeletion event details:")
    print_event_summary(event)
    
    # Get user confirmation
    if input("\nReady to publish deletion event? (y/N): ").lower() != 'y':
        print("Publication cancelled.")
        sys.exit(0)
    
    # Publish event
    print(f"\nPublishing deletion event to relays: {', '.join(args.relays)}")
    
    if publish_event(event, args.relays):
        print("\nDeletion event published successfully!")
    else:
        print("\nFailed to publish deletion event.")
        sys.exit(1)

if __name__ == "__main__":
    main()