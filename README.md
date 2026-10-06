# Blockchain Based Anti-Forgery System for Academic Certificates

## 📌 Overview

**CertChain** is a blockchain-based certificate verification system designed to detect forged or tampered academic certificates and provide a secure method for verifying certificate authenticity.

The system combines image-based forgery detection, OCR, digital signatures, blockchain technology, IPFS storage, and certificate revocation into a single verification pipeline.

## 🎯 Objectives

- Detect possible tampering in academic certificates.
- Verify certificate authenticity using blockchain records.
- Generate and verify SHA-256 certificate hashes.
- Protect certificate integrity using digital signatures.
- Store certificate files using IPFS.
- Verify certificate information using OCR and image analysis.
- Detect and compare certificate names, signatures, seals, and other fields.
- Support certificate revocation.
- Provide a web-based interface for certificate issuance and verification.

## ✨ Key Features

- 🔐 Blockchain-based certificate registration
- 🧾 SHA-256 certificate hashing
- ✍️ RSA digital signature generation and verification
- 🖼️ Image-based forgery detection
- 🔍 OCR-based certificate information extraction
- 👤 Student name detection and comparison
- 📝 Register number comparison
- ✒️ Signature detection
- 🏛️ Seal detection
- 📐 Image alignment and structural comparison
- 📦 IPFS-based certificate storage
- 🚫 Certificate revocation
- ⚡ FastAPI backend
- 🖥️ Web-based frontend
- 👨‍💼 Admin dashboard
- 📋 Verification and audit information

---

# 🏗️ System Architecture

The system consists of five major layers:

```text
                    ┌───────────────────────┐
                    │       Frontend        │
                    │   HTML / CSS / JS     │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │    FastAPI Backend    │
                    │       Python          │
                    └───────────┬───────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
              ▼                 ▼                 ▼
       ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
       │   Forgery   │   │  Digital    │   │    IPFS     │
       │  Detection  │   │  Signature  │   │   Storage   │
       └─────────────┘   └─────────────┘   └─────────────┘
              │                 │                 │
              └─────────────────┼─────────────────┘
                                ▼
                    ┌───────────────────────┐
                    │      Blockchain       │
                    │  Solidity Smart       │
                    │      Contract         │
                    └───────────────────────┘