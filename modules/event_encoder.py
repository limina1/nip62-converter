import subprocess

def encode_event_id(event_id: str) -> str:
    """Encode an event ID to nevent format using nak"""
    try:
        print(f"\nDebug: Encoding event ID: {event_id}")
        result = subprocess.run(
            ['nak', 'encode', 'note', event_id],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10
        )
        if result.returncode != 0:
            print("Debug: Encoding failed:")
            print(f"Debug: stderr: {result.stderr.decode()}")
            raise Exception(f"Failed to encode event: {result.stderr.decode()}")
        
        encoded = result.stdout.decode().strip()
        print(f"Debug: Encoded successfully: {encoded}")
        return encoded
    except subprocess.TimeoutExpired:
        print("Error: Encoding timed out")
        return event_id
    except Exception as e:
        print(f"Error encoding event: {e}")
        return event_id