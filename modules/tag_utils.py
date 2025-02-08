import re
from typing import List


def clean_tag(text: str) -> str:
    """Clean text for use in tags"""
    # Remove special characters and convert to lowercase
    cleaned = re.sub(r"[^\w\s-]", "", text.lower())
    # Replace spaces with hyphens and remove multiple hyphens
    cleaned = re.sub(r"[-\s]+", "-", cleaned)
    return cleaned.strip("-")


def create_standard_tag(tag_type: str, value: str) -> List[str]:
    """Create a standard tag with type and value"""
    return [tag_type, value]


def create_reference_tag(
    kind: int, pubkey: str, d_tag: str, event_id: str, relay_hint: str = ""
) -> List[str]:
    """Create an 'a' tag following NIP-62 format
    Format: ["a", "kind:pubkey:dtag", "<relay hint>", "<event id>"]
    """
    # Create the reference string without the dtag prefix
    ref = f"{kind}:{pubkey}:{d_tag}"
    return ["a", ref, relay_hint, event_id]


def create_section_tags(
    doc_title: str, section_title: str, doc_author: str = None
) -> List[List[str]]:
    """Create tags for a section event following NIP-62 format"""
    d_tag = f"{clean_tag(doc_title)}-{clean_tag(section_title)}"

    return [["d", d_tag], ["title", section_title]]


def create_index_tags(
    doc_title: str, auto_update: str = "yes", doc_author: str = None
) -> List[List[str]]:
    """Create initial tags for an index event"""
    if doc_author:
        return [
            ["d", clean_tag(doc_title)],
            ["title", doc_title],
            ["auto-update", auto_update],
            ["author", doc_author],
        ]
    return [
        ["d", clean_tag(doc_title)],
        ["title", doc_title],
        ["auto-update", auto_update],
    ]


def add_reference_to_index(
    index_tags: List[List[str]], section_event: dict, d_tag: str, relay: str
) -> List[List[str]]:
    """Add a section reference to index tags
    Following NIP-62 format for 'a' tags
    """
    ref_tag = create_reference_tag(
        kind=section_event["kind"],
        pubkey=section_event["pubkey"],
        d_tag=d_tag,  # Use clean d_tag without prefix
        event_id=section_event["id"],
        relay_hint=relay,
    )
    index_tags.append(ref_tag)
    return index_tags
