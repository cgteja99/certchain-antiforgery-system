import os
from datetime import datetime, timedelta

from jose import jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "development-secret-change-me"
)

ALGORITHM = "HS256"

TOKEN_EXPIRE_HOURS = TOKEN_EXPIRE_HOURS = 24 * 90

pwd = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def hash_password(password: str) -> str:
    return pwd.hash(password)


def verify_password(
    password: str,
    hashed: str
) -> bool:

    return pwd.verify(
        password,
        hashed
    )


def create_token(
    username: str,
    role: str
):

    payload = {
        "sub": username,
        "role": role,
        "exp": (
            datetime.utcnow()
            + timedelta(
                hours=TOKEN_EXPIRE_HOURS
            )
        )
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )