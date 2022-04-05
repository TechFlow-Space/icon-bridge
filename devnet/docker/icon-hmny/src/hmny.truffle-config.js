const HDWalletProvider = require("@truffle/hdwallet-provider");

if (process.env.PRIVATE_KEY.length == 0) {
  throw new Error(`PRIVATE_KEY not provided!`);
}

module.exports = {
  db: { enabled: false },
  compilers: {
    solc: {
      version: "0.7.6",
      settings: {
        evmVersion: "petersburg",
        optimizer: { enabled: true, runs: 200 },
      },
    },
  },
  networks: {
    hmny: {
      network_id: parseInt(process.env.NETWORK_ID),
      provider: () => {
        return new HDWalletProvider({
          privateKeys: [process.env.PRIVATE_KEY],
          providerOrUrl: process.env.URI,
          derivationPath: `m/44'/1023'/0'/0/`,
        });
      },
      skipDryRun: true,
    },
  },
};
