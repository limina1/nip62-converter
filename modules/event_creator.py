from typing import List, Dict, Tuple
import subprocess
import sys
import json
import getpass

# Global password cache
_PASSWORD = None

def create_event(kind: int, content: str, tags: List[List[str]], ncryptsec: str) -> dict:
    """Create and sign a Nostr event using nak"""
    try:
        global _PASSWORD
        
        # Get password if not cached
        if _PASSWORD is None:
            _PASSWORD = getpass.getpass("Enter password for key: ")

        # Create a process that we can interact with
        process = subprocess.Popen(
            ['nak', 'event', '--sec', ncryptsec, '--kind', str(kind)] +
            sum([['--tag', ':'.join(tag)] for tag in tags], []) +
            (['--content', content] if content else []),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Send password and get output
        stdout, stderr = process.communicate(input=_PASSWORD)
        
        if process.returncode != 0:
            print("Debug: Command failed with output:")
            print(f"Debug: stdout: {stdout}")
            print(f"Debug: stderr: {stderr}")
            
            # If password seems wrong, clear it and try once more
            if "failed to decrypt" in stdout or "EOF" in stdout:
                print("Debug: Password might be wrong, trying again...")
                _PASSWORD = None
                return create_event(kind, content, tags, ncryptsec)
                
            raise Exception(f"Command failed: {stderr}")
        
        event = json.loads(stdout)
        print(f"Debug: Event created successfully with ID: {event['id']}")
        return event
        
    except subprocess.TimeoutExpired:
        print("Error: Command timed out")
        sys.exit(1)
    except Exception as e:
        print(f"Error creating event: {e}")
        sys.exit(1)