import smartpy as sp

#TODO: change to mainnet address
HELPER_CONTRACT_ADDRESS = sp.address("KT1DHptHqSovffZ7qqvSM9dy6uZZ8juV88gP")

class EncodeLibrary:
    LIST_SHORT_START = sp.bytes("0xc0")

    def encode_bmc_service(self, params):
        sp.set_type(params, sp.TRecord(serviceType=sp.TString, payload=sp.TBytes))

        encode_service_type = sp.view("encode_string", self.data.helper, params.serviceType, t=sp.TBytes).open_some()

        payload_rlp = sp.view("encode_list", self.data.helper, [params.payload], t=sp.TBytes).open_some()
        payload_rlp = sp.view("with_length_prefix", self.data.helper, payload_rlp, t=sp.TBytes).open_some()

        rlp_bytes_with_prefix = sp.view("encode_list", self.data.helper, [encode_service_type, payload_rlp],
                                        t=sp.TBytes).open_some()
        rlp_bytes_with_prefix = sp.view("with_length_prefix", self.data.helper, rlp_bytes_with_prefix,
                                        t=sp.TBytes).open_some()
        return rlp_bytes_with_prefix

    def encode_bmc_message(self, params):
        sp.set_type(params, sp.TRecord(src=sp.TString, dst=sp.TString, svc=sp.TString, sn=sp.TInt, message=sp.TBytes))

        encode_src = sp.view("encode_string", self.data.helper, params.src, t=sp.TBytes).open_some()
        encode_dst = sp.view("encode_string", self.data.helper, params.dst, t=sp.TBytes).open_some()
        encode_svc = sp.view("encode_string", self.data.helper, params.svc, t=sp.TBytes).open_some()
        encode_sn = sp.view("to_bytes", HELPER_CONTRACT_ADDRESS, params.sn, t=sp.TBytes).open_some()

        rlp_bytes_with_prefix = sp.view("encode_list", self.data.helper, [encode_src, encode_dst, encode_svc, encode_sn, params.message], t=sp.TBytes).open_some()
        return rlp_bytes_with_prefix

    def encode_response(self, params):
        sp.set_type(params, sp.TRecord(code=sp.TNat, message=sp.TString))

        encode_code = sp.view("encode_nat", self.data.helper, params.code, t=sp.TBytes).open_some()
        encode_message = sp.view("encode_string", self.data.helper, params.message, t=sp.TBytes).open_some()

        rlp_bytes_with_prefix = sp.view("encode_list", self.data.helper, [encode_code, encode_message], t=sp.TBytes).open_some()
        return rlp_bytes_with_prefix
