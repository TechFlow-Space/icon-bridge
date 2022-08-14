package bsc

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"math/big"
	"math/rand"
	"sort"
	"time"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/types"
	ethTypes "github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/trie"
	"github.com/icon-project/icon-bridge/cmd/iconbridge/chain"
	"github.com/icon-project/icon-bridge/common/log"
	"github.com/pkg/errors"
)

const (
	BlockInterval              = 3 * time.Second
	BlockHeightPollInterval    = 60 * time.Second
	MonitorBlockMaxConcurrency = 300 // number of concurrent requests to synchronize older blocks from source chain
)
const RPCCallRetry = 5

func NewReceiver(
	src, dst chain.BTPAddress, urls []string,
	opts map[string]interface{}, l log.Logger) (chain.Receiver, error) {
	r := &receiver{
		log: l,
		src: src,
		dst: dst,
	}
	if len(urls) == 0 {
		return nil, fmt.Errorf("empty urls: %v", urls)
	}
	err := r.opts.Unmarshal(opts)
	if err != nil {
		return nil, err
	}
	if r.opts.SyncConcurrency < 1 {
		r.opts.SyncConcurrency = 1
	} else if r.opts.SyncConcurrency > MonitorBlockMaxConcurrency {
		r.opts.SyncConcurrency = MonitorBlockMaxConcurrency
	}

	r.cls, r.bmcs, err = newClients(urls, src.ContractAddress(), r.log)
	if err != nil {
		return nil, err
	}
	return r, nil
}

type ReceiverOptions struct {
	SyncConcurrency uint64           `json:"syncConcurrency"`
	Verifier        *VerifierOptions `json:"verifier"`
}

func (opts *ReceiverOptions) Unmarshal(v map[string]interface{}) error {
	b, err := json.Marshal(v)
	if err != nil {
		return err
	}
	return json.Unmarshal(b, opts)
}

type receiver struct {
	log  log.Logger
	src  chain.BTPAddress
	dst  chain.BTPAddress
	opts ReceiverOptions
	cls  []*Client
	bmcs []*BMC
}

func (r *receiver) client() *Client {
	randInt := rand.Intn(len(r.cls))
	return r.cls[randInt]
}

func (r *receiver) bmcClient() *BMC {
	randInt := rand.Intn(len(r.cls))
	return r.bmcs[randInt]
}

type BnOptions struct {
	StartHeight uint64
	Concurrency uint64
}

func (r *receiver) newVerifer(opts *VerifierOptions) (*Verifier, error) {
	vr := Verifier{
		next:       big.NewInt(int64(opts.BlockHeight)),
		parentHash: common.HexToHash(opts.BlockHash.String()),
	}
	header, err := r.client().GetHeaderByHeight(big.NewInt(int64(opts.BlockHeight)))
	if err != nil {
		err = errors.Wrapf(err, "GetHeaderByHeight: %v", err)
		return nil, err
	}
	if !bytes.Equal(header.ParentHash.Bytes(), vr.parentHash.Bytes()) {
		return nil, errors.New("Unexpected Hash")
	}
	return &vr, nil
}

func (r *receiver) syncVerifier(vr *Verifier, height int64, concurrency int) error {
	if height == vr.Next().Int64() {
		return nil
	}
	if vr.Next().Int64() > height {
		return fmt.Errorf(
			"invalid target height: verifier height (%s) > target height (%d)",
			vr.Next().String(), height)
	}

	type res struct {
		Height int64
		Header *types.Header
	}

	type req struct {
		height int64
		err    error
		res    *res
		retry  int64
	}

	r.log.WithFields(log.Fields{"height": vr.Next().String(), "target": height}).Debug("syncVerifier: start")

	for vr.Next().Int64() < height {
		rqch := make(chan *req, concurrency)
		for i := vr.Next().Int64(); len(rqch) < cap(rqch); i++ {
			rqch <- &req{height: i, retry: 5}
		}
		sres := make([]*res, 0, len(rqch))
		for q := range rqch {
			switch {
			case q.err != nil:
				if q.retry > 0 {
					q.retry--
					q.res, q.err = nil, nil
					rqch <- q
					continue
				}
				r.log.WithFields(log.Fields{
					"height": q.height, "error": q.err.Error()}).Debug("syncVerifier: req error")
				sres = append(sres, nil)
				if len(sres) == cap(sres) {
					close(rqch)
				}
			case q.res != nil:
				sres = append(sres, q.res)
				if len(sres) == cap(sres) {
					close(rqch)
				}
			default:
				go func(q *req) {
					defer func() {
						time.Sleep(500 * time.Millisecond)
						rqch <- q
					}()
					if q.res == nil {
						q.res = &res{}
					}
					q.res.Height = q.height
					q.res.Header, q.err = r.client().GetHeaderByHeight(big.NewInt(q.height))
					if q.err != nil {
						q.err = errors.Wrapf(q.err, "syncVerifier: getBlockHeader: %v", q.err)
						return
					}
				}(q)
			}
		}
		// filter nil
		_sres, sres := sres, sres[:0]
		for _, v := range _sres {
			if v != nil {
				sres = append(sres, v)
			}
		}
		// sort and forward notifications
		if len(sres) > 0 {
			sort.SliceStable(sres, func(i, j int) bool {
				return sres[i].Height < sres[j].Height
			})
			for _, r := range sres {
				if vr.Next().Int64() >= height {
					break
				}
				if vr.Next().Int64() == r.Height {
					err := vr.Verify(r.Header)
					if err != nil {
						return errors.Wrapf(err, "syncVerifier: Update: %v", err)
					}
				}
			}
			r.log.WithFields(log.Fields{"height": vr.Next().String(), "target": height}).Debug("syncVerifier: syncing")
		}
	}

	r.log.WithFields(log.Fields{"height": vr.Next().String()}).Info("syncVerifier: complete")
	return nil
}

func (r *receiver) receiveLoop(ctx context.Context, opts *BnOptions, callback func(v *BlockNotification) error) (err error) {

	if opts == nil {
		return errors.New("receiveLoop: invalid options: <nil>")
	}

	var vr *Verifier
	if r.opts.Verifier != nil {
		vr, err = r.newVerifer(r.opts.Verifier)
		if err != nil {
			return err
		}
		err = r.syncVerifier(vr, int64(opts.StartHeight), int(r.opts.SyncConcurrency))
		if err != nil {
			return errors.Wrapf(err, "receiveLoop: syncVerifier: %v", err)
		}
	}

	// block notification channel
	// (buffered: to avoid deadlock)
	// increase concurrency parameter for faster sync
	bnch := make(chan *BlockNotification, r.opts.SyncConcurrency)

	heightTicker := time.NewTicker(BlockInterval)
	defer heightTicker.Stop()

	heightPoller := time.NewTicker(BlockHeightPollInterval)
	defer heightPoller.Stop()

	latestHeight := func() uint64 {
		height, err := r.client().GetBlockNumber()
		if err != nil {
			r.log.WithFields(log.Fields{"error": err}).Error("receiveLoop: failed to GetBlockNumber")
			return 0
		}
		return height
	}

	next, latest := opts.StartHeight, latestHeight()

	// last unverified block notification
	var lbn *BlockNotification

	// start monitor loop
	for {
		select {
		case <-ctx.Done():
			return nil

		case <-heightTicker.C:
			latest++

		case <-heightPoller.C:
			if height := latestHeight(); height > latest {
				latest = height
				r.log.Debugf("receiveLoop: poll height; latest=%d, next=%d", latest, next)
			}

		case bn := <-bnch:
			// process all notifications
			for ; bn != nil; next++ {
				if lbn != nil {
					if vr != nil {
						if err := vr.Verify(lbn.Header); err != nil {
							r.log.WithFields(log.Fields{"height": bn.Height, "hash": bn.Hash}).Error("verification failed")
							break
							// return errors.Wrapf(err, "verification failed %v", err)
						}
					}
					if err := callback(lbn); err != nil {
						return errors.Wrapf(err, "receiveLoop: callback: %v", err)
					}
				}
				if lbn, bn = bn, nil; len(bnch) > 0 {
					bn = <-bnch
				}
			}
			// remove unprocessed notifications
			for len(bnch) > 0 {
				<-bnch
			}

		default:
			if next > latest {
				time.Sleep(10 * time.Millisecond)
				continue
			}

			type bnq struct {
				h     uint64
				v     *BlockNotification
				err   error
				retry int
			}

			qch := make(chan *bnq, cap(bnch))
			for i := next; i < latest &&
				len(qch) < cap(qch); i++ {
				qch <- &bnq{i, nil, nil, RPCCallRetry} // fill bch with requests
			}
			bns := make([]*BlockNotification, 0, len(qch))
			for q := range qch {
				switch {
				case q.err != nil:
					if q.retry > 0 {
						q.retry--
						q.v, q.err = nil, nil
						qch <- q
						continue
					}
					r.log.Debugf("receiveLoop: bnq: h=%d:%v, %v", q.h, q.v.Header.Hash(), q.err)
					bns = append(bns, nil)
					if len(bns) == cap(bns) {
						close(qch)
					}

				case q.v != nil:
					bns = append(bns, q.v)
					if len(bns) == cap(bns) {
						close(qch)
					}
				default:
					go func(q *bnq) {
						defer func() {
							time.Sleep(500 * time.Millisecond)
							qch <- q
						}()
						if q.v == nil {
							q.v = &BlockNotification{}
						}
						q.v.Height = (&big.Int{}).SetUint64(q.h)
						q.v.Header, q.err = r.client().GetHeaderByHeight(q.v.Height)
						if q.err != nil {
							q.err = errors.Wrapf(q.err, "GetHeaderByHeight: %v", q.err)
							return
						}
						q.v.Hash = q.v.Header.Hash()
						if q.v.Header.GasUsed > 0 {
							q.v.Receipts, q.err = r.client().GetBlockReceipts(q.v.Hash)
							if q.err == nil {
								receiptsRoot := ethTypes.DeriveSha(q.v.Receipts, trie.NewStackTrie(nil))
								if !bytes.Equal(receiptsRoot.Bytes(), q.v.Header.ReceiptHash.Bytes()) {
									q.err = fmt.Errorf(
										"invalid receipts: remote=%v, local=%v",
										q.v.Header.ReceiptHash, receiptsRoot)
								}
							}
							if q.err != nil {
								q.err = errors.Wrapf(q.err, "GetBlockReceipts: %v", q.err)
								return
							}
						}
					}(q)
				}
			}
			// filter nil
			_bns_, bns := bns, bns[:0]
			for _, v := range _bns_ {
				if v != nil {
					bns = append(bns, v)
				}
			}
			// sort and forward notifications
			if len(bns) > 0 {
				sort.SliceStable(bns, func(i, j int) bool {
					return bns[i].Height.Uint64() < bns[j].Height.Uint64()
				})
				for i, v := range bns {
					if v.Height.Uint64() == next+uint64(i) {
						bnch <- v
					}
				}
			}
		}
	}
}

func (r *receiver) Subscribe(
	ctx context.Context, msgCh chan<- *chain.Message,
	opts chain.SubscribeOptions) (errCh <-chan error, err error) {

	opts.Seq++

	_errCh := make(chan error)

	go func() {
		defer close(_errCh)
		lastHeight := opts.Height - 1
		if err := r.receiveLoop(ctx,
			&BnOptions{
				StartHeight: opts.Height,
				Concurrency: r.opts.SyncConcurrency,
			},
			func(v *BlockNotification) error {
				r.log.WithFields(log.Fields{"height": v.Height}).Debug("block notification")

				if v.Height.Uint64() != lastHeight+1 {
					r.log.Errorf("expected v.Height == %d, got %d", lastHeight+1, v.Height.Uint64())
					return fmt.Errorf(
						"block notification: expected=%d, got=%d",
						lastHeight+1, v.Height.Uint64())
				}

				receipts := r.getRelayReceipts(v)
				for _, receipt := range receipts {
					events := receipt.Events[:0]
					for _, event := range receipt.Events {
						switch {
						case event.Sequence == opts.Seq:
							events = append(events, event)
							opts.Seq++
						case event.Sequence > opts.Seq:
							r.log.WithFields(log.Fields{
								"seq": log.Fields{"got": event.Sequence, "expected": opts.Seq},
							}).Error("invalid event seq")
							return fmt.Errorf("invalid event seq")
						}
					}
					receipt.Events = events
				}
				if len(receipts) > 0 {
					msgCh <- &chain.Message{Receipts: receipts}
				}
				lastHeight++
				return nil
			}); err != nil {
			r.log.Errorf("receiveLoop terminated: %v", err)
			_errCh <- err
		}
	}()

	return _errCh, nil
}

func (r *receiver) getRelayReceipts(v *BlockNotification) []*chain.Receipt {
	sc := common.HexToAddress(r.src.ContractAddress())
	var receipts []*chain.Receipt
	var events []*chain.Event
	for i, receipt := range v.Receipts {
		events := events[:0]
		for _, log := range receipt.Logs {
			if !bytes.Equal(log.Address.Bytes(), sc.Bytes()) {
				continue
			}
			msg, err := r.bmcClient().ParseMessage(ethTypes.Log{
				Data: log.Data, Topics: log.Topics,
			})
			if err == nil {
				events = append(events, &chain.Event{
					Next:     chain.BTPAddress(msg.Next),
					Sequence: msg.Seq.Uint64(),
					Message:  msg.Msg,
				})
			}
		}
		if len(events) > 0 {
			rp := &chain.Receipt{}
			rp.Index, rp.Height = uint64(i), v.Height.Uint64()
			rp.Events = append(rp.Events, events...)
			receipts = append(receipts, rp)
		}
	}
	return receipts
}
