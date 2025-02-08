from typing import List, Dict

def print_event_summary(event: dict) -> None:
    """Print a readable summary of an event"""
    print("\nEvent Summary:")
    print(f"  ID: {event['id']}")
    print(f"  Kind: {event['kind']}")
    print(f"  Tags:")
    for tag in event['tags']:
        print(f"    - {':'.join(tag)}")
    if event.get('content'):
        print(f"  Content preview: {event['content'][:100]}..." if len(event['content']) > 100 else f"  Content: {event['content']}")
    print("  ---")

def get_title_from_tags(tags: List[List[str]]) -> str:
    """Extract title from event tags"""
    if not tags:
        return "Untitled"
    
    title_tags = [tag[1] for tag in tags if tag[0] == 'title']
    if title_tags:
        return title_tags[0]
    else:
        d_tags = [tag[1] for tag in tags if tag[0] == 'd']
        if d_tags:
            # Convert d-tag back to readable title
            return d_tags[0].replace('-', ' ').title()
    
    return "Untitled"