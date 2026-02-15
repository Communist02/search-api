from argon2.low_level import hash_secret_raw, Type
from hashlib import sha256


def hash_argon2_from_password(password: str) -> bytes:
    password_bytes = password.encode()
    salt = sha256(password_bytes).digest()[3:19]

    hash = hash_secret_raw(
        secret=password_bytes,
        salt=salt,
        time_cost=3,
        memory_cost=64 * 1024,  # 64 MiB
        parallelism=2,
        hash_len=32,
        type=Type.ID
    )
    return hash
