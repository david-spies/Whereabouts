import secrets
import hmac
import hashlib

def generate_secure_token() -> str:
    """Generates cryptographically secure internal job execution tokens."""
    return secrets.token_urlsafe(32)

def verify_file_integrity(file_bytes: bytes, expected_hash: str) -> bool:
    """Validates incoming binary arrays against pre-computed SHA-256 integrity checksums."""
    computed_hash = hashlib.sha256(file_bytes).hexdigest()
    return hmac.compare_digest(computed_hash, expected_hash)
