package main

import (
	"encoding/json"
	"fmt"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

type TrustLedgerContract struct {
	contractapi.Contract
}

type DiagnosisAnchor struct {
	DiagnosisID string `json:"diagnosisId"`
	RecordHash  string `json:"recordHash"`
	TrustHash   string `json:"trustHash"`
	AuditHash   string `json:"auditHash"`
	HospitalID  string `json:"hospitalId"`
	Timestamp   string `json:"timestamp"`
}

func (c *TrustLedgerContract) AnchorDiagnosis(ctx contractapi.TransactionContextInterface, anchorJSON string) error {
	var anchor DiagnosisAnchor
	if err := json.Unmarshal([]byte(anchorJSON), &anchor); err != nil {
		return err
	}
	if anchor.DiagnosisID == "" || anchor.RecordHash == "" {
		return fmt.Errorf("diagnosisId and recordHash are required")
	}
	payload, err := json.Marshal(anchor)
	if err != nil {
		return err
	}
	return ctx.GetStub().PutState(anchor.DiagnosisID, payload)
}

func (c *TrustLedgerContract) ReadDiagnosis(ctx contractapi.TransactionContextInterface, diagnosisID string) (*DiagnosisAnchor, error) {
	payload, err := ctx.GetStub().GetState(diagnosisID)
	if err != nil {
		return nil, err
	}
	if payload == nil {
		return nil, fmt.Errorf("diagnosis not found")
	}
	var anchor DiagnosisAnchor
	if err := json.Unmarshal(payload, &anchor); err != nil {
		return nil, err
	}
	return &anchor, nil
}

func main() {
	chaincode, err := contractapi.NewChaincode(new(TrustLedgerContract))
	if err != nil {
		panic(err)
	}
	if err := chaincode.Start(); err != nil {
		panic(err)
	}
}
