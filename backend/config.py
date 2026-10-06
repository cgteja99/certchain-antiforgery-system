import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Blockchain
    WEB3_PROVIDER_URI = os.getenv("WEB3_PROVIDER_URI", "http://127.0.0.1:8545")
    CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "")
    ISSUER_PRIVATE_KEY = os.getenv("ISSUER_PRIVATE_KEY", "")
    CHAIN_ID = int(os.getenv("CHAIN_ID", "31337"))

    # IPFS
    STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")  # "local" or "web3storage"
    IPFS_API_ADDR = os.getenv("IPFS_API_ADDR", "/ip4/127.0.0.1/tcp/5001")
    WEB3STORAGE_API_TOKEN = os.getenv("WEB3STORAGE_API_TOKEN", "")

    # Digital signature
    RSA_PRIVATE_KEY_PATH = os.getenv("RSA_PRIVATE_KEY_PATH", "keys/issuer_private_key.pem")
    RSA_PUBLIC_KEY_PATH = os.getenv("RSA_PUBLIC_KEY_PATH", "keys/issuer_public_key.pem")

    # Forgery detection
    ELA_QUALITY = int(os.getenv("ELA_QUALITY", "90"))
    FORGERY_SCORE_THRESHOLD = float(os.getenv("FORGERY_SCORE_THRESHOLD", "0.35"))


settings = Settings()
