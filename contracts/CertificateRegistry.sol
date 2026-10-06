// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title CertificateRegistry
/// @notice Stores tamper-evident records of academic certificates.
///         Each record links: a SHA-256 hash of the certificate content,
///         the IPFS CID of the stored file, and the issuer's digital
///         signature over that hash. Nothing about the certificate's
///         actual content is stored on-chain — only proofs.
contract CertificateRegistry {
    struct Certificate {
        bytes32 certHash;      // SHA-256 hash of certificate content
        string  ipfsCID;       // Content identifier on IPFS
        address issuer;        // Wallet address of issuing institution
        bytes   signature;     // Issuer's digital signature over certHash
        uint256 issuedAt;      // Block timestamp of issuance
        bool    revoked;       // Revocation flag
        string  studentIdHash; // Hashed student identifier (privacy-preserving)
    }

    // certHash => Certificate
    mapping(bytes32 => Certificate) private certificates;
    // certHash => existence flag
    mapping(bytes32 => bool) private exists;

    // Authorized issuing institutions (registrars, universities)
    mapping(address => bool) public authorizedIssuers;
    address public admin;

    event IssuerAuthorized(address indexed issuer);
    event IssuerRevoked(address indexed issuer);
    event CertificateIssued(bytes32 indexed certHash, address indexed issuer, string ipfsCID, uint256 issuedAt);
    event CertificateRevoked(bytes32 indexed certHash, address indexed revokedBy);

    modifier onlyAdmin() {
        require(msg.sender == admin, "Not admin");
        _;
    }

    modifier onlyAuthorizedIssuer() {
        require(authorizedIssuers[msg.sender], "Not an authorized issuer");
        _;
    }

    constructor() {
        admin = msg.sender;
        authorizedIssuers[msg.sender] = true;
        emit IssuerAuthorized(msg.sender);
    }

    function authorizeIssuer(address issuer) external onlyAdmin {
        authorizedIssuers[issuer] = true;
        emit IssuerAuthorized(issuer);
    }

    function revokeIssuer(address issuer) external onlyAdmin {
        authorizedIssuers[issuer] = false;
        emit IssuerRevoked(issuer);
    }

    /// @notice Register a new certificate on-chain.
    /// @param certHash SHA-256 hash of the canonical certificate data.
    /// @param ipfsCID IPFS content identifier where the file/metadata is pinned.
    /// @param signature Issuer's digital signature over certHash.
    /// @param studentIdHash Hash of the student's identifier (not raw PII).
    function issueCertificate(
        bytes32 certHash,
        string calldata ipfsCID,
        bytes calldata signature,
        string calldata studentIdHash
    ) external onlyAuthorizedIssuer {
        require(!exists[certHash], "Certificate already registered");

        certificates[certHash] = Certificate({
            certHash: certHash,
            ipfsCID: ipfsCID,
            issuer: msg.sender,
            signature: signature,
            issuedAt: block.timestamp,
            revoked: false,
            studentIdHash: studentIdHash
        });
        exists[certHash] = true;

        emit CertificateIssued(certHash, msg.sender, ipfsCID, block.timestamp);
    }

    /// @notice Revoke a previously issued certificate (e.g. found fraudulent after the fact).
    function revokeCertificate(bytes32 certHash) external {
        require(exists[certHash], "Certificate not found");
        Certificate storage c = certificates[certHash];
        require(msg.sender == c.issuer || msg.sender == admin, "Not authorized to revoke");
        c.revoked = true;
        emit CertificateRevoked(certHash, msg.sender);
    }

    /// @notice Verify and fetch a certificate record by its content hash.
    function verifyCertificate(bytes32 certHash)
        external
        view
        returns (
            bool found,
            string memory ipfsCID,
            address issuer,
            bytes memory signature,
            uint256 issuedAt,
            bool revoked,
            string memory studentIdHash
        )
    {
        if (!exists[certHash]) {
            return (false, "", address(0), "", 0, false, "");
        }
        Certificate storage c = certificates[certHash];
        return (true, c.ipfsCID, c.issuer, c.signature, c.issuedAt, c.revoked, c.studentIdHash);
    }

    function isIssuerAuthorized(address issuer) external view returns (bool) {
        return authorizedIssuers[issuer];
    }
}
