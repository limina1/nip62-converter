#!/usr/bin/env python3

import sys
import re

def convert_md_to_adoc(md_text: str) -> str:
    """Convert markdown to AsciiDoc format"""
    # Convert headers
    text = re.sub(r'^# (.*)', r'= \1', md_text, flags=re.MULTILINE)
    text = re.sub(r'^## (.*)', r'== \1', text, flags=re.MULTILINE)
    text = re.sub(r'^### (.*)', r'=== \1', text, flags=re.MULTILINE)
    
    # Convert code blocks with language
    text = re.sub(r'```(\w+)\n(.*?)\n```', r'[source,\1]\n----\n\2\n----', text, flags=re.MULTILINE | re.DOTALL)
    
    # Convert code blocks without language
    text = re.sub(r'```\n(.*?)\n```', r'----\n\1\n----', text, flags=re.MULTILINE | re.DOTALL)
    
    # Convert inline code
    text = re.sub(r'`([^`]+)`', r'`\1`', text)
    
    # Convert links
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'\1 <\2>', text)
    
    # Convert emphasis
    text = re.sub(r'\*\*([^\*]+)\*\*', r'*\1*', text)  # bold to strong
    text = re.sub(r'_([^_]+)_', r'_\1_', text)  # italic remains italic
    
    return text

def main():
    # Read the README.md
    with open('nak-help/README.md', 'r') as f:
        readme_content = f.read()
    
    # Convert README to AsciiDoc
    readme_adoc = convert_md_to_adoc(readme_content)
    
    # Read the current nak.adoc
    with open('nak-adoc-help/nak.adoc', 'r') as f:
        adoc_lines = f.readlines()
    
    # Find where the actual content starts (after the metadata)
    content_start = 0
    for i, line in enumerate(adoc_lines):
        if line.startswith('= '):
            content_start = i
            break
    
    # Create new content with README as first section
    new_content = ''.join(adoc_lines[:content_start])  # Metadata
    new_content += '= NAK: The Nostr Army Knife\n\n'  # Main title
    new_content += '== NAK README\n\n'  # README section
    new_content += readme_adoc + '\n\n'  # README content
    new_content += '== Documentation\n\n'  # Original content section
    new_content += ''.join(adoc_lines[content_start+1:])  # Rest of original content
    
    # Write the new content
    with open('nak-adoc-help/nak.adoc', 'w') as f:
        f.write(new_content)

if __name__ == "__main__":
    main()