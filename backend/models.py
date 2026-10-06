from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean
)

from sqlalchemy.orm import relationship

from datetime import datetime

from database import Base


# ==========================================================
# USER
# ==========================================================

class User(Base):

    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    username = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )

    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )

    password_hash = Column(
        String(255),
        nullable=False
    )

    role = Column(
        String(50),
        nullable=False,
        default="student"
    )

    is_active = Column(
        Boolean,
        default=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


# ==========================================================
# INSTITUTION
# ==========================================================

class Institution(Base):

    __tablename__ = "institutions"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String(255),
        nullable=False
    )

    institution_code = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )

    email = Column(
        String(255)
    )

    address = Column(
        String(500)
    )

    is_active = Column(
        Boolean,
        default=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


# ==========================================================
# STUDENT
# ==========================================================

class Student(Base):

    __tablename__ = "students"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    student_id = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )

    name = Column(
        String(255),
        nullable=False
    )

    course = Column(
        String(255)
    )

    institution_id = Column(
        Integer,
        ForeignKey(
            "institutions.id"
        )
    )

    email = Column(
        String(255)
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


# ==========================================================
# AUDIT LOG
# ==========================================================

class AuditLog(Base):

    __tablename__ = "audit_logs"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        nullable=True
    )

    action = Column(
        String(100),
        nullable=False
    )

    description = Column(
        String(1000)
    )

    ip_address = Column(
        String(100)
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    # ==========================================================
# CERTIFICATE
# ==========================================================

class Certificate(Base):

    __tablename__ = "certificates"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    student_id = Column(
        String(100),
        nullable=False,
        index=True
    )

    student_name = Column(
        String(255),
        nullable=False
    )

    course = Column(
        String(255)
    )

    certificate_hash = Column(
        String(66),
        unique=True,
        nullable=False,
        index=True
    )

    ipfs_cid = Column(
        String(255)
    )

    transaction_hash = Column(
        String(100)
    )

    block_number = Column(
        Integer
    )

    signature_hex = Column(
        String(1000)
    )

    student_id_hash = Column(
        String(100)
    )

    issuer = Column(
        String(255)
    )

    issued_at = Column(
        Integer
    )

    revoked = Column(
        Boolean,
        default=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )