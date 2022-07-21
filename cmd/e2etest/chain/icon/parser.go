package icon

import (
	"bytes"
	"encoding/hex"
	"fmt"
	"math/big"
	"strings"

	"github.com/pkg/errors"

	"github.com/ethereum/go-ethereum/common/hexutil"
	"github.com/ethereum/go-ethereum/rlp"
	"github.com/icon-project/icon-bridge/cmd/e2etest/chain"
	"github.com/icon-project/icon-bridge/cmd/iconbridge/chain/icon"
	"github.com/icon-project/icon-bridge/common"
)

type parser struct {
	addressToContractName map[string]chain.ContractName
}

func NewParser(nameToAddr map[chain.ContractName]string) (*parser, error) {
	addrToName := map[string]chain.ContractName{}
	for name, addr := range nameToAddr {
		addrToName[addr] = name
	}
	return &parser{addressToContractName: addrToName}, nil
}

func (p *parser) ParseTxn(log *TxnEventLog) (resLog interface{}, eventType chain.EventLogType, err error) {
	eventName := strings.Split(string(log.Indexed[0]), "(")
	eventType = chain.EventLogType(strings.TrimSpace(eventName[0]))
	if eventType == chain.TransferStart {
		resLog, err = parseTransferStartTxn(log)
	} else if eventType == chain.TransferReceived {
		resLog, err = parseTransferReceivedTxn(log)
	} else if eventType == chain.TransferEnd {
		resLog, err = parseTransferEndTxn(log)
	} else {
		err = fmt.Errorf("No matching signature for event log of type %v generated by contract address %v", eventType, log.Addr)
	}
	return
}

func (p *parser) Parse(log *icon.EventLog) (resLog interface{}, eventType chain.EventLogType, err error) {
	eventName := strings.Split(string(log.Indexed[0]), "(")
	eventType = chain.EventLogType(strings.TrimSpace(eventName[0]))
	if eventType == chain.TransferStart {
		resLog, err = parseTransferStart(log)
	} else if eventType == chain.TransferReceived {
		resLog, err = parseTransferReceived(log)
	} else if eventType == chain.TransferEnd {
		resLog, err = parseTransferEnd(log)
	} else {
		err = fmt.Errorf("No matching signature for event log of type %v generated by contract address %v", eventType, log.Addr)
	}
	return
}

func rlpDecodeHex(str string, out interface{}) error {
	if strings.HasPrefix(str, "0x") {
		str = str[2:]
	}
	input, err := hex.DecodeString(str)
	if err != nil {
		return errors.Wrap(err, "hex.DecodeString ")
	}
	err = rlp.Decode(bytes.NewReader(input), out)
	if err != nil {
		return errors.Wrap(err, "rlp.Decode ")
	}
	return nil
}

func parseTransferStart(log *icon.EventLog) (*chain.TransferStartEvent, error) {
	if len(log.Data) != 3 {
		return nil, fmt.Errorf("Unexpected length of log.Data. Got %d. Expected 3", len(log.Data))
	}
	//logAddr := common.NewAddress(log.Addr).String()
	var sn common.HexInt
	sn.SetBytes(log.Data[1])

	res := []AssetTxDetails{}
	err := rlp.Decode(bytes.NewReader(log.Data[2]), &res)
	if err != nil {
		fmt.Println(err)
		return nil, errors.Wrapf(err, "rlp.Decode %v", err)
	}

	ts := &chain.TransferStartEvent{
		From:   common.NewAddress(log.Indexed[1]).String(),
		To:     string(log.Data[0]),
		Sn:     big.NewInt(sn.Int64()),
		Assets: []chain.AssetTransferDetails{},
	}
	for _, r := range res {
		f := new(big.Int)
		f.SetString(hexutil.Encode(r.Fee)[2:], 16)
		v := new(big.Int)
		v.SetString(hexutil.Encode(r.Value)[2:], 16)

		ts.Assets = append(ts.Assets, chain.AssetTransferDetails{
			Name:  r.Name,
			Value: v,
			Fee:   f,
		})
	}
	return ts, nil
}

func parseTransferReceived(log *icon.EventLog) (*chain.TransferReceivedEvent, error) {
	if len(log.Data) != 2 || len(log.Indexed) != 3 {
		return nil, fmt.Errorf("Unexpected length. Got %v and %v. Expected 2 and 3", len(log.Data), len(log.Indexed))
	}

	res := []AssetTx{}
	err := rlpDecodeHex(common.HexBytes(log.Data[1]).String(), &res)
	if err != nil {
		return nil, errors.Wrap(err, "rlp.DecodeHex ")
	}
	var sn common.HexInt
	sn.SetBytes(log.Data[0])

	ts := &chain.TransferReceivedEvent{
		From:   string(log.Indexed[1]),
		To:     common.NewAddress(log.Indexed[2]).String(),
		Sn:     big.NewInt(sn.Int64()),
		Assets: []chain.AssetTransferDetails{},
	}
	for _, r := range res {
		v := new(big.Int)
		v.SetString(hexutil.Encode(r.Value)[2:], 16)

		ts.Assets = append(ts.Assets, chain.AssetTransferDetails{
			Name:  r.Name,
			Value: v,
		})
	}
	return ts, nil
}

func parseTransferEnd(log *icon.EventLog) (*chain.TransferEndEvent, error) {
	var sn common.HexInt
	sn.SetBytes(log.Data[0])

	var cd common.HexInt
	cd.SetBytes(log.Data[1])
	response := ""
	if len(log.Data[2]) > 0 {
		response = string(log.Data[2])
	}
	te := &chain.TransferEndEvent{
		From:     common.NewAddress(log.Indexed[1]).String(),
		Sn:       big.NewInt(sn.Int64()),
		Code:     big.NewInt(cd.Int64()),
		Response: response,
	}
	return te, nil
}

func parseTransferStartTxn(log *TxnEventLog) (*chain.TransferStartEvent, error) {
	if len(log.Data) != 3 {
		return nil, fmt.Errorf("Unexpected length of log.Data. Got %d. Expected 3", len(log.Data))
	}
	data := log.Data
	res := []AssetTxDetails{}
	err := rlpDecodeHex(data[len(data)-1], &res)
	if err != nil {
		return nil, errors.Wrapf(err, "rlpDecodeHex %v", err)
	}
	sn := new(big.Int)
	if strings.HasPrefix(data[1], "0x") {
		data[1] = data[1][2:]
	}
	sn.SetString(data[1], 16)
	ts := &chain.TransferStartEvent{
		From:   log.Indexed[1],
		To:     data[0],
		Sn:     sn,
		Assets: []chain.AssetTransferDetails{},
	}

	for _, r := range res {
		f := new(big.Int)
		f.SetString(hexutil.Encode(r.Fee)[2:], 16)
		v := new(big.Int)
		v.SetString(hexutil.Encode(r.Value)[2:], 16)

		ts.Assets = append(ts.Assets, chain.AssetTransferDetails{
			Name:  r.Name,
			Value: v,
			Fee:   f,
		})
	}
	return ts, nil
}

func parseTransferReceivedTxn(log *TxnEventLog) (*chain.TransferReceivedEvent, error) {
	if len(log.Data) != 2 || len(log.Indexed) != 3 {
		return nil, fmt.Errorf("Unexpected length. Got %v and %v. Expected 2 and 3", len(log.Data), len(log.Indexed))
	}
	data := log.Data
	res := []AssetTx{}
	err := rlpDecodeHex(data[len(data)-1], &res)
	if err != nil {
		return nil, errors.Wrap(err, "rlp.DecodeHex ")
	}
	sn := new(big.Int)
	if strings.HasPrefix(data[0], "0x") {
		data[0] = data[0][2:]
	}
	sn.SetString(data[0], 16)

	ts := &chain.TransferReceivedEvent{
		From:   log.Indexed[1],
		To:     log.Indexed[2],
		Sn:     sn,
		Assets: []chain.AssetTransferDetails{},
	}
	for _, r := range res {
		v := new(big.Int)
		v.SetString(hexutil.Encode(r.Value)[2:], 16)

		ts.Assets = append(ts.Assets, chain.AssetTransferDetails{
			Name:  r.Name,
			Value: v,
		})
	}
	return ts, nil
}

func parseTransferEndTxn(log *TxnEventLog) (*chain.TransferEndEvent, error) {
	data := log.Data
	sn := new(big.Int)
	if strings.HasPrefix(data[0], "0x") {
		data[0] = data[0][2:]
	}
	sn.SetString(data[0], 16)

	cd := new(big.Int)
	if strings.HasPrefix(data[1], "0x") {
		data[1] = data[1][2:]
	}

	cd.SetString(data[1], 16)
	te := &chain.TransferEndEvent{
		From:     log.Indexed[1],
		Sn:       sn,
		Code:     cd,
		Response: data[2],
	}
	return te, nil
}

type AssetTxDetails struct {
	Name  string
	Value []byte
	Fee   []byte
}

type AssetTx struct {
	Name  string
	Value []byte
}
