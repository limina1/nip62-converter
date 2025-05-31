# NKBIP-01 Quick Start Guide

This guide will help you quickly publish NKBIP-01 compliant documents to Nostr.

## Prerequisites

1. Install `nak` CLI tool: https://github.com/fiatjaf/nak
2. Have your Nostr private key (nsec) ready
3. Know at least one Nostr relay URL

## Basic Usage

### 1. Prepare Your Document

Create an AsciiDoc file with proper metadata:

```asciidoc
= My Awesome Book
:author: Your Name
:published: 2024-01-22
:tags: fiction, adventure

This is a summary of my book...

== Chapter 1

Chapter content here...

== Chapter 2  

More content...
```

### 2. Upload Your Document

```bash
python nkb_uploader.py \
    --nsec your_private_key \
    --relays wss://relay.damus.io \
    --file my_book.adoc \
    --type book
```

### 3. Validate First (Recommended)

Test without publishing:

```bash
python nkb_uploader.py \
    --nsec your_key \
    --relays wss://relay.damus.io \
    --file my_book.adoc \
    --validate-only
```

## Common Examples

### Academic Paper with DOI

```bash
python nkb_uploader.py \
    --nsec your_key \
    --relays wss://relay.nostr.com \
    --file paper.adoc \
    --type academic \
    --doi 10.1234/example \
    --external
```

### Technical Documentation

```bash
python nkb_uploader.py \
    --nsec your_key \
    --relays wss://relay.nostr.com \
    --file docs.adoc \
    --type documentation
```

### Using Encrypted Key File

```bash
python nkb_uploader.py \
    --nsec /path/to/encrypted.key \
    --relays wss://relay.nostr.com \
    --file book.adoc \
    --type book
```

## Document Structure Tips

1. **Title**: Use single `=` for document title
2. **Sections**: Use `==` for main sections (become separate events)
3. **Subsections**: Use `===` or more (included in parent section)
4. **Metadata**: Add between title and first section
5. **Images**: Use `image::url[]` syntax

## Metadata Reference

| AsciiDoc Attribute | NKBIP-01 Tag | Description |
|-------------------|--------------|-------------|
| `:author:` | `author` | Creator name |
| `:published:` | `published_on` | Date (YYYY-MM-DD) |
| `:publisher:` | `published_by` | Publisher |
| `:tags:` | `t` | Comma-separated topics |
| `:language:` | `l` | Language code (en, es, etc) |
| `:doi:` | `i`, `k` | DOI identifier |
| `:isbn:` | `i`, `k` | ISBN number |

## Verification

After publishing, verify your events:

1. Copy the `nevent` or `naddr` from output
2. Use a Nostr client that supports NKBIP-01
3. Or verify manually:

```bash
# Fetch and decode the event
nak decode nevent1...
```

## Troubleshooting

### "nak not found"
Install from: https://github.com/fiatjaf/nak

### Key decryption fails
- Check file path is correct
- Ensure you're entering the right password

### Relay connection errors
- Verify relay URL includes `wss://`
- Try a different relay
- Check internet connection

### Validation errors
Run with `--validate-only` and check:
- All required metadata present
- Document has proper structure
- No empty sections

## Next Steps

1. Check out example templates in `examples/templates/`
2. Read full documentation in `README_NKBIP01.adoc`
3. Join the discussion at [Nostr community]