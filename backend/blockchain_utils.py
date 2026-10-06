"""
Blockchain interaction layer.

Wraps web3.py calls to the deployed CertificateRegistry contract:
- issuing certificates
- verifying certificates
- revoking certificates
"""

import json
import os

from web3 import Web3
from eth_account import Account

from config import settings


# ==========================================================
# CONTRACT ABI
# ==========================================================

_ABI_PATH = os.path.join(
    os.path.dirname(__file__),
    "contract_abi.json"
)


def _load_abi():
    """
    Load the deployed smart-contract ABI.
    """

    with open(
        _ABI_PATH,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ==========================================================
# WEB3 CONNECTION
# ==========================================================

def get_web3() -> Web3:
    """
    Create and return a Web3 connection.
    """

    w3 = Web3(
        Web3.HTTPProvider(
            settings.WEB3_PROVIDER_URI
        )
    )

    if not w3.is_connected():

        raise ConnectionError(
            "Could not connect to Ethereum node at "
            f"{settings.WEB3_PROVIDER_URI}. "
            "Is `npx hardhat node` running?"
        )

    return w3


# ==========================================================
# SMART CONTRACT
# ==========================================================

def get_contract():
    """
    Return Web3 instance and CertificateRegistry contract.
    """

    w3 = get_web3()

    if not settings.CONTRACT_ADDRESS:

        raise ValueError(
            "CONTRACT_ADDRESS not set in .env — "
            "deploy the contract first."
        )

    abi = _load_abi()

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(
            settings.CONTRACT_ADDRESS
        ),
        abi=abi,
    )

    return w3, contract


# ==========================================================
# HASH NORMALIZATION
# ==========================================================

def _clean_hash(cert_hash_hex: str) -> str:
    """
    Normalize a certificate hash.

    Accepts:
        abc123...
        0xabc123...

    Returns:
        64-character lowercase hexadecimal hash.
    """

    if not cert_hash_hex:

        raise ValueError(
            "Certificate hash cannot be empty."
        )

    clean_hash = (
        cert_hash_hex
        .strip()
        .lower()
        .replace("0x", "")
    )

    if len(clean_hash) != 64:

        raise ValueError(
            "Certificate hash must contain "
            "exactly 64 hexadecimal characters."
        )

    try:

        bytes.fromhex(clean_hash)

    except ValueError:

        raise ValueError(
            "Certificate hash contains invalid "
            "hexadecimal characters."
        )

    return clean_hash


# ==========================================================
# SIGNED TRANSACTION HELPER
# ==========================================================

def _get_raw_transaction(signed_tx):
    """
    Support both old and new eth-account
    SignedTransaction attribute names.
    """

    raw_tx = getattr(
        signed_tx,
        "rawTransaction",
        None
    )

    if raw_tx is None:

        raw_tx = getattr(
            signed_tx,
            "raw_transaction",
            None
        )

    if raw_tx is None:

        raise AttributeError(
            "Could not find raw transaction bytes "
            "in SignedTransaction."
        )

    return raw_tx


# ==========================================================
# ISSUE CERTIFICATE
# ==========================================================

def issue_certificate_onchain(
    cert_hash_hex: str,
    ipfs_cid: str,
    signature: bytes,
    student_id_hash: str,
) -> dict:
    """
    Issue a certificate on the blockchain.
    """

    w3, contract = get_contract()

    account = Account.from_key(
        settings.ISSUER_PRIVATE_KEY
    )

    clean_hash = _clean_hash(
        cert_hash_hex
    )

    cert_hash_bytes32 = bytes.fromhex(
        clean_hash
    )

    nonce = w3.eth.get_transaction_count(
        account.address
    )

    tx = contract.functions.issueCertificate(
        cert_hash_bytes32,
        ipfs_cid,
        signature,
        student_id_hash,
    ).build_transaction(
        {
            "from": account.address,
            "nonce": nonce,
            "chainId": settings.CHAIN_ID,
            "gas": 500000,
            "gasPrice": w3.eth.gas_price,
        }
    )

    signed_tx = account.sign_transaction(
        tx
    )

    raw_tx = _get_raw_transaction(
        signed_tx
    )

    tx_hash = w3.eth.send_raw_transaction(
        raw_tx
    )

    receipt = (
        w3.eth.wait_for_transaction_receipt(
            tx_hash
        )
    )

    return {

        "tx_hash":
            tx_hash.hex(),

        "block_number":
            receipt.blockNumber,

        "status":
            "success"
            if receipt.status == 1
            else "failed",
    }


# ==========================================================
# VERIFY CERTIFICATE ON BLOCKCHAIN
# ==========================================================

def verify_certificate_onchain(
    cert_hash_hex: str
) -> dict:
    """
    Read a certificate record from the blockchain.

    IMPORTANT:
    This function checks the exact hash supplied to it.
    """

    w3, contract = get_contract()

    clean_hash = _clean_hash(
        cert_hash_hex
    )

    cert_hash_bytes32 = bytes.fromhex(
        clean_hash
    )

    result = contract.functions.verifyCertificate(
        cert_hash_bytes32
    ).call()

    (
        found,
        ipfs_cid,
        issuer,
        signature,
        issued_at,
        revoked,
        student_id_hash,
    ) = result

    return {

        "found":
            bool(found),

        "ipfs_cid":
            ipfs_cid,

        "issuer":
            issuer,

        "signature":
            signature.hex()
            if signature
            else None,

        "issued_at":
            issued_at,

        "revoked":
            bool(revoked),

        "student_id_hash":
            student_id_hash,
    }


# ==========================================================
# REVOKE CERTIFICATE
# ==========================================================

def revoke_certificate_onchain(
    cert_hash_hex: str
) -> dict:
    """
    Revoke a certificate on the blockchain.
    """

    w3, contract = get_contract()

    account = Account.from_key(
        settings.ISSUER_PRIVATE_KEY
    )

    clean_hash = _clean_hash(
        cert_hash_hex
    )

    cert_hash_bytes32 = bytes.fromhex(
        clean_hash
    )

    nonce = w3.eth.get_transaction_count(
        account.address
    )

    tx = contract.functions.revokeCertificate(
        cert_hash_bytes32
    ).build_transaction(
        {
            "from": account.address,
            "nonce": nonce,
            "chainId": settings.CHAIN_ID,
            "gas": 200000,
            "gasPrice": w3.eth.gas_price,
        }
    )

    signed_tx = account.sign_transaction(
        tx
    )

    raw_tx = _get_raw_transaction(
        signed_tx
    )

    tx_hash = w3.eth.send_raw_transaction(
        raw_tx
    )

    receipt = (
        w3.eth.wait_for_transaction_receipt(
            tx_hash
        )
    )

    return {

        "tx_hash":
            tx_hash.hex(),

        "status":
            "success"
            if receipt.status == 1
            else "failed",
    }