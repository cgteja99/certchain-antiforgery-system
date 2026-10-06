"""
Decentralized storage layer (IPFS).

Two backends are supported, switched via STORAGE_BACKEND in .env:

- "local": talks to a locally-running IPFS daemon (`ipfs daemon`) over its
  HTTP API using the `ipfshttpclient` library.
- "web3storage": uploads via the web3.storage HTTP API using an API token,
  useful when you don't want to run your own IPFS node (e.g. for a demo).

Either way, the function `upload_bytes()` returns the resulting CID, which
is what gets written into the smart contract.
"""
import requests
from config import settings


class IPFSError(Exception):
    pass


def _upload_local(file_bytes: bytes, filename: str) -> str:
    try:
        import ipfshttpclient
    except ImportError as e:
        raise IPFSError(
            "ipfshttpclient not installed. Run: pip install ipfshttpclient"
        ) from e

    try:
        client = ipfshttpclient.connect(settings.IPFS_API_ADDR)
        result = client.add_bytes(file_bytes)
        return result  # CID string
    except Exception as e:
        raise IPFSError(f"Local IPFS upload failed: {e}") from e


def _upload_web3storage(file_bytes: bytes, filename: str) -> str:
    if not settings.WEB3STORAGE_API_TOKEN:
        raise IPFSError("WEB3STORAGE_API_TOKEN not set in .env")

    url = "https://api.web3.storage/upload"
    headers = {"Authorization": f"Bearer {settings.WEB3STORAGE_API_TOKEN}"}
    files = {"file": (filename, file_bytes)}

    resp = requests.post(url, headers=headers, files=files, timeout=60)
    if resp.status_code != 200:
        raise IPFSError(f"web3.storage upload failed: {resp.status_code} {resp.text}")

    data = resp.json()
    return data["cid"]


def upload_bytes(file_bytes: bytes, filename: str = "certificate") -> str:
    """Upload raw bytes to IPFS and return the resulting CID."""
    if settings.STORAGE_BACKEND == "web3storage":
        return _upload_web3storage(file_bytes, filename)
    return _upload_local(file_bytes, filename)


def fetch_bytes(cid: str) -> bytes:
    """Fetch file content back from IPFS by CID, for verification flows."""
    if settings.STORAGE_BACKEND == "web3storage":
        # Public gateway retrieval
        gateway_url = f"https://{cid}.ipfs.w3s.link"
        resp = requests.get(gateway_url, timeout=30)
        if resp.status_code != 200:
            raise IPFSError(f"Failed to fetch {cid} from gateway: {resp.status_code}")
        return resp.content
    else:
        try:
            import ipfshttpclient
        except ImportError as e:
            raise IPFSError("ipfshttpclient not installed") from e
        client = ipfshttpclient.connect(settings.IPFS_API_ADDR)
        return client.cat(cid)
