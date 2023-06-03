import smartpy as sp

BMCManagement = sp.io.import_script_from_url("file:./contracts/src/bmc_management.py")
BMCPeriphery = sp.io.import_script_from_url("file:./contracts/src/bmc_periphery.py")
BMCHelper = sp.io.import_script_from_url("file:./contracts/src/helper.py")
ParseAddress = sp.io.import_script_from_url("file:../bts/contracts/src/parse_address.py")



@sp.add_test("BMCManagementTest")
def test():
    sc = sp.test_scenario()

    # test account
    alice = sp.test_account("Alice")
    jack = sp.test_account("Jack")
    bob = sp.test_account("Bob")
    creator2 = sp.test_account("creator2")
    service1_address = sp.test_account("service1_address")
    service2_address = sp.test_account("service2_address")


    # deploy BMCManagement contract

    helper_contract = deploy_helper_contract()
    sc += helper_contract

    bmcManagement_contract = deploy_bmcManagement_contract(sp.address("tz1XGbmLYhqcigxFuBCJrgyJejnwkySE4Sk9"), helper_contract.address)
    sc += bmcManagement_contract

    parse_address = deploy_parse_address()
    sc += parse_address

    bmcPeriphery_contract = deploy_bmcPeriphery_contract(bmcManagement_contract.address, helper_contract.address, parse_address.address)
    sc += bmcPeriphery_contract


    # set_bmc_btp_address
    bmcPeriphery_contract.set_bmc_btp_address("tezos.77").run(sender=alice, valid=False, exception="Unauthorized")
    bmcPeriphery_contract.set_bmc_btp_address("tezos.77").run(sender=bmcManagement_contract.address)
    sc.verify(bmcPeriphery_contract.data.bmc_btp_address == sp.some(sp.string("btp://tezos.77/KT1Tezooo3zzSmartPyzzSTATiCzzzseJjWC")))

    # get_bmc_btp_address
    sc.verify_equal(bmcPeriphery_contract.get_bmc_btp_address(), sp.string("btp://tezos.77/KT1Tezooo3zzSmartPyzzSTATiCzzzseJjWC"))

    
    # set_helper_address
    bmcPeriphery_contract.set_helper_address(sp.address("KT1EXYXNGdbh4uvdKc8hh7ETQXCXPzhelper")).run(sender=jack, valid=False, exception="Unauthorized")  
    bmcPeriphery_contract.set_helper_address(sp.address("KT1EXYXNGdbh4uvdKc8hh7ETQXCXPzhelper")).run(sender=sp.address("tz1XGbmLYhqcigxFuBCJrgyJejnwkySE4Sk9"))
    sc.verify(bmcPeriphery_contract.data.helper == sp.address("KT1EXYXNGdbh4uvdKc8hh7ETQXCXPzhelper"))

    # set_parse_address
    bmcPeriphery_contract.set_parse_address(sp.address("KT1EXYXNGdbh4uvdKc8hh7ETQXCXPzhparse")).run(sender=jack, valid=False, exception="Unauthorized")  
    bmcPeriphery_contract.set_parse_address(sp.address("KT1EXYXNGdbh4uvdKc8hh7ETQXCXPzhparse")).run(sender=sp.address("tz1XGbmLYhqcigxFuBCJrgyJejnwkySE4Sk9"))
    sc.verify(bmcPeriphery_contract.data.parse_contract == sp.address("KT1EXYXNGdbh4uvdKc8hh7ETQXCXPzhparse"))

    # set_bmc_management_addr
    bmcPeriphery_contract.set_bmc_management_addr(sp.address("KT1EXYXNGdbh4uvdKc8hh7ETQXmanagement")).run(sender=jack, valid=False, exception="Unauthorized")  
    bmcPeriphery_contract.set_bmc_management_addr(sp.address("KT1EXYXNGdbh4uvdKc8hh7ETQXmanagement")).run(sender=sp.address("tz1XGbmLYhqcigxFuBCJrgyJejnwkySE4Sk9"))
    sc.verify(bmcPeriphery_contract.data.bmc_management == sp.address("KT1EXYXNGdbh4uvdKc8hh7ETQXmanagement"))

    # #get_status
    # sc.verify_equal(bmcPeriphery_contract.get_status("btp://0x7.icon/cxff8a87fde8971a1d10d93dfed3416b0a6258d67b"), sp.record(rx_seq=0,tx_seq=0,rx_height=0,current_height=0))





def deploy_bmcManagement_contract(owner, helper):
    bmcManagement_contract = BMCManagement.BMCManagement(owner, helper)
    return bmcManagement_contract

def deploy_bmcPeriphery_contract(bmc_addres, helper, parse):
    owner = sp.address("tz1XGbmLYhqcigxFuBCJrgyJejnwkySE4Sk9")
    bmcPeriphery_contract = BMCPeriphery.BMCPreiphery(bmc_addres, helper, parse, owner)
    return bmcPeriphery_contract

def deploy_helper_contract():
    helper_contract = BMCHelper.Helper()
    return helper_contract


def deploy_parse_address():
    parse_address = ParseAddress.ParseAddress()
    return parse_address
