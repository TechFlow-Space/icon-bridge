import smartpy as sp

BMCPeriphery = sp.io.import_script_from_url("file:./contracts/src/bmc_periphery.py")

@sp.add_test("BMCPeripheryTest")
def test():
    sc = sp.test_scenario()

    # test account
    alice = sp.test_account("Alice")
    creator = sp.test_account("Creator")
    jack = sp.test_account("Jack")
    bob = sp.test_account("Bob")

    # deploy BMCPeriphery contract
    bmcperiphery_contract = deploy_bmcperiphery_contract()
    sc += bmcperiphery_contract


    # test 1 : handle_relay_message function
    bmcperiphery_contract.handle_relay_message(sp.record(prev="demo", msg=sp.bytes("0x0dae11"))).run(sender=creator)

    #test 2: send_message function
    bmcperiphery_contract.send_message(sp.record(to=sp.string('77.tezos'), svc=('service1'), sn=(sp.nat(1)), msg=sp.bytes("0x0dae11"))).run(sender=creator)
def deploy_bmcperiphery_contract():
    bmc_management = sp.test_account("BMC Management")
    bmcperiphery_contract = BMCPeriphery.BMCPreiphery("tezos", bmc_management.address)
    return bmcperiphery_contract