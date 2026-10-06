"""
Digital signature layer.

The issuing institution holds an RSA keypair. When a certificate is issued,
we sign the SHA-256 hash of its canonical content with the institution's
private key (PSS padding). The signature is stored both on-chain (as bytes)
and can be independently re-verified by anyone holding the institution's
public key -- without needing to trust the blockchain node itself.
"""
import os
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.exceptions import InvalidSignature

from config import settings


def generate_keypair_if_missing():
    """Generate an RSA-2048 keypair for the issuing institution if one doesn't exist yet."""
    priv_path = settings.RSA_PRIVATE_KEY_PATH
    pub_path = settings.RSA_PUBLIC_KEY_PATH
    os.makedirs(os.path.dirname(priv_path) or ".", exist_ok=True)

    if os.path.exists(priv_path) and os.path.exists(pub_path):
        return

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    with open(priv_path, "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    with open(pub_path, "wb") as f:
        f.write(
            public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )


def _load_private_key():
    with open(settings.RSA_PRIVATE_KEY_PATH, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def _load_public_key(pem_bytes: bytes = None):
    if pem_bytes is not None:
        return serialization.load_pem_public_key(pem_bytes)
    with open(settings.RSA_PUBLIC_KEY_PATH, "rb") as f:
        return serialization.load_pem_public_key(f.read())


def sign_hash(cert_hash_bytes: bytes) -> bytes:
    """Sign a 32-byte SHA-256 hash with the issuer's RSA private key."""
    private_key = _load_private_key()
    signature = private_key.sign(
        cert_hash_bytes,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )
    return signature


def verify_signature(cert_hash_bytes: bytes, signature: bytes, public_key_pem: bytes = None) -> bool:
    """Verify a signature over a certificate hash using the issuer's public key."""
    public_key = _load_public_key(public_key_pem)
    try:
        public_key.verify(
            signature,
            cert_hash_bytes,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )
        return True
    except InvalidSignature:
        return False


def get_public_key_pem() -> bytes:
    with open(settings.RSA_PUBLIC_KEY_PATH, "rb") as f:
        return f.read()
