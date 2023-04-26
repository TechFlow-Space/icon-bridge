import smartpy as sp

types = sp.io.import_script_from_url("file:./contracts/src/Types.py")
strings = sp.io.import_script_from_url("file:./contracts/src/String.py")
rlp_encode = sp.io.import_script_from_url("file:./contracts/src/RLP_encode_struct.py")
parse_addr = sp.io.import_script_from_url("file:./contracts/src/parse_address.py")

class BTPPreiphery(sp.Contract):
    service_name = sp.string("bts")

    RC_OK = sp.nat(0)
    RC_ERR = sp.nat(1)

    MAX_BATCH_SIZE = sp.nat(15)

    def __init__(self, bmc_address, bts_core_address):
        self.update_initial_storage(
            bmc=bmc_address,
            bts_core=bts_core_address,
            blacklist=sp.map(tkey=sp.TAddress, tvalue=sp.TBool),
            token_limit=sp.map(tkey=sp.TString, tvalue=sp.TNat),
            requests=sp.big_map(tkey=sp.TNat, tvalue=types.Types.PendingTransferCoin),
            serial_no = sp.nat(0),
            number_of_pending_requests = sp.nat(0)
        )

    def only_bmc(self):
        sp.verify(sp.sender == self.data.bmc, "Unauthorized")

    def only_btp_core(self):
        sp.verify(sp.sender == self.data.bts_core, "Unauthorized")

    @sp.onchain_view()
    def has_pending_request(self):
        """

        :return: boolean
        """
        sp.result(self.data.number_of_pending_requests != sp.nat(0))

    @sp.entry_point
    def add_to_blacklist(self, params):
        """

        :param params: List of addresses to be blacklisted
        :return:
        """
        sp.set_type(params, sp.TList(sp.TString))
        # sp.verify(sp.sender == sp.self_address, "Unauthorized")
        sp.verify(sp.len(params) <= self.MAX_BATCH_SIZE, "BatchMaxSizeExceed")

        sp.for itm in params:
            parsed_addr = parse_addr.str_to_addr(itm)
            with sp.if_(parsed_addr != sp.address("tz1ZZZZZZZZZZZZZZZZZZZZZZZZZZZZNkiRg")):
                self.data.blacklist[parsed_addr] = True
            with sp.else_():
                sp.failwith("InvalidAddress")


    @sp.entry_point
    def remove_from_blacklist(self, params):
        """
        :param params: list of address strings
        :return:
        """
        sp.set_type(params, sp.TList(sp.TString))

        # sp.verify(sp.sender == sp.self_address, "Unauthorized")
        sp.verify(sp.len(params) <= self.MAX_BATCH_SIZE, "BatchMaxSizeExceed")

        sp.for itm in params:
            parsed_addr = parse_addr.str_to_addr(itm)
            with sp.if_(parsed_addr != sp.address("tz1ZZZZZZZZZZZZZZZZZZZZZZZZZZZZNkiRg")):
                sp.verify(self.data.blacklist.contains(parsed_addr), "UserNotFound")
                sp.verify(self.data.blacklist.get(parsed_addr) == True, "UserNotBlacklisted")
                del self.data.blacklist[parsed_addr]
            with sp.else_():
                sp.failwith("InvalidAddress")

    @sp.entry_point
    def set_token_limit(self, coin_names, token_limit):
        """
        :param coin_names: list of coin names
        :param token_limit: list of token limits
        :return:
        """
        sp.set_type(coin_names, sp.TMap(sp.TNat, sp.TString))
        sp.set_type(token_limit, sp.TMap(sp.TNat, sp.TNat))

        # uncomment later
        # sp.verify((sp.sender == sp.self_address )| (sp.sender == self.data.bts_core), "Unauthorized")
        sp.verify(sp.len(coin_names) == sp.len(token_limit), "InvalidParams")
        sp.verify(sp.len(coin_names) <= self.MAX_BATCH_SIZE, "BatchMaxSizeExceed")

        sp.for i in sp.range(0, sp.len(coin_names)):
            self.data.token_limit[coin_names[i]] = token_limit[i]


    @sp.entry_point
    def send_service_message(self, _from, to, coin_names, values, fees):
        """
        Send service message to BMC
        :param _from: from address
        :param to: to address
        :param coin_names:
        :param values:
        :param fees:
        :return:
        """

        sp.set_type(_from, sp.TAddress)
        sp.set_type(to, sp.TString)
        sp.set_type(coin_names, sp.TMap(sp.TNat, sp.TString))
        sp.set_type(values, sp.TMap(sp.TNat, sp.TNat))
        sp.set_type(fees, sp.TMap(sp.TNat, sp.TNat))

        self.only_btp_core()

        to_network, to_address = sp.match_pair(strings.split_btp_address(to))

        assets = sp.compute(sp.map(tkey=sp.TNat, tvalue=types.Types.Asset))
        assets_details = sp.compute(sp.map(tkey=sp.TNat, tvalue=types.Types.AssetTransferDetail))
        sp.for i in sp.range(sp.nat(0), sp.len(coin_names)):
            assets[i]=sp.record(
                coin_name=coin_names[i],
                value=values[i]
            )
            assets_details[i] = sp.record(
                coin_name=coin_names[i],
                value=values[i],
                fee=fees[i]
            )

        self.data.serial_no += 1

        start_from = parse_addr.add_to_str(_from)

        send_message_args_type = sp.TRecord(to=sp.TString, svc=sp.TString, sn=sp.TNat, msg=sp.TBytes)
        send_message_entry_point = sp.contract(send_message_args_type, self.data.bmc, "send_message").open_some()
        send_message_args = sp.record(
            to=to_network, svc=self.service_name, sn=self.data.serial_no,
            msg=rlp_encode.encode_service_message(sp.compute(sp.record(serviceType=(sp.variant("REQUEST_COIN_TRANSFER", 0)),
                                  data=rlp_encode.encode_transfer_coin_msg(sp.compute(sp.record(from_addr=start_from, to=to_address, assets=assets)))
                                            )
                                    )
                        )
        )
        sp.transfer(send_message_args, sp.tez(0), send_message_entry_point)

        # push pending tx into record list
        self.data.requests[self.data.serial_no] = sp.record(
            from_addr=start_from, to=to, coin_names=coin_names, amounts=values, fees=fees
        )
        self.data.number_of_pending_requests +=sp.nat(1)
        sp.emit(sp.record(from_address=_from, to=to, serial_no=self.data.serial_no, assets_details=assets_details), tag="TransferStart")


    @sp.entry_point
    def handle_btp_message(self, _from, svc, sn, msg):
        """
        BSH handle BTP message from BMC contract
        :param _from: An originated network address of a request
        :param svc: A service name of BSH contract
        :param sn: A serial number of a service request
        :param msg: An RLP message of a service request/service response
        :return:
        """

        sp.set_type(_from, sp.TString)
        sp.set_type(svc, sp.TString)
        sp.set_type(sn, sp.TNat)
        sp.set_type(msg, sp.TBytes)

        # self.only_bmc()
        # TODO: implement try catch

        sp.verify(svc == self.service_name, "InvalidSvc")
        err_msg = sp.local("error", "")

        # byt= sp.pack(sp.record(serviceType=sp.variant("REQUEST_COIN_TRANSFER", 0), data=sp.bytes("0x0dae11")))
        # sp.trace(byt)

        sm = sp.unpack(msg, t=types.Types.ServiceMessage).open_some()
        # sm=sp.record(serviceType=sp.variant("REQUEST_COIN_TRANSFER", 0), data=sp.bytes("0x0dae11"))
        sp.trace(sm.serviceType)

        # service_type = sm.serviceType
        # service_type = sp.set_type_expr(service_type, types.Types.s_type)
        # sp.trace(service_type)

        with sm.serviceType.match_cases() as arg:
            with arg.match("REQUEST_COIN_TRANSFER") as a1:
                # TODO: decode tc
                # tc = sp.unpack(sm.data, t=types.Types.TransferCoin)
                # parsed_addr = parse_addr.str_to_addr(tc.to)
                # remove below parsed_addr after tc decode implemented
                parsed_addr = sp.address("tz1ZZZZZZZZZZZZZZZZZZZZZZZZZZZZNkiRg")
                with sp.if_(parsed_addr != sp.address("tz1ZZZZZZZZZZZZZZZZZZZZZZZZZZZZNkiRg")):
                    pass
                    # TODO: implement handle request service

                with sp.else_():
                    err_msg.value = "InvalidAddress"

                self.send_response_message(sp.variant("RESPONSE_HANDLE_SERVICE", 2), _from, sn, "", self.RC_OK)
                # sp.emit(sp.record(from_address=_from, to=tc.to, serial_no=self.data.serial_no, assets_details=tc.assets))

            with arg.match("BLACKLIST_MESSAGE") as a2:

                bm = sp.unpack(sm.data, types.Types.BlacklistMessage).open_some()
                # bm=sp.record(serviceType=sp.variant("ADD_TO_BLACKLIST", 0), addrs={0:"tz1e2HPzZWBsuExFSM4XDBtQiFnaUB5hiPnW"},
                #              net="Tezos")
                addresses = bm.addrs

                with bm.serviceType.match_cases() as b_agr:
                    with b_agr.match("ADD_TO_BLACKLIST") as b_val_1:
                        # self.add_to_blacklist(addresses)
                        self.send_response_message(sp.variant("BLACKLIST_MESSAGE", 3), _from, sn, "AddedToBlacklist", self.RC_OK)

                    with b_agr.match("REMOVE_FROM_BLACKLIST") as b_val_2:
                        # self.remove_from_blacklist(addresses)
                        self.send_response_message(sp.variant("BLACKLIST_MESSAGE", 3), _from, sn, "RemovedFromBlacklist", self.RC_OK)

            with arg.match("CHANGE_TOKEN_LIMIT") as a3:
                # TODO: implement decodeTokenLimitMsg
                tl = sp.unpack(sm.data, t=types.Types.TokenLimitMessage).open_some()
                # tl = sp.record(coin_name={0:"Tok1"},token_limit={0:5}, net="Tezos")
                coin_names = sp.map({0: tl.coin_name})
                token_limits = sp.map({0: tl.token_limit})

                # self.set_token_limit(coin_names, token_limits)
                self.send_response_message(sp.variant("CHANGE_TOKEN_LIMIT", 4), _from, sn, "ChangeTokenLimit",self.RC_OK)

            with arg.match("RESPONSE_HANDLE_SERVICE") as a4:
                # TODO: implement decodeResponse
                response = sp.unpack(sm.data, types.Types.Response).open_some()
                # response = sp.record(code=2, message="Test")

                self.handle_response_service(sn, response.code, response.message)

            with arg.match("UNKNOWN_TYPE") as a5:
                sp.emit(sp.record(_from=_from, sn=sn))

        # using if else
        # with sp.if_(sm.serviceType == types.Types.ServiceType.open_variant("REQUEST_COIN_TRANSFER")):
            # tc = sp.unpack(sm.data, t=types.Types.TransferCoin)
            # TDo: check address and handle request service
            # # with sp.if_(self.check_parse_address(tc.to)):
            # #     with sp.if_(self.handle_request_service(tc.to, tc.assets)):
            # self.send_response_message(types.Types.ServiceType.open_variant("REQUEST_COIN_TRANSFER"), _from, sn, "", self.RC_OK)
            # sp.emit(sp.record(from_address=_from, to=tc.to, serial_no=self.data.serial_no, assets_details=tc.assets))
            #     # with sp.else_():
            #     #     err_msg = "ErrorWhileMinting"
            # # with sp.else_():
            # err_msg = "InvalidAddress"
            # sp.trace(err_msg)
            # self.send_response_message(types.Types.ServiceType.open_variant("REQUEST_COIN_TRANSFER"), _from, sn, err_msg, self.RC_ERR)


    @sp.entry_point
    def handle_btp_error(self, svc, sn, code, msg):
        """
        BSH handle BTP Error from BMC contract
        :param svc: A service name of BSH contract
        :param sn: A serial number of a service request
        :param code: A response code of a message (RC_OK / RC_ERR)
        :param msg: A response message
        :return:
        """

        sp.set_type(svc, sp.TString)
        sp.set_type(sn, sp.TNat)
        sp.set_type(code, sp.TNat)
        sp.set_type(msg, sp.TString)

        # self.only_bmc()

        sp.verify(svc == self.service_name, "InvalidSvc")
        sp.verify(sp.len(sp.pack(self.data.requests[sn].from_addr)) != 0, "InvalidSN")

        emit_msg= sp.concat(["errCode: ", parse_addr.Utils.String.of_int(sp.to_int(code)),", errMsg: ", msg])
        self.handle_response_service(sn, self.RC_ERR, emit_msg)

    def handle_response_service(self, sn, code, msg):
        """

        :param sn:
        :param code:
        :param msg:
        :return:
        """
        sp.set_type(sn, sp.TNat)
        sp.set_type(code, sp.TNat)
        sp.set_type(msg, sp.TString)

        caller = sp.local("caller", parse_addr.str_to_addr(self.data.requests[sn].from_addr), sp.TAddress).value
        loop = sp.local("loop", sp.len(self.data.requests[sn].coin_names), sp.TNat).value
        sp.verify(loop <= self.MAX_BATCH_SIZE, "BatchMaxSizeExceed")

        sp.for i in sp.range(0, loop):
            # inter score call
            handle_response_service_args_type = sp.TRecord(
                requester=sp.TAddress, coin_name=sp.TString, value=sp.TNat, fee=sp.TNat, rsp_code=sp.TNat
            )
            handle_response_service_entry_point = sp.contract(handle_response_service_args_type, self.data.bts_core, "handle_response_service").open_some("invalid call")
            handle_response_service_args = sp.record(
                requester=caller, coin_name=self.data.requests[sn].coin_names[i], value=self.data.requests[sn].amounts[i],
                fee=self.data.requests[sn].fees[i], rsp_code=code
            )
            sp.transfer(handle_response_service_args, sp.tez(0), handle_response_service_entry_point)

        del self.data.requests[sn]
        self.data.number_of_pending_requests = sp.as_nat(self.data.number_of_pending_requests-1)

        sp.emit(sp.record(caller=caller, sn=sn, code=code, msg=msg), tag="TransferEnd")

    @sp.entry_point
    def handle_request_service(self, to, assets):
        """
        Handle a list of minting/transferring coins/tokens
        :param to: An address to receive coins/tokens
        :param assets:  A list of requested coin respectively with an amount
        :return:
        """
        sp.set_type(to, sp.TString)
        sp.set_type(assets, sp.TMap(sp.TNat, types.Types.Asset))

        # sp.verify(sp.sender == sp.self_address, "Unauthorized")
        sp.verify(sp.len(assets) <= self.MAX_BATCH_SIZE, "BatchMaxSizeExceed")

        parsed_to = parse_addr.str_to_addr(to)
        sp.for i in sp.range(0, sp.len(assets)):
            valid_coin = sp.view("is_valid_coin", self.data.bts_core, assets[i].coin_name, t=sp.TBool).open_some()
            # sp.verify(valid_coin == True, "UnregisteredCoin")

            # in case of on chain view
            check_transfer = sp.view("check_transfer_restrictions", sp.self_address, sp.record(
                coin_name=assets[i].coin_name,user=parsed_to, value=assets[i].value), t=sp.TBool).open_some()
            sp.verify(check_transfer == True, "FailCheckTransfer")

            # TODO: implement try

            # inter score call
            mint_args_type = sp.TRecord(
                to=sp.TAddress, coin_name=sp.TString, value=sp.TNat
            )
            mint_args_type_entry_point = sp.contract(mint_args_type, self.data.bts_core, "mint").open_some()
            mint_args = sp.record(
                to=parsed_to, coin_name=assets[i].coin_name, value=assets[i].value
            )
            sp.transfer(mint_args, sp.tez(0), mint_args_type_entry_point)


    def send_response_message(self, service_type, to, sn, msg, code):
        """

        :param service_type:
        :param to:
        :param sn:
        :param msg:
        :param code:
        :return:
        """
        sp.set_type(service_type, types.Types.ServiceType)
        sp.set_type(to, sp.TString)
        sp.set_type(sn, sp.TNat)
        sp.set_type(msg, sp.TString)
        sp.set_type(code, sp.TNat)

        sp.trace("in send_response_message")

        send_message_args_type = sp.TRecord(
            to=sp.TString, svc=sp.TString, sn=sp.TNat, msg=sp.TBytes
        )
        send_message_entry_point = sp.contract(send_message_args_type, self.data.bmc, "send_message").open_some()
        send_message_args = sp.record(to=to, svc=self.service_name, sn=self.data.serial_no,
                                      msg=sp.pack(sp.record(serviceType=service_type, data=sp.pack(sp.record(code=code, message=msg))))
                                      )
        sp.transfer(send_message_args, sp.tez(0), send_message_entry_point)


    @sp.entry_point
    def handle_fee_gathering(self, fa, svc):
        """
        BSH handle Gather Fee Message request from BMC contract
        :param fa: A BTP address of fee aggregator
        :param svc: A name of the service
        :return:
        """
        sp.set_type(fa, sp.TString)
        sp.set_type(svc, sp.TString)

        # self.only_bmc()
        sp.verify(svc == self.service_name, "InvalidSvc")

        strings.split_btp_address(fa)

        # call transfer_fees of BTS_Core
        transfer_fees_args_type = sp.TString
        transfer_fees_entry_point = sp.contract(transfer_fees_args_type, self.data.bts_core, "transfer_fees").open_some()
        sp.transfer(fa, sp.tez(0), transfer_fees_entry_point)


    @sp.onchain_view()
    def check_transfer_restrictions(self, params):
        """

        :param params: Record of coin transfer details
        :return:
        """
        sp.set_type(params, sp.TRecord(coin_name=sp.TString, user=sp.TAddress, value=sp.TNat))

        sp.verify(self.data.blacklist.contains(params.user) == False, "Blacklisted")
        sp.verify(self.data.token_limit[params.coin_name] >= params.value, "LimitExceed")
        sp.result(True)



@sp.add_test(name="Counter")
def test():
    alice = sp.test_account("Alice")
    admin = sp.test_account("Admin")

    scenario = sp.test_scenario()
    counter = BTPPreiphery(alice.address, admin.address)
    scenario += counter

    counter.add_to_blacklist(["tz1e2HPzZWBsuExFSM4XDBtQiFnaUB5hiPnW"]).run(sender=alice)
    counter.send_service_message(sp.record(_from=sp.address("tz1e2HPzZWBsuExFSM4XDBtQiFnaUB5hiPnW"), to="btp://77.tezos/tz1e2HPzZWBsuExFSM4XDBtQiFnaUB5hiPnW",
                                           coin_names={0:"Tok1"}, values={0:sp.nat(10)}, fees={0:sp.nat(2)})).run(
        sender=admin
    )
    counter.handle_btp_error(sp.record(svc= "bts", code=sp.nat(2), sn=sp.nat(1), msg="test 1")).run(
        sender=admin
    )

    counter.set_token_limit(sp.record(coin_names={0:"Tok2"}, token_limit={0:sp.nat(5)})).run(sender=admin)

    counter.handle_request_service(sp.record(to= "tz1VA29GwaSA814BVM7AzeqVzxztEjjxiMEc", assets={0:
                                             sp.record(coin_name="Tok2", value=sp.nat(4))})).run(
        sender=admin
    )

    counter.handle_fee_gathering(sp.record(fa="btp://77.tezos/tz1e2HPzZWBsuExFSM4XDBtQiFnaUB5hiPnW", svc="bts")).run(sender=admin)

    # counter.handle_btp_message(sp.record(_from="tz1e2HPzZWBsuExFSM4XDBtQiFnaUB5hiPnW", svc="bts", sn=sp.nat(4),
    #                                      msg=sp.bytes("0x0507070a000000030dae110000") )).run(sender=admin)


sp.add_compilation_target("bts_periphery", BTPPreiphery(bmc_address=sp.address("tz1e2HPzZWBsuExFSM4XDBtQiFnaUB5hiPnW"),
                                                        bts_core_address=sp.address("tz1e2HPzZWBsuExFSM4XDBtQiFnaUB5hiPnW")))