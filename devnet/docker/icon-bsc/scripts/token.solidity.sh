#!/bin/sh
source utils.sh

eth_blocknumber() {
  curl -s -X POST $BSC_RPC_URI --header 'Content-Type: application/json' \
    --data-raw '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[], "id": 1}' | jq -r .result | xargs printf "%d\n"
}

deploy_solidity_bmc() {
  cd $CONTRACTS_DIR/solidity/bmc
  if [ ! -f $CONFIG_DIR/bsc.deploy.bmc ]; then
    rm -rf contracts/test build .openzeppelin
    truffle compile --all
    echo "deploying solidity bmc"
    set +e
    for i in $(seq 1 20); do
      BMC_BTP_NET=$BSC_BMC_NET \
      truffle migrate --network bsc --compile-none
      if [ $? == 0 ]; then
          break
      fi
      echo "Retry: "$i
    done
    set -e
    eth_blocknumber > $CONFIG_DIR/bsc.chain.height
    generate_metadata "BMC"
    echo -n "bmc" > $CONFIG_DIR/bsc.deploy.bmc
  fi
} 

deploy_solidity_bts() {
  echo "deploying solidity bts"
  cd $CONTRACTS_DIR/solidity/bts
  if [ ! -f $CONFIG_DIR/bsc.deploy.bts ]; then
    rm -rf contracts/test build .openzeppelin
    truffle compile --all
    set +e
    for i in $(seq 1 20); do
      BSH_COIN_NAME="BNB" \
      BSH_COIN_FEE=100 \
      BSH_FIXED_FEE=5000 \
      BMC_PERIPHERY_ADDRESS="$(cat $CONFIG_DIR/bsc.addr.bmcperiphery)" \
      truffle migrate --compile-none --network bsc --f 1 --to 1
      if [ $? == 0 ]; then
        break
      fi
      echo "Retry: "$i
    done
    set -e
    generate_metadata "BTS"
    echo -n "bts" > $CONFIG_DIR/bsc.deploy.bts
  fi
} 

deploy_solidity_token() {
  echo "deploying solidity token " $1
  cd $CONTRACTS_DIR/solidity/bts
  if [ ! -f $CONFIG_DIR/bsc.deploy.coin$1 ]; then
    set +e
    for i in $(seq 1 20); do
      BSH_COIN_NAME=$1 \
      BSH_COIN_SYMBOL=$2 \
      BSH_DECIMALS=18 \
      BSH_INITIAL_SUPPLY=100000 \
      truffle migrate --compile-none --network bsc --f 3 --to 3
      if [ $? == 0 ]; then
        break
      fi
      echo "Retry: "$i
    done
    set -e
    jq -r '.networks[] | .address' build/contracts/ERC20TKN.json >$CONFIG_DIR/bsc.addr.$1
    wait_for_file $CONFIG_DIR/bsc.addr.$1
    echo -n $1 > $CONFIG_DIR/bsc.deploy.coin$1
  fi
}

configure_solidity_add_bts_service() {
  echo "adding bts service into BMC"
  cd $CONTRACTS_DIR/solidity/bmc
  if [ ! -f $CONFIG_DIR/bsc.configure.addbts ]; then
    tx=$(truffle exec --network bsc "$SCRIPTS_DIR"/bmc.js \
      --method addService --name "bts" --addr $(cat $CONFIG_DIR/bsc.addr.btsperiphery))
    echo "$tx" >$CONFIG_DIR/tx/addService.bsc
    isTrue=$(echo "$tx" | grep "status: true" | wc -l)
    if [ "$isTrue" == "1" ];
    then
      echo "addedBTS" > $CONFIG_DIR/bsc.configure.addbts
    else
      echo "Error Addding BTS"
      return 1
    fi  
  fi
}
 
configure_solidity_add_bmc_owner() {
  echo "adding bmc owner"
  BSC_BMC_USER=$(cat $CONFIG_DIR/keystore/bsc.bmc.wallet.json | jq -r .address)
  cd $CONTRACTS_DIR/solidity/bmc
  tx=$(truffle exec --network bsc "$SCRIPTS_DIR"/bmc.js \
    --method isOwner --addr "0x${BSC_BMC_USER}")
  ownerExists=$(echo "$tx" | grep "IsOwner: true" | wc -l)
  if [ "$ownerExists" == "0" ];then
    tx=$(truffle exec --network bsc "$SCRIPTS_DIR"/bmc.js \
      --method addOwner --addr "0x${BSC_BMC_USER}")
    echo "$tx" >$CONFIG_DIR/tx/addBmcUser.bsc
    ownerAdded=$(echo "$tx" | grep "status: true" | wc -l)
    if [ "$ownerAdded" != "1" ]; then
      echo "Error adding bmc owner"
      return 1 
    fi
  fi
}
 
 configure_solidity_add_bts_owner() {
  echo "adding bts owner"
  BSC_BTS_USER=$(cat $CONFIG_DIR/keystore/bsc.bts.wallet.json | jq -r .address)
  cd $CONTRACTS_DIR/solidity/bts
  tx=$(truffle exec --network bsc "$SCRIPTS_DIR"/bts.js \
    --method isOwner --addr "0x${BSC_BTS_USER}")
  ownerExists=$(echo "$tx" | grep "IsOwner: true" | wc -l)
  if [ "$ownerExists" == "0" ];then
    tx=$(truffle exec --network bsc "$SCRIPTS_DIR"/bts.js \
      --method addOwner --addr "0x${BSC_BTS_USER}")
    echo "$tx" >$CONFIG_DIR/tx/addBtsUser.bsc
    ownerAdded=$(echo "$tx" | grep "status: true" | wc -l)
    if [ "$ownerAdded" != "1" ]; then
      echo "Error adding bts owner"
      return 1
    fi  
  fi
}

configure_solidity_set_fee_ratio() {
  echo "SetFee Ratio"
  cd $CONTRACTS_DIR/solidity/bts
  if [ ! -f $CONFIG_DIR/bsc.configure.setfee ]; then
    tx=$(truffle exec --network bsc "$SCRIPTS_DIR"/bts.js \
      --method setFeeRatio --name BNB --feeNumerator 100 --fixedFee 5000)
    echo "$tx" >$CONFIG_DIR/tx/setFee.bsc
    status=$(echo "$tx" | grep "status: true" | wc -l)
    if [ "$status" != "1" ]; 
    then
      echo "Error setting fee ratio"
      return 1
    else
      echo "feeSet" > $CONFIG_DIR/bsc.configure.setfee
    fi  
  fi
}
 
add_icon_link() {
  echo "adding icon link $(cat $CONFIG_DIR/icon.addr.bmcbtp)"
  cd $CONTRACTS_DIR/solidity/bmc
  if [ ! -f $CONFIG_DIR/bsc.configure.addLink ]; then
    tx=$(truffle exec --network bsc "$SCRIPTS_DIR"/bmc.js \
    --method addLink --link $(cat $CONFIG_DIR/icon.addr.bmcbtp) --blockInterval 3000 --maxAggregation 2 --delayLimit 3)
    echo "$tx" >$CONFIG_DIR/tx/addLink.bsc
    status=$(echo "$tx" | grep "status: true" | wc -l)
    if [ "$status" != "1" ]; 
    then
      echo "Error adding link"
      return 1
    else
      echo "addedLink" > $CONFIG_DIR/bsc.configure.addLink
    fi 
  fi
}

set_link_height() {
  echo "set link height"
  cd $CONTRACTS_DIR/solidity/bmc
  if [ ! -f $CONFIG_DIR/bsc.configure.setLink ]; then
    tx=$(truffle exec --network bsc "$SCRIPTS_DIR"/bmc.js \
    --method setLinkRxHeight --link $(cat $CONFIG_DIR/icon.addr.bmcbtp) --height $(cat $CONFIG_DIR/icon.chain.height))
    echo "$tx" >$CONFIG_DIR/tx/setLinkRxHeight.bsc
      status=$(echo "$tx" | grep "status: true" | wc -l)
    if [ "$status" != "1" ]; 
    then
      echo "Error setting link"
      return 1
    else
      echo "setLink" > $CONFIG_DIR/bsc.configure.setLink
    fi 
  fi
}

add_icon_relay() {
  echo "adding icon relay"
  BSC_RELAY_USER=$(cat $CONFIG_DIR/keystore/bsc.bmr.wallet.json | jq -r .address)
  cd $CONTRACTS_DIR/solidity/bmc
  if [ ! -f $CONFIG_DIR/bsc.configure.addRelay ]; then
    tx=$(truffle exec --network bsc "$SCRIPTS_DIR"/bmc.js \
      --method addRelay --link $(cat $CONFIG_DIR/icon.addr.bmcbtp) --addr "0x${BSC_RELAY_USER}")
    echo "$tx" >$CONFIG_DIR/tx/addRelay.bsc
    status=$(echo "$tx" | grep "status: true" | wc -l)
    if [ "$status" != "1" ]; 
    then
      echo "Error adding relay"
      return 1
    else
      echo "addedRelay" > $CONFIG_DIR/bsc.configure.addRelay
    fi 
  fi
} 


bsc_register_wrapped_coin() {
  echo "bts: Register Wrapped Coin " $1
  local bts_fee_numerator=100
  local bts_fixed_fee=5000
  cd $CONTRACTS_DIR/solidity/bts
  if [ ! -f $CONFIG_DIR/bsc.register.coin$1 ]; then
    tx=$(truffle exec --network bsc "$SCRIPTS_DIR"/bts.js \
      --method register --name "$1" --symbol "$2" --decimals 18 --addr "0x0000000000000000000000000000000000000000" \
      --feeNumerator ${bts_fee_numerator} --fixedFee ${bts_fixed_fee})
    echo "$tx" >$CONFIG_DIR/tx/register.$1.bsc
    status=$(echo "$tx" | grep "status: true" | wc -l)
    if [ "$status" != "1" ]; 
    then
      echo "Error registering wrapped coin " $1
      return 1
    else
      echo "registered "$1 > $CONFIG_DIR/bsc.register.coin$1
    fi 
  fi
}

bsc_register_native_token() {
  local bts_fee_numerator=100
  local bts_fixed_fee=5000
  local addr=$(cat $CONFIG_DIR/bsc.addr.$1) 
  cd $CONTRACTS_DIR/solidity/bts
  if [ ! -f $CONFIG_DIR/bsc.register.coin$1 ]; then
    echo "bts: Register NativeCoin " $1
    tx=$(truffle exec --network bsc "$SCRIPTS_DIR"/bts.js \
      --method register --name "$1" --symbol "$2" --decimals 18 --addr $addr --feeNumerator $bts_fee_numerator --fixedFee ${bts_fixed_fee})
    echo "$tx" >$CONFIG_DIR/tx/register.$1.bsc
    status=$(echo "$tx" | grep "status: true" | wc -l)
    if [ "$status" != "1" ]; 
    then
      echo "Error registering native token " $1
      return 1
    else
      echo "registered "$1 > $CONFIG_DIR/bsc.register.coin$1
    fi 
  fi
}

get_coinID() {
  echo "getCoinID " $1
  cd $CONTRACTS_DIR/solidity/bts
  tx=$(truffle exec --network bsc "$SCRIPTS_DIR"/bts.js \
    --method coinId --coinName "$1")
  coinId=$(echo "$tx" | grep "coinId:" | sed -e "s/^coinId: //")
  exists=$(echo $coinId | wc -l)
  if [ "$exists" != "1" ]; 
  then
    echo "Error getting coinID " $1
    return 1
  else 
    echo "$coinId" >$CONFIG_DIR/bsc.addr.coin$1
  fi 
}

generate_metadata() {
  option=$1
  case "$option" in

  BMC)
    echo "###################  Generating BMC Solidity metadata ###################"

    local BMC_ADDRESS=$(jq -r '.networks[] | .address' build/contracts/BMCPeriphery.json)
    echo btp://$BSC_BMC_NET/"${BMC_ADDRESS}" >$CONFIG_DIR/bsc.addr.bmcbtp
    echo "${BMC_ADDRESS}" >$CONFIG_DIR/bsc.addr.bmcperiphery
    wait_for_file $CONFIG_DIR/bsc.addr.bmcperiphery

    jq -r '.networks[] | .address' build/contracts/BMCManagement.json >$CONFIG_DIR/bsc.addr.bmcmanagement
    wait_for_file $CONFIG_DIR/bsc.addr.bmcmanagement
    echo "DONE."
    ;;

  \
    BTS)
    echo "################### Generating BTS  Solidity metadata ###################"

    jq -r '.networks[] | .address' build/contracts/BTSCore.json >$CONFIG_DIR/bsc.addr.btscore
    wait_for_file $CONFIG_DIR/bsc.addr.btscore
    jq -r '.networks[] | .address' build/contracts/BTSPeriphery.json >$CONFIG_DIR/bsc.addr.btsperiphery
    wait_for_file $CONFIG_DIR/bsc.addr.btsperiphery
    echo "DONE."
    ;;
  *)
    echo "Invalid option for generating meta data"
    ;;
  esac
}
