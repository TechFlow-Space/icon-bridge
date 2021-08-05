//! BMC Generic Contract

use btp_common::BTPAddress;
use near_sdk::borsh::{self, BorshDeserialize, BorshSerialize};
//use near_sdk::collections::UnorderedMap;
use crate::bmc_types::*;
use crate::BMC;
use near_sdk::{env, near_bindgen, setup_alloc};

setup_alloc!();
/// This struct implements `Default`: https://github.com/near/near-sdk-rs#writing-rust-contract
#[near_bindgen]
#[derive(BorshDeserialize, BorshSerialize, Clone)]
pub struct BmcGeneric {
    // a network address BMV, i.e. btp://1234.pra/0xabcd
    bmc_btp_address: String,
    bmc_management: String,
}

impl Default for BmcGeneric {
    fn default() -> Self {
        Self {
            bmc_btp_address: "".to_string(),
            bmc_management: "".to_string(),
        }
    }
}

impl BMC for BmcGeneric {
    /*** BMC Generic ***/

    /// Get BMC BTP address
    fn get_bmc_btp_address(&self) -> String {
        self.bmc_btp_address.to_string()
    }

    /// Verify and decode RelayMessage with BMV, and dispatch BTP Messages to registered BSHs
    /// Caller must be a registered relayer.
    fn handle_relay_message(&mut self, prev: &str, msg: &str) {
        let serialized_msgs = self.decode_msg_and_validate_relay(prev, msg);

        // dispatch BTP messages
        for msg in serialized_msgs {
            if let Ok(decoded) = self.clone().decode_btp_message(msg.as_slice()) {
                let message = decoded.clone();
                let _ = BmcMessage {
                    src: decoded.src,
                    dst: decoded.dst,
                    svc: decoded.svc,
                    sn: decoded.sn,
                    message: decoded.message,
                };
                if message.dst == self.get_bmc_btp_address() {
                    self.handle_message_internal(prev, &message);
                } else {
                    let _net = BTPAddress::new(message.dst)
                        .network_address()
                        .expect("Failed to retrieve network address");
                }
            }
        }
    }

    fn decode_msg_and_validate_relay(&mut self, _prev: &str, _msg: &str) -> Vec<Vec<u8>> {
        todo!()
    }

    fn decode_btp_message(&mut self, _rlp: &[u8]) -> Result<BmcMessage, String> {
        todo!()
    }

    fn handle_message_internal(&mut self, _prev: &str, _msg: &BmcMessage) {
        todo!()
    }

    fn send_message_internal(&mut self, _to: &str, _serialized_msg: &[u8]) {
        todo!()
    }

    fn send_error_internal(
        &mut self,
        _prev: &str,
        _msg: BmcMessage,
        _err_code: u32,
        _err_msg: &str,
    ) {
        todo!()
    }

    /// Send the message to a specific network
    /// Caller must be a registered BSH
    fn send_message(&mut self, _to: &str, _svc: &str, _sn: u64, _msg: &[u8]) {
        todo!()
    }

    /// Get status of BMC
    fn get_status(&self, _link: &str) -> LinkStats {
        todo!()
    }

    /*** BMC Management ***/

    /// Update BMC generic
    /// Caller must be an owner of BTP network
    fn set_bmc_generic(&mut self, _addr: &str) {
        unimplemented!()
    }

    /// Add another owner
    /// Caller must be an owner of BTP network
    fn add_owner(&mut self, _owner: &str) {
        unimplemented!()
    }

    /// Remove an existing owner
    /// Caller must be an owner of BTP network
    fn remove_owner(&mut self, _owner: &str) {
        unimplemented!()
    }

    /// Check whether one specific address has owner role
    /// Caller can be ANY
    fn is_owner(&self) -> bool {
        unimplemented!()
    }

    /// Register the smart contract for the service
    /// Caller must be an operator of BTP network
    fn add_service(&mut self, _svc: &str, _addr: &str) {
        unimplemented!()
    }

    /// De-register the smart contract for the service
    /// Caller must be an operator of BTP network
    fn remove_service(&mut self, _svc: &str) {
        unimplemented!()
    }

    /// Register BMV for the network
    /// Caller must be an operator of BTP network
    fn add_verifier(&mut self, _net: &str, _addr: &str) {
        unimplemented!()
    }

    /// De-register BMV for the network
    /// Caller must be an operator of BTP network
    fn remove_verifier(&mut self, _net: &str) {
        unimplemented!()
    }

    /// Initialize status information for the link
    /// Caller must be an operator of BTP network
    fn add_link(&mut self, _link: &str) {
        unimplemented!()
    }

    /// Set the link and status information
    /// Caller must be an operator of BTP network
    fn set_link(&mut self, _link: &str, _block_interval: u128, _max_agg: u128, _delay_limit: u128) {
        unimplemented!()
    }

    /// Remove the link and status information
    /// Caller must be an operator of BTP network
    fn remove_link(&mut self, _link: &str) {
        unimplemented!()
    }

    /// Add route to the BMC
    /// Caller must be an operator of BTP network
    fn add_route(&mut self, _dst: &str, _link: &str) {
        unimplemented!()
    }

    /// Remove route to the BMC
    /// Caller must be an operator of BTP network
    fn remove_route(&mut self, _dst: &str) {
        unimplemented!()
    }

    /// Register Relay for the network
    /// Caller must be an operator of BTP network
    fn add_relay(&mut self, _link: &str, _addrs: &[&str]) {
        unimplemented!()
    }

    /// Unregister Relay for the network
    /// Caller must be an operator of BTP network
    fn remove_relay(&mut self, _link: &str, _addrs: &[&str]) {
        unimplemented!()
    }

    /// Get registered services
    /// Returns an array of services
    fn get_services(&self) -> Vec<Service> {
        unimplemented!()
    }

    /// Get registered verifiers
    /// Returns an array of verifiers
    fn get_verifiers(&self) -> Vec<Verifier> {
        unimplemented!()
    }

    /// Get registered links
    /// Returns an array of links (BTP addresses of the BMCs)
    fn get_links(&self) -> Vec<String> {
        unimplemented!()
    }

    /// Get routing information
    /// Returns an array of routes
    fn get_routes(&self) -> Vec<Route> {
        unimplemented!()
    }

    /// Get registered relays
    /// Returns a list of relays
    fn get_relays(&self, _link: &str) -> Vec<String> {
        unimplemented!()
    }

    /// Get BSH services by name. Only called by BMC generic
    /// Returns BSH service address
    fn get_bsh_service_by_name(&self, _service_name: &str) -> String {
        unimplemented!()
    }

    /// Get BMV services by net. Only called by BMC generic
    /// Returns BMV service address
    fn get_bmv_service_by_net(&self, _net: &str) -> String {
        unimplemented!()
    }

    /// Get link info. Only called by BMC generic
    /// Returns link info
    fn get_link(&self, _to: &str) -> Link {
        unimplemented!()
    }

    /// Get rotation sequence by link. Only called by BMC generic
    /// Returns rotation sequence
    fn get_link_rx_seq(&self, _prev: &str) -> u128 {
        unimplemented!()
    }

    /// Get transaction sequence by link. Only called by BMC generic
    /// Returns transaction sequence
    fn get_link_tx_seq(&self, _prev: &str) -> u128 {
        unimplemented!()
    }

    /// Get relays by link. Only called by BMC generic
    /// Returns a list of relays' addresses
    fn get_link_relays(&self, _prev: &str) -> Vec<String> {
        unimplemented!()
    }

    /// Get relays status by link. Only called by BMC generic
    /// Returns relay status of all relays
    fn get_relay_status_by_link(&self, _prev: &str) -> Vec<RelayStats> {
        unimplemented!()
    }

    /// Update rotation sequence by link. Only called by BMC generic
    fn update_link_rx_seq(&mut self, _prev: &str, _val: u128) {
        unimplemented!()
    }

    /// Increase transaction sequence by 1
    fn update_link_tx_seq(&mut self, _prev: &str) {
        unimplemented!()
    }

    /// Add a reachable BTP address to link. Only called by BMC generic
    fn update_link_reachable(&mut self, _prev: &str, _to: &str) {
        unimplemented!()
    }

    /// Remove a reachable BTP address. Only called by BMC generic
    fn delete_link_reachable(&mut self, _prev: &str, _index: u128) {
        unimplemented!()
    }

    /// Update relay status. Only called by BMC generic
    fn update_relay_stats(&mut self, _relay: &str, _block_count_val: u128, _msg_count_val: u128) {
        unimplemented!()
    }

    /// Resolve next BMC. Only called by BMC generic
    /// Returns BTP address of next BMC and destined BMC
    fn resolve_route(&mut self, _dst_net: &str) -> (String, String) {
        unimplemented!()
    }

    /// Rotate relay for relay address. Only called by BMC generic
    /// Returns relay address
    fn rotate_relay(
        &mut self,
        _link: &str,
        _current_height: u128,
        _relay_msg_height: u128,
        _has_msg: bool,
    ) -> String {
        unimplemented!()
    }
}

#[near_bindgen]
impl BmcGeneric {
    pub const UNKNOWN_ERR: u32 = 0;
    pub const BMC_ERR: u32 = 10;
    pub const BMV_ERR: u32 = 25;
    pub const BSH_ERR: u32 = 40;

    #[init]
    pub fn new(network: &str, bmc_mgt_addr: &str) -> Self {
        let bmc_btp_address = format!("btp://{}/{}", network, env::current_account_id());
        Self {
            bmc_btp_address,
            bmc_management: bmc_mgt_addr.to_string(),
        }
    }
}
