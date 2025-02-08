from typing import List
import subprocess
import json

def publish_event(event: dict, relays: List[str]) -> bool:
    """Publish an event to specified relays using nak"""
    try:
        print(f"\nDebug: Publishing event {event['id']} to relays: {relays}")
        event_str = json.dumps(event)
        relay_args = ['nak', 'event']
        
        # Add relay arguments
        for relay in relays:
            relay_args.extend(['--relay', relay])
        
        print(f"Debug: Event tags: {json.dumps(event.get('tags', []), indent=2)}")
        print(f"Debug: Publish command: {' '.join(relay_args)}")
        
        # Create and publish the event
        result = subprocess.run(
            relay_args,
            input=event_str.encode(),
            capture_output=True,
            timeout=30  # Longer timeout for publishing
        )
        
        if result.returncode != 0:
            print("Debug: Publishing failed:")
            print(f"Debug: stdout: {result.stdout.decode()}")
            print(f"Debug: stderr: {result.stderr.decode()}")
        else:
            print("Debug: Event published successfully")
        
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("Error: Publishing timed out")
        return False
    except Exception as e:
        print(f"Error publishing event: {e}")
        return False