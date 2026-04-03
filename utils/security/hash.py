from hashlib import sha256, sha1
from typing import Literal

import argon2


def make_pass(password: str) -> str:
    ph = argon2.PasswordHasher()
    return ph.hash(password)


def check_pass(password: str, hashed_password: str) -> bool:
    ph = argon2.PasswordHasher()
    try:
        ph.verify(hashed_password, password)
        return True
    except argon2.exceptions.VerifyMismatchError:
        return False


def fnv1a_hash(text, bits: Literal[32, 64] = 32) -> str:
    if bits == 32:
        fnv_prime = 0x01000193
        offset_basis = 0x811c9dc5
        mask = 0xFFFFFFFF
    elif bits == 64:
        fnv_prime = 0x100000001b3
        offset_basis = 0xcbf29ce484222325
        mask = 0xFFFFFFFFFFFFFFFF
    else:
        raise ValueError("bits must be 32 or 64")

    hash_value = offset_basis
    for char in text:
        hash_value ^= ord(char)
        hash_value = (hash_value * fnv_prime) & mask

    return f"{hash_value:0{bits // 4}x}"


def sha256hash(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def sha1hash(text: str) -> str:
    return sha1(text.encode("utf-8")).hexdigest()
