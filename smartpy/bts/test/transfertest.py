import smartpy as sp
BTSPeriphery = sp.io.import_script_from_url("file:./contracts/src/bts_periphery.py")
BTSCore = sp.io.import_script_from_url("file:./contracts/src/bts_core.py")
BTSOwnerManager = sp.io.import_script_from_url("file:./contracts/src/bts_owner_manager.py")
ParseAddress = sp.io.import_script_from_url("file:./contracts/src/parse_address.py")
Helper= sp.io.import_script_from_url("file:./contracts/src/helper.py")



@sp.add_test("FlowTest")
def test():
    sc = sp.test_scenario()

    # test account
    alice=sp.test_account("Alice")
    bmc_address = sp.test_account('bmc')
    admin=sp.test_account('admin')
    helper = sp.test_account("Helper")
    

    def deploy_btsperiphery_contract():
     btsperiphery_contract = BTSPeriphery.BTPPreiphery(bmc_address.address,btscore_contract.address,btshelpercontract.address,btsparsecontract.address,admin.address)
     return btsperiphery_contract
    
    def deploy_parsecontract():
       btsparsecontract = ParseAddress.ParseAddress()
       return btsparsecontract
    
    def deploy_helper():
       btshelper = Helper.Helper()
       return btshelper
    
    def deploy_fa2_Contract(admin_address):
        fa2_contract = BTSCore.FA2_contract.SingleAssetToken(admin=admin_address, metadata=sp.big_map({"ss": sp.bytes("0x0dae11")}), token_metadata=sp.map({"ff": sp.bytes("0x0dae11")}))
        return fa2_contract
    
       
    
    def deploy_btscore_contract():
        btscore_contract= BTSCore.BTSCore(
         owner_manager= bts_OwnerManager_contract.address,
         _native_coin_name="BTSCOIN",
         _fee_numerator=sp.nat(1000),
         _fixed_fee=sp.nat(10))
        return btscore_contract
    
    def deploy_btsOwnerManager_Contract():
     bts_OwnerManager_Contract = BTSOwnerManager.BTSOwnerManager(sp.address("tz1XGbmLYhqcigxFuBCJrgyJejnwkySE4Sk9"))
     return bts_OwnerManager_Contract
    
    bts_OwnerManager_contract = deploy_btsOwnerManager_Contract()
    sc+= bts_OwnerManager_contract

    btscore_contract = deploy_btscore_contract()
    sc+= btscore_contract

    btshelpercontract = deploy_helper()
    sc+= btshelpercontract

    btsparsecontract = deploy_parsecontract()
    sc+= btsparsecontract
    
    # deploy btsperiphery contract
    btsperiphery_contract = deploy_btsperiphery_contract()
    sc += btsperiphery_contract

    fa2 = deploy_fa2_Contract(btsperiphery_contract.address)
    sc += fa2
    
    btscore_contract.update_bts_periphery(btsperiphery_contract.address).run(sender=sp.address("tz1XGbmLYhqcigxFuBCJrgyJejnwkySE4Sk9"))

    # #test case : transfer_native_coin function
    btsperiphery_contract.set_token_limit(
        sp.record(
            coin_names=sp.map({0: "BTSCOIN"}),
            token_limit=sp.map({0: 115792089237316195423570985008687907853269984665640564039457584007913129639935})
        )
    ).run(sender = btscore_contract.address)
    btscore_contract.transfer_native_coin("tz1eZMrKqCNPrHzykdTuqKRyySoDv4QRSo7d").run(sender= sp.address("tz1XGbmLYhqcigxFuBCJrgyJejnwkySE4Sk9"), amount=sp.tez(30))
    sc.show(btscore_contract.balance_of(
            sp.record(owner=sp.address("tz1eZMrKqCNPrHzykdTuqKRyySoDv4QRSo7d"), coin_name='BTSCOIN')
        ))
    
    # sc.verify_equal(
    #     btscore_contract.balance_of(
    #         sp.record(owner=sp.address("tz1eZMrKqCNPrHzykdTuqKRyySoDv4QRSo7d"), coin_name='BTSCOIN')
    #     ),
    #     sp.record(usable_balance=0, locked_balance=0, refundable_balance=0, user_balance=0)
    # )


    # test case : nonnative coin
    btscore_contract.register(
        name=sp.string("new_coin"),
        fee_numerator=sp.nat(10),
        fixed_fee=sp.nat(2),
        addr=fa2.address,
        token_metadata=sp.map({"ff": sp.bytes("0x0dae11")}),
        metadata=sp.big_map({"ff": sp.bytes("0x0dae11")})
    ).run(sender=sp.address("tz1XGbmLYhqcigxFuBCJrgyJejnwkySE4Sk9"))

    fa2.mint([sp.record(to_=sp.address("tz1XGbmLYhqcigxFuBCJrgyJejnwkySE4Sk9"), amount=sp.nat(100))]).run(sender=btsperiphery_contract.address)
    fa2.set_allowance([sp.record(spender=btscore_contract.address, amount=sp.nat(100))]).run(sender=sp.address("tz1XGbmLYhqcigxFuBCJrgyJejnwkySE4Sk9"))

    fa2.update_operators(
         [sp.variant("add_operator", sp.record(owner=sp.address("tz1XGbmLYhqcigxFuBCJrgyJejnwkySE4Sk9"), operator=btscore_contract.address, token_id=0))]).run(
         sender=sp.address("tz1XGbmLYhqcigxFuBCJrgyJejnwkySE4Sk9"))
    sc.verify_equal(btscore_contract.is_valid_coin('new_coin'), True)
    btscore_contract.transfer(coin_name='new_coin', value=10,  to="tz1eZMrKqCNPrHzykdTuqKRyySoDv4QRSo7d").run(sender = sp.address("tz1XGbmLYhqcigxFuBCJrgyJejnwkySE4Sk9"))    
    sc.verify_equal(
        btscore_contract.balance_of(
            sp.record(owner=sp.address("tz1XGbmLYhqcigxFuBCJrgyJejnwkySE4Sk9"), coin_name='new_coin')
        ),
        sp.record(usable_balance=90, locked_balance=10, refundable_balance=0, user_balance=90)
    )


    
    

    