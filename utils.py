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