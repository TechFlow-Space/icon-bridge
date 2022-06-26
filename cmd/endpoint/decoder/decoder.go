package decoder

import (
	"errors"
	"fmt"
	"sync"

	ctr "github.com/icon-project/icon-bridge/cmd/endpoint/decoder/contracts"
	"github.com/icon-project/icon-bridge/cmd/endpoint/decoder/contracts/bmcHmy"
	bmcicon "github.com/icon-project/icon-bridge/cmd/endpoint/decoder/contracts/bmcIcon"
	"github.com/icon-project/icon-bridge/cmd/endpoint/decoder/contracts/erc20Hmy"
	"github.com/icon-project/icon-bridge/cmd/endpoint/decoder/contracts/irc2Icon"
	"github.com/icon-project/icon-bridge/cmd/endpoint/decoder/contracts/nativeHmy"
	"github.com/icon-project/icon-bridge/cmd/endpoint/decoder/contracts/nativeIcon"
	"github.com/icon-project/icon-bridge/cmd/endpoint/decoder/contracts/tokenHmy"
	"github.com/icon-project/icon-bridge/cmd/endpoint/decoder/contracts/tokenIcon"
)

// Update this function for more contracts
func getNewContract(cName ctr.ContractName, url string, cAddr string) (ctr.Contract, error) {
	if cName == ctr.TokenHmy {
		return tokenHmy.NewContract(cName, url, cAddr)
	} else if cName == ctr.NativeHmy {
		return nativeHmy.NewContract(cName, url, cAddr)
	} else if cName == ctr.Erc20Hmy {
		return erc20Hmy.NewContract(cName, url, cAddr)
	} else if cName == ctr.Erc20TradeableHmy {
		return erc20Hmy.NewContract(cName, url, cAddr)
	} else if cName == ctr.BmcHmy {
		return bmcHmy.NewContract(cName, url, cAddr)
	} else if cName == ctr.TokenIcon {
		return tokenIcon.NewContract(cName)
	} else if cName == ctr.NativeIcon {
		return nativeIcon.NewContract(cName)
	} else if cName == ctr.Irc2Icon {
		return irc2Icon.NewContract(cName)
	} else if cName == ctr.Irc2TradeableIcon {
		return irc2Icon.NewContract(cName)
	} else if cName == ctr.BmcIcon {
		return bmcicon.NewContract(cName)
	}
	return nil, errors.New("Contract not registered")
}

type Decoder interface {
	Add(contractNameToAddressMap map[ctr.ContractName]string) (err error)
	Remove(addr string)
	DecodeEventLogData(log interface{}, addr string) (map[string]interface{}, error)
}

type decoder struct {
	url            string
	mtx            sync.RWMutex
	addrToContract map[string]ctr.Contract
}

func New(url string, contractNameToAddressMap map[ctr.ContractName]string) (Decoder, error) {
	var err error
	dec := &decoder{mtx: sync.RWMutex{}, url: url, addrToContract: make(map[string]ctr.Contract)}
	for cName, cAddr := range contractNameToAddressMap {
		dec.addrToContract[cAddr], err = getNewContract(cName, url, cAddr)
		if err != nil {
			return nil, err
		}
	}
	return dec, nil
}

func (d *decoder) Add(contractNameToAddressMap map[ctr.ContractName]string) (err error) {
	d.mtx.Lock()
	defer d.mtx.Unlock()
	for cName, cAddr := range contractNameToAddressMap {
		if _, ok := d.addrToContract[cAddr]; ok {
			continue // address already exists
		}
		d.addrToContract[cAddr], err = getNewContract(cName, d.url, cAddr)
		if err != nil {
			return
		}
	}
	return nil
}

func (d *decoder) Remove(addr string) {
	d.mtx.Lock()
	defer d.mtx.Unlock()
	delete(d.addrToContract, addr)
}

func (d *decoder) DecodeEventLogData(log interface{}, addr string) (map[string]interface{}, error) {
	d.mtx.RLock()
	defer d.mtx.RUnlock()
	ctr, ok := d.addrToContract[addr]
	if !ok {
		fmt.Println("Skipping ", addr)
		return nil, nil
	}
	return ctr.Decode(log)
}
