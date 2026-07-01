// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract TrustLedger {
    address public immutable owner;

    struct DiagnosisAnchor {
        bytes32 recordHash;
        bytes32 trustHash;
        bytes32 auditHash;
        address submitter;
        uint256 timestamp;
    }

    mapping(bytes32 => DiagnosisAnchor) public anchors;
    mapping(address => bool) public verifiedHospitals;

    event HospitalVerified(address indexed hospital, bool verified);
    event DiagnosisAnchored(bytes32 indexed diagnosisId, bytes32 recordHash, bytes32 trustHash, bytes32 auditHash);

    modifier onlyOwner() {
        require(msg.sender == owner, "owner only");
        _;
    }

    modifier onlyVerifiedHospital() {
        require(verifiedHospitals[msg.sender], "hospital not verified");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function setHospitalVerification(address hospital, bool verified) external onlyOwner {
        verifiedHospitals[hospital] = verified;
        emit HospitalVerified(hospital, verified);
    }

    function anchorDiagnosis(bytes32 diagnosisId, bytes32 recordHash, bytes32 trustHash, bytes32 auditHash) external onlyVerifiedHospital {
        require(anchors[diagnosisId].timestamp == 0, "diagnosis already anchored");
        anchors[diagnosisId] = DiagnosisAnchor({
            recordHash: recordHash,
            trustHash: trustHash,
            auditHash: auditHash,
            submitter: msg.sender,
            timestamp: block.timestamp
        });
        emit DiagnosisAnchored(diagnosisId, recordHash, trustHash, auditHash);
    }
}
