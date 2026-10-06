from database import SessionLocal
from models import Certificate
import blockchain_utils
import digital_signature


# ==========================================================
# CERTIFICATES TO SYNCHRONIZE
# ==========================================================

CERTIFICATE_IDS = [
    "95649026484",
    "30906103052/RG",
    "0425/2010",
    "204163090011",
    "1402005144",
    "A1465289",
]

# ==========================================================
# DATABASE
# ==========================================================

db = SessionLocal()


try:

    print()
    print("=" * 70)
    print("CERTCHAIN BLOCKCHAIN SYNCHRONIZATION")
    print("=" * 70)
    print()

    for student_id in CERTIFICATE_IDS:

        print("-" * 70)
        print("Certificate ID:", student_id)

        certificate = (
            db.query(Certificate)
            .filter(
                Certificate.student_id == student_id
            )
            .first()
        )

        if certificate is None:

            print("ERROR: Certificate not found in database.")
            continue

        print("Database record:", certificate.id)
        print("Hash:", certificate.certificate_hash)

        # --------------------------------------------------
        # CHECK WHETHER CERTIFICATE ALREADY EXISTS
        # --------------------------------------------------

        existing = (
            blockchain_utils
            .verify_certificate_onchain(
                certificate.certificate_hash
            )
        )

        if existing.get("found"):

            print("Blockchain: ALREADY FOUND")
            print("Skipping this certificate.")
            continue

        print("Blockchain: NOT FOUND")
        print("Registering certificate on current chain...")

        # --------------------------------------------------
        # PREPARE SIGNATURE
        # --------------------------------------------------

        signature = bytes.fromhex(
            certificate.signature_hex
        )

        # --------------------------------------------------
        # ISSUE CERTIFICATE ON CURRENT BLOCKCHAIN
        # --------------------------------------------------

        tx_result = (
            blockchain_utils
            .issue_certificate_onchain(
                certificate.certificate_hash,
                certificate.ipfs_cid,
                signature,
                certificate.student_id_hash,
            )
        )

        print("Transaction:", tx_result["tx_hash"])
        print("Block:", tx_result["block_number"])
        print("Status:", tx_result["status"])

        # --------------------------------------------------
        # VERIFY TRANSACTION
        # --------------------------------------------------

        if tx_result["status"] != "success":

            print(
                "ERROR: Blockchain transaction failed."
            )

            continue

        # --------------------------------------------------
        # UPDATE EXISTING DATABASE RECORD
        # --------------------------------------------------

        certificate.transaction_hash = (
            tx_result["tx_hash"]
        )

        certificate.block_number = (
            tx_result["block_number"]
        )

        db.commit()

        print(
            "Database record updated successfully."
        )

        # --------------------------------------------------
        # VERIFY AGAIN
        # --------------------------------------------------

        verification = (
            blockchain_utils
            .verify_certificate_onchain(
                certificate.certificate_hash
            )
        )

        print(
            "Blockchain verification:",
            verification.get("found")
        )

        if verification.get("found"):

            print(
                "SUCCESS: Certificate is now "
                "registered on the current blockchain."
            )

        else:

            print(
                "WARNING: Certificate could not "
                "be verified after registration."
            )

    print()
    print("=" * 70)
    print("SYNCHRONIZATION COMPLETE")
    print("=" * 70)
    print()


finally:

    db.close()