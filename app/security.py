"""Password hashing (Python's built-in scrypt - no extra library) and a simple login throttle.
We never store passwords, only a salted hash that can't be turned back into the password."""
import hashlib
import hmac
import os
import time

# scrypt settings: slow on purpose, so guessing passwords is expensive.
_N, _R, _P = 2**14, 8, 1


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        return False
    try:
        _, n, r, p, salt_hex, digest_hex = stored.split("$")
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex),
                                n=int(n), r=int(r), p=int(p), dklen=32)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)  # constant-time comparison


# Used when the email doesn't exist, so "no such user" takes as long as "wrong password".
_DUMMY_HASH = hash_password("not-a-real-password")


def verify_unknown_user(password: str) -> None:
    verify_password(password, _DUMMY_HASH)


# --- Login throttle: 5 failed attempts per email in 15 minutes, then wait. ---
# Kept in memory, so it resets when the app restarts (fine for a prototype).
MAX_FAILURES, WINDOW_SECONDS = 5, 15 * 60
_failures: dict[str, list[float]] = {}


def is_locked_out(email: str) -> bool:
    recent = [t for t in _failures.get(email, []) if time.time() - t < WINDOW_SECONDS]
    _failures[email] = recent
    return len(recent) >= MAX_FAILURES


def record_failure(email: str) -> None:
    _failures.setdefault(email, []).append(time.time())


def clear_failures(email: str | None = None) -> None:
    if email is None:
        _failures.clear()
    else:
        _failures.pop(email, None)
