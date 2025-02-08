import re

def clean_tag(text: str) -> str:
    """Clean text for use in tags"""
    # Remove special characters and convert to lowercase
    cleaned = re.sub(r'[^\w\s-]', '', text.lower())
    # Replace spaces with hyphens and remove multiple hyphens
    cleaned = re.sub(r'[-\s]+', '-', cleaned)
    return cleaned.strip('-')