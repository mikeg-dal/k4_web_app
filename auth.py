import hashlib

# Set your cleartext password here
PASSWORD = "tester"

# Compute SHA-384 hash and encode as ASCII hex string
def get_sha384_hash(password: str) -> bytes:
    sha384 = hashlib.sha384()
    sha384.update(password.encode("utf-8"))
    return sha384.hexdigest().encode("ascii")

AUTH_HASH = get_sha384_hash(PASSWORD)