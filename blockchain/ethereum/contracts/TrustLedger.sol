// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract TrustLedger {
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

    modifier onlyVerifiedHospital() {
        require(verifiedHospitals[msg.sender], "hospital not verified");
        _;
    }

    function setHospitalVerification(address hospital, bool verified) external {
        verifiedHospitals[hospital] = verified;
        emit HospitalVerified(hospital, verified);
    }

    function anchorDiagnosis(bytes32 diagnosisId, bytes32 recordHash, bytes32 trustHash, bytes32 auditHash) external onlyVerifiedHospital {
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
