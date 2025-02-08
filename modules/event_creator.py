from typing import List, Dict, Tuple
import subprocess
import sys
import json
import getpass
import time

def decrypt_key(encrypted_key: str) -> str:
    """Decrypt an encrypted key using nak"""
    try:
        password = getpass.getpass("Enter password to decrypt key: ")
        
        # Pass encrypted key as argument, password through stdin
        decrypt_process = subprocess.run(
            ['nak', 'key', 'decrypt', encrypted_key],
            input=password.encode('utf-8'),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        if decrypt_process.returncode != 0:
            print(f"Debug: Decryption failed:")
            print(f"Debug: stdout: {decrypt_process.stdout.decode()}")
            print(f"Debug: stderr: {decrypt_process.stderr.decode()}")
            raise Exception("Failed to decrypt key")
            
        # Get the decrypted private key
        privkey = decrypt_process.stdout.decode().strip()
        
        # Verify by getting the pubkey
        pubkey_process = subprocess.run(
            ['nak', 'key', 'public'],
            input=privkey.encode('utf-8'),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        if pubkey_process.returncode == 0:
            print(f"Debug: Using pubkey: {pubkey_process.stdout.decode().strip()}")
        
        return privkey
        
    except Exception as e:
        print(f"Error decrypting key: {e}")
        sys.exit(1)

# Global decrypted key cache
_DECRYPTED_KEY = None

def create_event(kind: int, content: str, tags: List[List[str]], ncryptsec: str) -> dict:
    """Create and sign a Nostr event using nak"""
    try:
        global _DECRYPTED_KEY
        
        # Get or decrypt the key
        if _DECRYPTED_KEY is None:
            # Read the encrypted key if it's a file path
            if ncryptsec.startswith('/'):
                with open(ncryptsec, 'r') as f:
                    ncryptsec = f.read().strip()
            
            _DECRYPTED_KEY = decrypt_key(ncryptsec)

        # Create the complete event
        event = {
            "kind": kind,
            "content": content,
            "tags": tags,
            "created_at": int(time.time())
        }
        
        # Convert to JSON - ensure no extra newlines
        event_json = json.dumps(event, separators=(',', ':'))
            
        # Debug output
        print(f"Debug: Creating event with kind {kind}")
        print(f"Debug: Tags: {json.dumps(tags, indent=2)}")
        print(f"Debug: Event JSON: {event_json}")
        
        # Create the event with decrypted key
        cmd = ['nak', 'event', '--sec', _DECRYPTED_KEY]
        
        # Send event JSON through stdin
        process = subprocess.run(
            cmd,
            input=event_json.encode('utf-8'),
            capture_output=True
        )
        
        if process.returncode != 0:
            print("Debug: Event creation failed:")
            print(f"Debug: stdout: {process.stdout.decode()}")
            print(f"Debug: stderr: {process.stderr.decode()}")
            raise Exception(f"Command failed: {process.stderr.decode()}")
        
        result_event = json.loads(process.stdout.decode())
        print(f"Debug: Event created successfully with ID: {result_event['id']}")
        print(f"Debug: Event tags: {json.dumps(result_event['tags'], indent=2)}")
        return result_event
        
    except subprocess.TimeoutExpired:
        print("Error: Command timed out")
        sys.exit(1)
    except Exception as e:
        print(f"Error creating event: {e}")
        sys.exit(1)