"""
FastAPI backend for the Blockchain-Based Anti-Forgery System
for Academic Certificates.

Verification pipeline:

1. Receive certificate image + certificate_id.
2. Find the trusted reference certificate.
3. Run:
   - ELA detection
   - Image alignment
   - Student-name detection
   - Signature detection
   - Seal detection
   - Register-number detection when configured
4. Compute SHA-256 hash.
5. Look up trusted certificate on blockchain.
6. Verify the trusted blockchain record.
7. Check revoked status.
8. Return combined final verdict.

IMPORTANT:
A SHA-256 mismatch by itself does NOT mean that the visible
certificate is forged. JPEG recompression, resizing, metadata
changes, or re-saving can change the file hash.

When a trusted reference image is available, structured
certificate comparison is used as the primary visual/content
decision. The blockchain hash remains important for proving
exact-file identity, but it is not used by itself to label a
visually matching certificate as forged.
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import (
    FastAPI,
    Response,
    File,
    UploadFile,
    Form,
    HTTPException,
    Depends,
    Request
)

from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from sqlalchemy.orm import Session

from pydantic import BaseModel

from database import get_db
from database import SessionLocal

from models import (
    Certificate,
    User,
    Institution,
    Student,
    AuditLog
)

from auth import (
    verify_password,
    create_token,
    SECRET_KEY,
    ALGORITHM
)

oauth2_scheme = HTTPBearer()


# ==========================================================
# EXISTING PROJECT MODULES
# ==========================================================

import digital_signature
import forgery_detection
import ipfs_storage
import blockchain_utils

from config import settings


# ==========================================================
# REFERENCE MANAGER
# ==========================================================

from detection.reference_manager import (
    get_reference_image as dynamic_get_reference_image,
    save_reference_image,
    save_reference
)


# ==========================================================
# FASTAPI APP
# ==========================================================

app = FastAPI(
    title=(
        "CertChain — Blockchain Anti-Forgery "
        "System for Academic Certificates"
    ),
    description=(
        "AI forgery detection + digital signatures "
        "+ decentralized storage + blockchain verification"
    ),
    version="1.0.0",
)


# ==========================================================
# VERIFICATION ACTIVITY LOG
# ==========================================================

VERIFICATION_LOG_FILE = os.path.join(
    os.path.dirname(__file__),
    "verification_activity.json"
)


def _append_verification_event(data):
    """Store one completed verification event locally."""

    try:
        events = []

        if os.path.exists(VERIFICATION_LOG_FILE):
            try:
                with open(
                    VERIFICATION_LOG_FILE,
                    "r",
                    encoding="utf-8"
                ) as f:
                    events = json.load(f)
            except Exception:
                events = []

        events.append(data)

        with open(
            VERIFICATION_LOG_FILE,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                events[-1000:],
                f,
                indent=2
            )

    except Exception as e:
        print("Verification audit log error:", repr(e))


def _verification_category(data):
    verdict = str(
        data.get("overall_verdict", "")
    ).upper()

    forgery = data.get(
        "forgery_check",
        {}
    ) or {}

    if verdict.startswith("WRONG DETAILS"):
        return "wrong_details"

    if (
        data.get("revoked") is True
        or verdict.startswith("REVOKED")
    ):
        return "revoked"

    if (
        forgery.get("structured_tampering") is True
        or "FORGED / ALTERED" in verdict
    ):
        return "forged"

    if (
        verdict.startswith("VALID")
        or verdict.startswith("LIKELY GENUINE")
        or verdict.startswith("VISUALLY VERIFIED")
    ):
        return "authentic"

    return "invalid"


def _tampered_components(forgery):
    components = []

    def is_tampered(value):
        return (
            isinstance(value, dict)
            and str(value.get("status", "")).upper()
            == "TAMPERED"
        )

    if is_tampered(forgery.get("student_name")):
        components.append("Student Name")

    if is_tampered(forgery.get("register_number")):
        components.append("Register Number")

    if is_tampered(forgery.get("seal")):
        components.append("Seal")

    signature = forgery.get("signature") or {}

    if is_tampered(signature):
        components.append("Signature")
    else:
        signatures = signature.get("signatures", [])
        if isinstance(signatures, list):
            if any(is_tampered(item) for item in signatures):
                components.append("Signature")

    return components


@app.middleware("http")
async def verification_activity_middleware(request, call_next):
    response = await call_next(request)

    if (
        request.url.path == "/verify"
        and response.status_code == 200
    ):
        body = b""

        async for chunk in response.body_iterator:
            body += chunk

        try:
            data = json.loads(
                body.decode("utf-8")
            )

            forgery = data.get(
                "forgery_check",
                {}
            ) or {}

            event = {
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
                "category": _verification_category(data),
                "verdict": data.get(
                    "overall_verdict",
                    "UNKNOWN"
                ),
                "components": _tampered_components(
                    forgery
                )
            }

            _append_verification_event(event)

        except Exception as e:
            print(
                "Verification response logging error:",
                repr(e)
            )

        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type
        )

    return response


# ==========================================================
# CORS
# ==========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================================
# STARTUP
# ==========================================================

digital_signature.generate_keypair_if_missing()

forgery_detection.load_cnn_model()


# ==========================================================
# HELPER FUNCTIONS
# ==========================================================

def sha256_hex(data: bytes) -> str:
    """Calculate SHA-256 hash of certificate bytes."""

    return hashlib.sha256(
        data
    ).hexdigest()


def hash_student_id(student_id: str) -> str:
    """Hash student identifier before blockchain/IPFS metadata."""

    return hashlib.sha256(
        student_id.encode("utf-8")
    ).hexdigest()


# ==========================================================
# RESPONSE MODEL
# ==========================================================

class LoginRequest(BaseModel):

    username: str
    password: str


class VerifyResult(BaseModel):

    forgery_check: dict

    hash_found_onchain: bool

    signature_valid: Optional[bool] = None

    revoked: Optional[bool] = None

    issuer: Optional[str] = None

    ipfs_cid: Optional[str] = None

    issued_at: Optional[int] = None

    overall_verdict: str


# ==========================================================
# ROOT
# ==========================================================

@app.get("/")
def root():

    return {
        "service": (
            "CertChain Anti-Forgery API"
        ),

        "endpoints": [
            "/issue",
            "/verify",
            "/certificate/{cert_hash}",
            "/public-key",
            "/health"
        ]
    }


# ==========================================================
# HEALTH CHECK
# ==========================================================

@app.get("/health")
def health():

    checks = {}

    try:

        w3 = blockchain_utils.get_web3()

        checks["blockchain"] = (
            "connected"
            if w3.is_connected()
            else "unreachable"
        )

    except Exception as e:

        checks["blockchain"] = (
            f"error: {e}"
        )

    checks["storage_backend"] = (
        settings.STORAGE_BACKEND
    )

    return checks


# ==========================================================
# PUBLIC KEY
# ==========================================================

@app.get("/public-key")
def public_key():

    return {
        "public_key_pem":
            digital_signature
            .get_public_key_pem()
            .decode()
    }


# ==========================================================
# AUDIT LOG HELPER
# ==========================================================

def record_audit_log(
    db: Session,
    user_id: Optional[int],
    action: str,
    description: str,
    ip_address: Optional[str] = None
):
    try:
        log = AuditLog(
            user_id=user_id,
            action=action,
            description=description,
            ip_address=ip_address
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        print("Audit log write failed:", e)


# ==========================================================
# LOGIN
# ==========================================================

@app.post("/login")
async def login(
    data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):

    user = (
        db.query(User)
        .filter(
            User.username == data.username
        )
        .first()
    )

    if not user:

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    if not verify_password(
        data.password,
        user.password_hash
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    if not user.is_active:

        raise HTTPException(
            status_code=403,
            detail="User account is disabled"
        )

    token = create_token(
        user.username,
        user.role
    )

    record_audit_log(
        db,
        user.id,
        "LOGIN",
        f"Successful login for {user.username} ({user.role})",
        request.client.host if request.client else None
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user.username,
        "role": user.role
    }


# ==========================================================
# CURRENT USER
# ==========================================================

@app.get("/me")
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        oauth2_scheme
    ),
    db: Session = Depends(get_db)
):

    token = credentials.credentials

    from jose import JWTError, jwt

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        username = payload.get("sub")

        if not username:

            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

    except JWTError:

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    user = (
        db.query(User)
        .filter(
            User.username == username
        )
        .first()
    )

    if not user:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return {
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active
    }


# ==========================================================
# ADMIN DASHBOARD
# ==========================================================

@app.get("/admin/dashboard")
async def admin_dashboard(
    credentials: HTTPAuthorizationCredentials = Depends(
        oauth2_scheme
    ),
    db: Session = Depends(get_db)
):

    token = credentials.credentials

    from jose import JWTError, jwt

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        username = payload.get("sub")
        role = payload.get("role")

        if not username:

            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

    except JWTError:

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    if role != "admin":

        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    total_users = (
        db.query(User)
        .count()
    )

    active_users = (
        db.query(User)
        .filter(
            User.is_active == True
        )
        .count()
    )

    total_students = (
        db.query(Student)
        .count()
    )

    total_institutions = (
        db.query(Institution)
        .count()
    )

    total_audit_logs = (
        db.query(AuditLog)
        .count()
    )

    return {

        "admin": username,

        "role": role,

        "statistics": {

            "total_users":
                total_users,

            "active_users":
                active_users,

            "total_students":
                total_students,

            "total_institutions":
                total_institutions,

            "total_audit_logs":
                total_audit_logs
        }
    }


# ==========================================================
# ADMIN AUDIT LOGS
# ==========================================================

@app.get("/admin/audit-logs")
async def admin_audit_logs(
    credentials: HTTPAuthorizationCredentials = Depends(
        oauth2_scheme
    ),
    db: Session = Depends(get_db)
):
    token = credentials.credentials

    from jose import JWTError, jwt

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        username = payload.get("sub")

        if not username:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    current_user = (
        db.query(User)
        .filter(User.username == username)
        .first()
    )

    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    logs = (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(100)
        .all()
    )

    result = []

    for log in logs:
        user = None

        if log.user_id is not None:
            user = (
                db.query(User)
                .filter(User.id == log.user_id)
                .first()
            )

        result.append({
            "id": log.id,
            "username": user.username if user else "System",
            "user_id": log.user_id,
            "action": log.action,
            "description": log.description,
            "ip_address": log.ip_address,
            "created_at": (
                log.created_at.isoformat()
                if log.created_at
                else None
            )
        })

    return result


# ==========================================================
# VERIFICATION & FORGERY ANALYTICS - ADMIN
# ==========================================================

@app.get("/admin/verification-analytics")
async def verification_analytics(
    credentials: HTTPAuthorizationCredentials = Depends(
        oauth2_scheme
    ),
    db: Session = Depends(get_db)
):

    token = credentials.credentials

    from jose import JWTError, jwt

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        username = payload.get("sub")

        if not username:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    current_user = (
        db.query(User)
        .filter(User.username == username)
        .first()
    )

    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    events = []

    if os.path.exists(VERIFICATION_LOG_FILE):
        try:
            with open(
                VERIFICATION_LOG_FILE,
                "r",
                encoding="utf-8"
            ) as f:
                events = json.load(f)
        except Exception:
            events = []

    counts = {
        "total": len(events),
        "authentic": 0,
        "forged": 0,
        "wrong_details": 0,
        "revoked": 0,
        "invalid": 0,
        "student_name_tampered": 0,
        "signature_tampered": 0,
        "seal_tampered": 0,
        "register_number_tampered": 0
    }

    for event in events:
        category = event.get(
            "category",
            "invalid"
        )

        if category in counts:
            counts[category] += 1

        components = event.get(
            "components",
            []
        ) or []

        if "Student Name" in components:
            counts["student_name_tampered"] += 1

        if "Signature" in components:
            counts["signature_tampered"] += 1

        if "Seal" in components:
            counts["seal_tampered"] += 1

        if "Register Number" in components:
            counts["register_number_tampered"] += 1

    return {
        "statistics": counts,
        "recent": events[-10:][::-1]
    }


# ==========================================================
# GET ALL CERTIFICATES - ADMIN
# ==========================================================

@app.get("/admin/certificates")
async def get_all_certificates(
    credentials: HTTPAuthorizationCredentials = Depends(
        oauth2_scheme
    ),
    db: Session = Depends(get_db)
):

    token = credentials.credentials

    from jose import JWTError, jwt

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        username = payload.get("sub")
        role = payload.get("role")

        if not username:

            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

    except JWTError:

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    if role != "admin":

        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    certificates = (
        db.query(Certificate)
        .order_by(Certificate.id.desc())
        .all()
    )

    return [
        {
            "id": cert.id,
            "student_id": cert.student_id,
            "student_name": cert.student_name,
            "course": cert.course,
            "certificate_hash": cert.certificate_hash,
            "ipfs_cid": cert.ipfs_cid,
            "transaction_hash": cert.transaction_hash,
            "block_number": cert.block_number,
            "student_id_hash": cert.student_id_hash,
            "revoked": cert.revoked,
            "created_at": (
                cert.created_at.isoformat()
                if cert.created_at
                else None
            )
        }
        for cert in certificates
    ]


# ==========================================================
# REVOKE CERTIFICATE - ADMIN
# ==========================================================

@app.post("/revoke/{cert_hash}")
async def revoke_certificate(
    cert_hash: str,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(
        oauth2_scheme
    ),
    db: Session = Depends(get_db)
):

    token = credentials.credentials

    from jose import JWTError, jwt

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        username = payload.get("sub")
        role = payload.get("role")

        if not username:

            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

    except JWTError:

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    if role != "admin":

        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    clean_hash = cert_hash.replace(
        "0x",
        ""
    ).strip()

    if len(clean_hash) != 64:

        raise HTTPException(
            status_code=400,
            detail="Invalid certificate hash."
        )

    certificate = (
        db.query(Certificate)
        .filter(
            Certificate.certificate_hash
            == "0x" + clean_hash
        )
        .first()
    )

    if certificate is None:

        raise HTTPException(
            status_code=404,
            detail="Certificate not found in database."
        )

    if certificate.revoked:

        return {
            "message":
                "Certificate is already revoked.",

            "certificate_hash":
                certificate.certificate_hash,

            "revoked":
                True
        }

    try:

        tx_result = (
            blockchain_utils
            .revoke_certificate_onchain(
                clean_hash
            )
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                "Blockchain revocation failed: "
                + str(e)
            )
        )

    certificate.revoked = True

    db.commit()
    db.refresh(certificate)

    audit_user = (
        db.query(User)
        .filter(User.username == username)
        .first()
    )
    record_audit_log(
        db,
        audit_user.id if audit_user else None,
        "CERTIFICATE_REVOKED",
        f"Certificate {certificate.id} ({certificate.student_id}) revoked",
        request.client.host if request.client else None
    )

    return {
        "message":
            "Certificate revoked successfully.",

        "certificate_hash":
            certificate.certificate_hash,

        "revoked":
            True,

        "transaction":
            tx_result
    }


# ==========================================================
# ISSUE CERTIFICATE
# ==========================================================

@app.post("/issue")
async def issue_certificate(
    file: UploadFile = File(...),
    student_id: str = Form(...),
    student_name: str = Form(...),
    course: str = Form(...),
):

    file_bytes = await file.read()

    if not file_bytes:

        raise HTTPException(
            status_code=400,
            detail="Uploaded certificate is empty."
        )

    forgery_result = (
        forgery_detection.analyze_image(
            file_bytes
        )
    )

    if forgery_result.get(
        "structured_tampering",
        False
    ):

        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    "Source file failed structured "
                    "forgery pre-check — refusing to issue."
                ),
                "forgery_check":
                    forgery_result,
            },
        )

    cert_hash_hex = sha256_hex(
        file_bytes
    )

    cert_hash_bytes = bytes.fromhex(
        cert_hash_hex
    )

    certificate_hash = (
        "0x" + cert_hash_hex
    )

    signature = digital_signature.sign_hash(
        cert_hash_bytes
    )

    cid = ipfs_storage.upload_bytes(
        file_bytes,
        filename=file.filename or "certificate"
    )

    student_id_hash = hash_student_id(
        student_id
    )

    try:

        tx_result = (
            blockchain_utils
            .issue_certificate_onchain(
                cert_hash_hex,
                cid,
                signature,
                student_id_hash
            )
        )

    except Exception as e:

        error_message = str(e)

        if (
            "Certificate already registered"
            in error_message
        ):

            raise HTTPException(
                status_code=409,
                detail=(
                    "Certificate already registered "
                    "on blockchain."
                )
            )

        raise HTTPException(
            status_code=500,
            detail=(
                "Blockchain issuance failed: "
                + error_message
            )
        )

    db = SessionLocal()

    try:

        certificate = (
            db.query(Certificate)
            .filter(
                Certificate.certificate_hash
                == certificate_hash
            )
            .first()
        )

        if certificate is None:

            certificate = Certificate(

                student_id=student_id,

                student_name=student_name,

                course=course,

                certificate_hash=
                    certificate_hash,

                ipfs_cid=cid,

                transaction_hash=
                    tx_result.get("tx_hash"),

                block_number=
                    tx_result.get("block_number"),

                signature_hex=
                    signature.hex(),

                student_id_hash=
                    student_id_hash,

                revoked=False
            )

            db.add(certificate)

        else:

            certificate.student_id = student_id

            certificate.student_name = student_name

            certificate.course = course

            certificate.ipfs_cid = cid

            certificate.transaction_hash = (
                tx_result.get("tx_hash")
            )

            certificate.block_number = (
                tx_result.get("block_number")
            )

            certificate.signature_hex = (
                signature.hex()
            )

            certificate.student_id_hash = (
                student_id_hash
            )

            certificate.revoked = False

        db.commit()
        db.refresh(certificate)

    finally:

        db.close()

    # ------------------------------------------------------
    # SAVE TRUSTED REFERENCE AUTOMATICALLY
    # ------------------------------------------------------
    # The exact uploaded bytes become the trusted visual
    # reference for this newly issued certificate.
    # Existing C1-C9 mappings remain as fallback.
    try:
        reference_path = save_reference_image(
            student_id,
            file_bytes,
            file.filename or "certificate.jpeg"
        )

        save_reference(
            certificate_hash,
            {
                "certificate_id": student_id,
                "student_name": student_name,
                "course": course,
                "reference_image": reference_path.name,
                "certificate_hash": certificate_hash,
                "ipfs_cid": cid,
            }
        )

        print(
            "TRUSTED REFERENCE SAVED:",
            student_id,
            reference_path
        )

    except Exception as e:
        print(
            "Trusted reference save failed:",
            repr(e)
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "Certificate was issued, but the trusted "
                "reference image could not be saved: "
                + str(e)
            )
        )

    return {

        "message":
            "Certificate issued and anchored on-chain",

        "certificate_hash":
            certificate_hash,

        "ipfs_cid":
            cid,

        "signature_hex":
            signature.hex(),

        "transaction":
            tx_result,

        "forgery_check":
            forgery_result,

        "student_name":
            student_name,

        "course":
            course,
    }


# ==========================================================
# CERTIFICATE REFERENCE MAP
# ==========================================================

CERTIFICATE_REFERENCE_MAP = {

    "A1465289":
        "c1.jpeg",

    "S150173796":
        "c2.jpeg",

    "1PE10EC038":
        "c3.jpeg",

    "MITU18DSME0016":
        "c4.jpeg",

    "95649026484":
        "c5.jpeg",

    "30906103052/RG":
        "c6.jpeg",

    "0425/2010":
        "c7.jpeg",

    "204163090011":
        "c8.jpeg",

    "1402005144":
        "c9.jpeg",
}


REFERENCE_DIR = os.path.join(

    os.path.dirname(__file__),

    "reference_data",

    "certificates"
)


def get_reference_image(
    certificate_id: str
):
    return dynamic_get_reference_image(certificate_id)


# ==========================================================
# WRONG CERTIFICATE ID / IMAGE CHECK
# ==========================================================

def _detect_wrong_certificate(
    certificate_id: str,
    file_bytes: bytes,
    reference_path: str,
    uploaded_filename: str = ""
):
    """
    Detect a certificate image that clearly belongs to a
    different known certificate.

    Two safe checks are used:
    1. Exact SHA-256 match against another trusted reference.
    2. Known cN/tN filename identity when the uploaded file
       explicitly uses the project's test naming convention.

    The filename check is only applied to c1..c9/t1..t9, so
    a normally renamed user upload is not rejected just because
    its filename is different.
    """

    expected_filename = os.path.basename(
        reference_path
    ).lower()

    # ------------------------------------------------------
    # 1. Exact hash match against another trusted reference
    # ------------------------------------------------------

    uploaded_hash = sha256_hex(
        file_bytes
    )

    for mapped_id, mapped_filename in CERTIFICATE_REFERENCE_MAP.items():

        mapped_filename = str(
            mapped_filename
        ).lower()

        if mapped_filename == expected_filename:
            continue

        candidate_path = os.path.join(
            REFERENCE_DIR,
            mapped_filename
        )

        if not os.path.exists(candidate_path):
            continue

        try:
            with open(
                candidate_path,
                "rb"
            ) as f:
                candidate_bytes = f.read()

            if uploaded_hash == sha256_hex(candidate_bytes):
                print(
                    "WRONG CERTIFICATE DETECTED BY HASH:",
                    mapped_id,
                    mapped_filename
                )
                return True

        except Exception as e:
            print(
                "Wrong-certificate hash check skipped:",
                repr(e)
            )

    # ------------------------------------------------------
    # 2. Known project filename check
    # ------------------------------------------------------

    uploaded_name = os.path.basename(
        uploaded_filename or ""
    ).lower()

    if uploaded_name:
        stem = os.path.splitext(
            uploaded_name
        )[0]

        expected_stem = os.path.splitext(
            expected_filename
        )[0]

        if (
            len(stem) >= 2
            and stem[0] in ("c", "t")
            and stem[1:].isdigit()
            and expected_stem.startswith("c")
            and expected_stem[1:].isdigit()
        ):
            uploaded_number = int(
                stem[1:]
            )

            expected_number = int(
                expected_stem[1:]
            )

            if uploaded_number != expected_number:
                print(
                    "WRONG CERTIFICATE DETECTED BY FILENAME:",
                    uploaded_name,
                    "expected",
                    expected_filename
                )
                return True

    return False


# ==========================================================
# VERIFY CERTIFICATE
# ==========================================================

@app.post(
    "/verify",
    response_model=VerifyResult
)
async def verify_certificate(
    file: UploadFile = File(...),
    certificate_id: str = Form(...)
):

    # ======================================================
    # 1. READ UPLOADED FILE
    # ======================================================

    file_bytes = await file.read()

    if not file_bytes:

        raise HTTPException(
            status_code=400,
            detail="Uploaded certificate is empty."
        )

    certificate_id = certificate_id.strip()

    if not certificate_id:

        raise HTTPException(
            status_code=400,
            detail="Certificate ID is required."
        )

    # ======================================================
    # 2. FIND CERTIFICATE IN DATABASE
    # ======================================================

    db = SessionLocal()

    try:

        trusted_certificate = (
            db.query(Certificate)
            .filter(
                Certificate.student_id
                == certificate_id
            )
            .first()
        )

    finally:

        db.close()

    if trusted_certificate is None:

        raise HTTPException(
            status_code=404,
            detail=(
                f"No trusted certificate found "
                f"for certificate ID: {certificate_id}"
            )
        )

    # ======================================================
    # 3. FIND TRUSTED REFERENCE IMAGE
    # ======================================================

    reference_path = get_reference_image(
        certificate_id
    )

    if reference_path is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "No trusted reference certificate "
                f"found for certificate ID: {certificate_id}"
            )
        )

    # ======================================================
    # 4. CHECK WHETHER UPLOADED IMAGE BELONGS TO THIS ID
    # ======================================================

    if _detect_wrong_certificate(
        certificate_id,
        file_bytes,
        reference_path,
        file.filename or ""
    ):

        return VerifyResult(
            forgery_check={
                "structured_tampering": False,
                "identity_mismatch": True
            },
            hash_found_onchain=False,
            signature_valid=False,
            revoked=trusted_certificate.revoked,
            issuer=None,
            ipfs_cid=trusted_certificate.ipfs_cid,
            issued_at=None,
            overall_verdict=(
                "WRONG DETAILS - uploaded certificate does not belong "
                "to the supplied certificate ID."
            )
        )

    # ======================================================
    # 4. CALCULATE HASHES
    # ======================================================

    uploaded_hash = sha256_hex(
        file_bytes
    )

    uploaded_hash_clean = (
        uploaded_hash
        .replace("0x", "")
        .lower()
        .strip()
    )

    trusted_hash = (
        trusted_certificate.certificate_hash
        or ""
    )

    trusted_hash_clean = (
        trusted_hash
        .replace("0x", "")
        .lower()
        .strip()
    )

    exact_hash_match = (
        uploaded_hash_clean
        == trusted_hash_clean
    )

    # ======================================================
    # DEBUG
    # ======================================================

    print()
    print("=" * 60)
    print("VERIFY DEBUG")
    print("Certificate ID:", certificate_id)
    print("Reference     :", reference_path)
    print("Uploaded Hash :", uploaded_hash_clean)
    print("Trusted Hash  :", trusted_hash_clean)
    print("Exact Hash Match:", exact_hash_match)
    print("=" * 60)

    # ======================================================
    # 5. GET TRUSTED BLOCKCHAIN RECORD
    # ======================================================

    trusted_onchain = (
        blockchain_utils
        .verify_certificate_onchain(
            trusted_hash
        )
    )

    # ======================================================
    # 6. CHECK UPLOADED HASH ON BLOCKCHAIN
    # ======================================================
    #
    # This is retained for exact-file verification.
    # It must NOT be used by itself to call a visually
    # matching certificate forged.
    # ======================================================

    uploaded_onchain = (
        blockchain_utils
        .verify_certificate_onchain(
            uploaded_hash
        )
    )

    # ======================================================
    # 7. IMAGE / STRUCTURED FORGERY ANALYSIS
    # ======================================================

    try:

        print()
        print("=" * 60)
        print("STARTING FORGERY ANALYSIS")
        print("Reference:", reference_path)
        print("=" * 60)

        forgery_result = (
            forgery_detection.analyze_image(
                file_bytes,
                reference_path,
                certificate_id
            )
        )

        print()
        print("=" * 60)
        print("FORGERY ANALYSIS RESULT")
        print(forgery_result)
        print("=" * 60)

    except Exception as e:

        print()
        print("=" * 60)
        print("FORGERY ANALYSIS ERROR")
        print("ERROR:", repr(e))
        print("=" * 60)

        forgery_result = {

            "verdict":
                "analysis_error",

            "structured_tampering":
                False,

            "error":
                str(e)
        }

    # ======================================================
    # 8. CHECK STRUCTURED TAMPERING
    # ======================================================

    structured_tampering = bool(
        forgery_result.get(
            "structured_tampering",
            False
        )
    )

    # ======================================================
    # 9. FIELD-LEVEL TAMPERING
    # ======================================================

    field_tampering = False

    # ------------------------------------------------------
    # STUDENT NAME
    # ------------------------------------------------------

    student_name_result = (
        forgery_result.get(
            "student_name"
        )
    )

    if isinstance(
        student_name_result,
        dict
    ):

        if (
            student_name_result.get(
                "status"
            )
            == "TAMPERED"
        ):

            field_tampering = True

    # ------------------------------------------------------
    # SIGNATURE
    # ------------------------------------------------------

    signature_result = (
        forgery_result.get(
            "signature"
        )
    )

    if isinstance(
        signature_result,
        dict
    ):

        if (
            signature_result.get(
                "status"
            )
            == "TAMPERED"
        ):

            field_tampering = True

        signatures = (
            signature_result.get(
                "signatures",
                []
            )
        )

        if isinstance(
            signatures,
            list
        ):

            for signature in signatures:

                if not isinstance(
                    signature,
                    dict
                ):

                    continue

                if (
                    signature.get(
                        "status"
                    )
                    == "TAMPERED"
                ):

                    field_tampering = True
                    break

    # ------------------------------------------------------
    # SEAL
    # ------------------------------------------------------

    seal_result = (
        forgery_result.get(
            "seal"
        )
    )

    if isinstance(
        seal_result,
        dict
    ):

        if (
            seal_result.get(
                "status"
            )
            == "TAMPERED"
        ):

            field_tampering = True

    # ------------------------------------------------------
    # REGISTER NUMBER
    # ------------------------------------------------------

    register_result = (
        forgery_result.get(
            "register_number"
        )
    )

    if isinstance(
        register_result,
        dict
    ):

        if (
            register_result.get(
                "status"
            )
            == "TAMPERED"
        ):

            field_tampering = True

    # ======================================================
    # 10. COMBINE FIELD RESULTS
    # ======================================================

    if field_tampering:

        structured_tampering = True

    # ======================================================
    # 11. ANALYSIS ERROR SAFETY
    # ======================================================
    #
    # An analysis error must never be silently treated as
    # a genuine certificate.
    # ======================================================

    analysis_error = (
        forgery_result.get(
            "verdict"
        )
        == "analysis_error"
    )

    if analysis_error:

        return VerifyResult(

            forgery_check=forgery_result,

            hash_found_onchain=(
                uploaded_onchain.get(
                    "found",
                    False
                )
            ),

            signature_valid=None,

            revoked=(
                trusted_onchain.get(
                    "revoked"
                )
                if trusted_onchain.get(
                    "found",
                    False
                )
                else None
            ),

            issuer=(
                trusted_onchain.get(
                    "issuer"
                )
                if trusted_onchain.get(
                    "found",
                    False
                )
                else None
            ),

            ipfs_cid=(
                trusted_onchain.get(
                    "ipfs_cid"
                )
                if trusted_onchain.get(
                    "found",
                    False
                )
                else None
            ),

            issued_at=(
                trusted_onchain.get(
                    "issued_at"
                )
                if trusted_onchain.get(
                    "found",
                    False
                )
                else None
            ),

            overall_verdict=(
                "VERIFICATION INCONCLUSIVE - "
                "forgery analysis could not be completed."
            )
        )

    # ======================================================
    # 12. FORGED / ALTERED
    #
    # Structured tampering has highest priority.
    # ======================================================

    if structured_tampering:

        forgery_result["verdict"] = (
            "FORGED / ALTERED"
        )

        return VerifyResult(

            forgery_check=forgery_result,

            hash_found_onchain=False,

            signature_valid=False,

            revoked=(
                trusted_onchain.get(
                    "revoked",
                    False
                )
                if trusted_onchain.get(
                    "found",
                    False
                )
                else None
            ),

            issuer=(
                trusted_onchain.get(
                    "issuer"
                )
                if trusted_onchain.get(
                    "found",
                    False
                )
                else None
            ),

            ipfs_cid=(
                trusted_onchain.get(
                    "ipfs_cid"
                )
                if trusted_onchain.get(
                    "found",
                    False
                )
                else None
            ),

            issued_at=(
                trusted_onchain.get(
                    "issued_at"
                )
                if trusted_onchain.get(
                    "found",
                    False
                )
                else None
            ),

            overall_verdict=(
                "FORGED / ALTERED - certificate "
                "content tampering was detected."
            )
        )

    # ======================================================
    # 13. HASH DIFFERENT BUT STRUCTURED CONTENT MATCHES
    # ======================================================
    #
    # IMPORTANT CHANGE:
    #
    # A different SHA-256 does NOT automatically produce:
    #
    #     INVALID
    #     VERIFICATION INCONCLUSIVE
    #
    # if the trusted reference is available and the
    # structured certificate checks all match.
    #
    # This is specifically required for certificates such
    # as C3 where the same visible certificate can be saved
    # with different JPEG encoding/metadata and therefore
    # receive a different SHA-256.
    #
    # The blockchain signature belongs to the ORIGINAL
    # trusted file, so it cannot cryptographically verify
    # the new bytes. Therefore signature_valid is left as
    # None for the re-encoded/visually-matched file.
    # ======================================================

    if not exact_hash_match:

        forgery_result["verdict"] = (
            "LIKELY GENUINE - VISUAL MATCH, "
            "FILE HASH DIFFERENT"
        )

        forgery_result["hash_match"] = False

        forgery_result["exact_file_match"] = False

        forgery_result["verification_basis"] = (
            "Trusted reference image + structured "
            "certificate comparison"
        )

        forgery_result["hash_note"] = (
            "Uploaded file SHA-256 differs from the "
            "blockchain-anchored file. This does not "
            "by itself indicate certificate forgery."
        )

        return VerifyResult(

            forgery_check=forgery_result,

            hash_found_onchain=(
                uploaded_onchain.get(
                    "found",
                    False
                )
            ),

            # None is intentional:
            # the uploaded bytes are not the exact bytes
            # that were digitally signed on-chain.
            signature_valid=None,

            revoked=(
                trusted_onchain.get(
                    "revoked"
                )
                if trusted_onchain.get(
                    "found",
                    False
                )
                else None
            ),

            issuer=(
                trusted_onchain.get(
                    "issuer"
                )
                if trusted_onchain.get(
                    "found",
                    False
                )
                else None
            ),

            ipfs_cid=(
                trusted_onchain.get(
                    "ipfs_cid"
                )
                if trusted_onchain.get(
                    "found",
                    False
                )
                else None
            ),

            issued_at=(
                trusted_onchain.get(
                    "issued_at"
                )
                if trusted_onchain.get(
                    "found",
                    False
                )
                else None
            ),

            overall_verdict=(
                "VALID - certificate visually matches "
                "the trusted reference. The uploaded "
                "file has a different SHA-256 because "
                "the file bytes are not identical to the "
                "original blockchain-anchored file."
            )
        )

    # ======================================================
    # 14. EXACT HASH MATCH
    # ======================================================

    if not uploaded_onchain.get(
        "found",
        False
    ):

        return VerifyResult(

            forgery_check=forgery_result,

            hash_found_onchain=False,

            signature_valid=False,

            revoked=(
                trusted_onchain.get(
                    "revoked"
                )
                if trusted_onchain.get(
                    "found",
                    False
                )
                else None
            ),

            issuer=(
                trusted_onchain.get(
                    "issuer"
                )
                if trusted_onchain.get(
                    "found",
                    False
                )
                else None
            ),

            ipfs_cid=(
                trusted_onchain.get(
                    "ipfs_cid"
                )
                if trusted_onchain.get(
                    "found",
                    False
                )
                else None
            ),

            issued_at=(
                trusted_onchain.get(
                    "issued_at"
                )
                if trusted_onchain.get(
                    "found",
                    False
                )
                else None
            ),

            overall_verdict=(
                "INVALID - certificate hash "
                "was not found on the blockchain."
            )
        )

    # ======================================================
    # 15. GET DIGITAL SIGNATURE
    # ======================================================

    signature_hex = (
        uploaded_onchain.get(
            "signature"
        )
    )

    signature_bytes = b""

    if signature_hex:

        try:

            signature_bytes = bytes.fromhex(
                signature_hex
            )

        except (
            ValueError,
            TypeError
        ):

            signature_bytes = b""

    # ======================================================
    # 16. VERIFY DIGITAL SIGNATURE
    # ======================================================

    signature_valid = False

    if signature_bytes:

        try:

            signature_valid = (
                digital_signature.verify_signature(
                    bytes.fromhex(
                        uploaded_hash_clean
                    ),
                    signature_bytes
                )
            )

        except Exception:

            signature_valid = False

    # ======================================================
    # 17. REVOCATION
    # ======================================================

    if trusted_onchain.get(
        "revoked",
        False
    ):

        verdict = (
            "REVOKED - certificate has been "
            "revoked on the blockchain."
        )

    # ======================================================
    # 18. SIGNATURE FAILURE
    # ======================================================

    elif not signature_valid:

        verdict = (
            "INVALID - digital signature "
            "verification failed."
        )

    # ======================================================
    # 19. VALID
    # ======================================================

    else:

        verdict = (
            "VALID - certificate is registered "
            "on-chain and digitally verified."
        )

    # ======================================================
    # 20. FINAL RESPONSE
    # ======================================================

    return VerifyResult(

        forgery_check=forgery_result,

        hash_found_onchain=True,

        signature_valid=signature_valid,

        revoked=(
            trusted_onchain.get(
                "revoked",
                False
            )
        ),

        issuer=(
            trusted_onchain.get(
                "issuer"
            )
        ),

        ipfs_cid=(
            trusted_onchain.get(
                "ipfs_cid"
            )
        ),

        issued_at=(
            trusted_onchain.get(
                "issued_at"
            )
        ),

        overall_verdict=verdict
    )
