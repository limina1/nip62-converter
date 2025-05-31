#!/usr/bin/env python3

import sys
import argparse
import json
import os
from typing import Dict, List, Optional
import pprint

from modules.adoc_parser import parse_adoc_file
from modules.tag_utils import (
    clean_tag,
    create_section_tags,
    create_index_tags,
    add_reference_to_index,
)
from modules.event_embedder import create_embedding_event, extract_vector_embedding
from modules.key_utils import read_encrypted_key
from modules.event_creator import create_event, create_a_tag

from modules.event_verifier import verify_event
from modules.event_encoder import encode_event_id
from modules.event_publisher import publish_event
from modules.event_utils import print_event_summary, get_title_from_tags
from modules.nak_utils import nak_decode
from modules.tag_utils import create_reference_tag
import warnings
from nip62_converter import *


def create_traceback_event(link_a_tag, parent_a_tag, primary_relay, key, decrypt=False):
    return create_event(
        30043, "", [link_a_tag, parent_a_tag, ["link-kind", "30041"]], key, decrypt
    )


def create_traceback_events_from_index(index_event, primary_relay, key, decrypt=False):
    events = []
    index_a_tag = create_a_tag(index_event, primary_relay)
    for tag in index_event["tags"]:
        if tag[0] == "a":
            events.append(
                create_traceback_event(tag, index_a_tag, primary_relay, key, decrypt)
            )
    return events


def create_args(
    ncryptsec: str = None,
    relays: List[str] = ["wss://thecitadel.nostr1.com"],
    adoc_file: str = "NostrApps101.adoc",
    author: Optional[str] = "Nostr.Build",
    author_pubkey: Optional[str] = "02d7b3",
):
    class Args:
        pass

    args = Args()
    args.ncryptsec = ncryptsec
    args.relays = relays
    args.adoc_file = adoc_file
    args.author = author
    args.author_pubkey = author_pubkey
    return args


def main():
    decrypt = True
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
    key = read_encrypted_key(args.nsec) if "ncryptsec" in args.nsec else args.nsec
    doc = parse_adoc_file(args.adoc_file)
    organized = organize_sections(doc["title"], doc["sections"])
    all_events = []
    primary_relay = args.relays[0]
    root_references = []
    embedding_events = []
    l1_index = None
    for l1_section in organized:
        section_events = []
        for l2_section in l1_section["l2_sections"]:
            event = create_content_event(
                l2_section["content"],
                l2_section["title"],
                l1_section["title"],
                key,
                args.author,
                decrypt=decrypt,
            )
            section_events.append(
                {
                    "event": event,
                    "title": l2_section["title"],
                    "d_tag": next(tag[1] for tag in event["tags"] if tag[0] == "d"),
                }
            )
            embedding_events.append(create_embedding_event(event, key, primary_relay))
            all_events.append(("Content", event))
            all_events.append(("Embedding", embedding_events[-1]))

        if l1_section["is_root"]:
            root_references.extend(section_events)
    root_title = next(s["title"] for s in organized if s["is_root"])
    root_tags = create_index_tags(root_title)
    image = extract_title_image(args.adoc_file)
    if image:
        root_tags.append(["image", image])
        if args.author:
            root_tags.append(["author", args.author])
            if args.author_pubkey:
                if "npub" in args.author_pubkey:
                    warnings.warn("Author pubkey in npub format, converting to pubkey")
                    args.author_pubkey = nak_decode(args.author_pubkey)["pubkey"]
                root_tags.append(["p", args.author_pubkey])
    for ref in root_references:
        root_tags = add_reference_to_index(
            root_tags, ref["event"], ref["d_tag"], primary_relay
        )

    print("\n=== Root Index Event ===")
    root_index = create_event(30040, "", root_tags, key, decrypt)
    if not verify_event(root_index):
        print("Root index event failed verification")
        sys.exit(1)
    all_events.append(("Root Index", root_index))
    traceback_events = create_traceback_events_from_index(
        root_index, primary_relay, key, decrypt
    )
    for traceback_event in traceback_events:
        all_events.append(("Traceback", traceback_event))
    print("\n=== Events Summary ===")
    for event_type, event in all_events:
        print(f"\n{event_type}:")
        print_event_summary(event)
    if input("\nPublish all events? (y/n): ").lower() != "y":
        print("Publication cancelled.")
        sys.exit(0)

        print(f"\nPublishing events to relays:{', '.join(args.relays)}")
    all_success = True
    for event_type, event in all_events:
        print(f"\nPublishing {event_type} event:")
        delay = 5 if (event_type != "embedding") or (event_type != "traceback") else 10
        if not publish_event(event, args.relays, delay=delay):
            print(f"Failed to publish {event_type} event")
            all_success = False
    if all_success:
        print("\nAll events published successfully!")
        print(f"Total {len(all_events)} events:")
        print(f"{len(section_events)} content events")
        print(f"{len(embedding_events)} embedding events")
        print(f"{len(traceback_events)} traceback events")
        nevent = encode_event_id(root_index, args.relays, note_format=True)
        print(f"\nPublication reference: {nevent}")
        naddr = encode_event_id(root_index, args.relays, note_format=False)
        print(f"Root index reference: {naddr}")
    else:
        print("\nFailed to publish all events")


if __name__ == "__main__":
    main()
