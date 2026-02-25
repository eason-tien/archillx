import hashlib


def canonicalize_and_hash(content: str) -> str:
    """
    Unified canonicalization rules for evidence hashing.
    Ensures consistent hash generation across different environments (Windows/Linux)
    and input formats (str/bytes).

    Rules:
    1. Input unified to bytes (UTF-8, errors='replace')
    2. Newlines unified to \\n
    3. Trailing newline preserved (no rstrip)
    """
    if content is None:
        return None

    if not isinstance(content, str):
        content = str(content)

    # Rule 2: Normalize line endings
    content = content.replace('\r\n', '\n')

    # Rule 1: Encode to bytes
    content_bytes = content.encode('utf-8', errors='replace')

    # Calculate SHA256
    return hashlib.sha256(content_bytes).hexdigest()
