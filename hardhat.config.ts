import { HardhatUserConfig } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";
import * as dotenv from "dotenv";

dotenv.config();

const PRIVATE_KEY = process.env.PRIVATE_KEY;

// Add this check
if (!PRIVATE_KEY) {
  console.warn("⚠️  Warning: PRIVATE_KEY not set in .env file");
}

const networks: any = {
  chainlab: {
    url: "https://testnet.chainlab.fun",
    accounts: PRIVATE_KEY ? [PRIVATE_KEY] : [],
  },
};

// ... rest unchanged

const config: HardhatUserConfig = {
  solidity: {
    version: "0.8.28",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
      evmVersion: "cancun",  // ✅ Add this line
    },
  },
  networks: networks,
  paths: {
    sources: "./contracts",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts"
  },
};

export default config;