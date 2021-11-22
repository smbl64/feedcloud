import base64

import bcrypt


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    hash = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return base64.b64encode(hash).decode("utf-8")


def check_password(plain_text_password: str, hashed_password: str) -> bool:
    hash = base64.b64decode(hashed_password)
    return bcrypt.checkpw(plain_text_password.encode("utf-8"), hash)
