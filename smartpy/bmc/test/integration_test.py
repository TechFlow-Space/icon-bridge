import smartpy as sp

BMCPeriphery = sp.io.import_script_from_url("file:./contracts/src/bmc_periphery.py")
BMCManagement = sp.io.import_script_from_url("file:./contracts/src/bmc_management.py")
ParseAddress = sp.io.import_script_from_url("file:./contracts/src/parse_address.py")
Helper= sp.io.import_script_from_url("file:./contracts/src/helper.py")



@sp.add_test("flow test")
def test():
    sc = sp.test_scenario()

    # test account
    alice = sp.test_account("Alice")
    creator = sp.test_account("Creator")
    jack = sp.test_account("Jack")
    bob = sp.test_account("Bob")
    helper=sp.test_account('helper')
    parse_contract = sp.test_account("Parser")

    service1_address = sp.test_account("service1_address")
    block_interval = sp.nat(2)
    _max_aggregation = sp.nat(3)
    delay_limit = sp.nat(2)
    link = sp.string('btp://77.tezos/tz1e2HPzZWBsuExFSM4XDBtQiFnaUB5hiPnA')


    def deploy_bmcManagement_contract():
     bmcManagement_contract = BMCManagement.BMCManagement(creator.address,btshelpercontract.address)
     return bmcManagement_contract
    
    def deploy_bmcperiphery_contract():
        bmcperiphery_contract = BMCPeriphery.BMCPreiphery(bmcManagement_contract.address,btshelpercontract.address, btsparsecontract.address, creator.address)
        return bmcperiphery_contract
    
    def deploy_parsecontract():
       btsparsecontract = ParseAddress.ParseAddress()
       return btsparsecontract
    
    def deploy_helper():
       btshelper = Helper.Helper()
       return btshelper
    
    btshelpercontract = deploy_helper()
    sc+= btshelpercontract

    btsparsecontract = deploy_parsecontract()
    sc+= btsparsecontract

    bmcManagement_contract = deploy_bmcManagement_contract()
    sc += bmcManagement_contract
   

    # deploy BMCPeriphery contract
    bmcperiphery_contract = deploy_bmcperiphery_contract()
    sc += bmcperiphery_contract



    bmcManagement_contract.set_bmc_periphery(bmcperiphery_contract.address).run(sender=creator)
    bmcManagement_contract.set_bmc_btp_address("tezos.77").run(sender=creator)
    svc1 = sp.string("service1")
    dst = "btp://77.tezos/tz1e2HPzZWBsuExFSM4XDBtQiFnaUB5hDEST"
    bmcManagement_contract.add_service(sp.record(addr=service1_address.address, svc=svc1)).run(sender=creator)
    bmcManagement_contract.add_route(sp.record(dst = "btp://77.tezos/tz1e2HPzZWBsuExFSM4XDBtQiFnaUB5hDEST", link = "btp://77.tezos/tz1e2HPzZWBsuExFSM4XDBtQiFnaUB5hiPnW")).run(sender=creator)
    #add-link error in local environment due to hard-coded HELPER_CONTRACT_ADDRESS in rlp_encode_contract line 4
    #bmcManagement_contract.add_link("btp://77.tezos/tz1e2HPzZWBsuExFSM4XDBtQiFnaUB5hiPnW").run(sender=creator)
    #bmcManagement_contract.add_relay(sp.record(link=link, addr=sp.set([sp.address("tz1XGbmLYhqcigxFuBCJrgyJejnwkySE4Sk9")]))).run(sender=creator)
    #bmcManagement_contract.set_link(sp.record(_link=link, block_interval=block_interval,_max_aggregation=_max_aggregation, delay_limit=delay_limit)).run(sender=creator)



    #sc.show(bmcperiphery_contract.get_status(link))
