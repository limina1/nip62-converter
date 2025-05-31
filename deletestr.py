#!/usr/bin/env python3

import argparse
import subprocess
import sys
import json
from typing import Dict, Any, List


def get_pubkey(key: str) -> str:
    """Get public key from a private key using nak."""
    try:
        process = subprocess.run(
            ["nak", "key", "public", key],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if process.returncode != 0:
            raise Exception(f"Failed to get pubkey: {process.stderr}")
        return process.stdout.strip()
    except Exception as e:
        print(f"Error getting pubkey: {e}")
        sys.exit(1)


def fetch_event(event_id: str, relay: str) -> Dict[str, Any]:
    """Fetch a specific event by ID from a relay."""
    try:
        process = subprocess.run(
            ["nak", "req", "-i", event_id, relay],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        if process.returncode != 0:
            raise Exception(f"Failed to fetch event: {process.stderr}")

        output = process.stdout.strip()
        for line in output.split("\n"):
            if (
                line
                and not line.startswith("connecting")
                and not line.startswith("ok.")
            ):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue

        raise Exception(f"Event with ID {event_id} not found on relay {relay}")
    except Exception as e:
        print(f"Error fetching event: {e}")
        sys.exit(1)


def create_deletion_request(
    event_id: str, kind: int, reason: str, key: str
) -> Dict[str, Any]:
    """Create a NIP-09 deletion request for the specified event."""
    try:
        cmd = ["nak", "event", "--sec", key, "-k", "5"]

        # Add tags
        cmd.extend(["-e", event_id])
        cmd.extend(["-t", f"k={kind}"])

        # Add reason if provided
        if reason:
            cmd.extend(["-c", reason])
        else:
            cmd.extend(["-c", ""])

        process = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        if process.returncode != 0:
            raise Exception(f"Failed to create deletion event: {process.stderr}")

        return json.loads(process.stdout)
    except Exception as e:
        print(f"Error creating deletion request: {e}")
        sys.exit(1)


def publish_deletion_request(event: Dict[str, Any], relay: str) -> bool:
    """Publish the deletion request to the relay."""
    try:
        # Create a temporary file with the event JSON
        with open("temp_event.json", "w") as f:
            json.dump(event, f)

        # Use nak to publish the event from the file
        cmd = f"cat temp_event.json | nak event {relay}"
        process = subprocess.run(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        # Clean up the temporary file
        subprocess.run(["rm", "temp_event.json"])

        if process.returncode != 0 or "failed" in process.stdout.lower():
            raise Exception(
                f"Failed to publish deletion request: {process.stdout}\n{process.stderr}"
            )

        return True
    except Exception as e:
        print(f"Error publishing deletion request: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Delete a specific Nostr event from a relay"
    )
    parser.add_argument("--event-id", required=True, help="ID of the event to delete")
    parser.add_argument(
        "--relay", required=True, help="Relay URL to delete the event from"
    )
    parser.add_argument(
        "--nsec", required=True, help="Private key (hex, nsec, or ncryptsec)"
    )
    parser.add_argument("--reason", default="", help="Optional reason for deletion")

    args = parser.parse_args()

    print("\nStarting event deletion process...")
    print(f"Target event: {args.event_id}")
    print(f"Relay: {args.relay}")

    # Handling encrypted keys
    key = args.nsec
    if key.startswith("ncryptsec"):
        try:
            process = subprocess.run(
                ["nak", "key", "decrypt", key],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                input="",  # This will prompt for password if needed
            )
            if process.returncode != 0:
                raise Exception(f"Failed to decrypt key: {process.stderr}")
            key = process.stdout.strip()
        except Exception as e:
            print(f"Error decrypting key: {e}")
            sys.exit(1)

    # Get pubkey
    pubkey = get_pubkey(key)
    print(f"Using pubkey: {pubkey}")

    # Fetch the event to get its kind
    print(f"\nFetching event {args.event_id} from {args.relay}...")
    try:
        event = fetch_event(args.event_id, args.relay)
        kind = event.get("kind", 1)  # Default to kind 1 if not found

        # Verify the event belongs to the user
        if event.get("pubkey") != pubkey:
            print(
                "Error: This event was not created by your key. Only the original author can delete an event."
            )
            sys.exit(1)

        print(f"Found event of kind {kind}")

        # Confirm deletion
        confirmation = input(f"\nDelete event {args.event_id}? (y/N): ")
        if confirmation.lower() != "y":
            print("Operation cancelled.")
            sys.exit(0)

        # Create deletion request
        deletion_event = create_deletion_request(args.event_id, kind, args.reason, key)

        # Print event summary
        print("\nDeletion event details:")
        print(f"ID: {deletion_event['id']}")
        print(f"Created at: {deletion_event['created_at']}")
        print(f"Tags: {deletion_event['tags']}")
        if args.reason:
            print(f"Reason: {args.reason}")

        # Publish event
        print(f"\nPublishing deletion request to {args.relay}...")
        if publish_deletion_request(deletion_event, args.relay):
            print("Successfully published deletion request!")

            # Generate nevent code
            try:
                process = subprocess.run(
                    [
                        "nak",
                        "encode",
                        "nevent",
                        "--relay",
                        args.relay,
                        deletion_event["id"],
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                if process.returncode == 0:
                    print(f"Deletion event reference: {process.stdout.strip()}")
            except:
                print(f"Deletion event ID: {deletion_event['id']}")
        else:
            print("Failed to publish deletion request.")
            sys.exit(1)

    except Exception as e:
        print(f"Error processing event: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
