import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";
import { ethers } from "ethers";

export default buildModule("VeriDripDeployment", (m) => {
  const deployer = m.getAccount(0);
  
  // Define the Python Oracle address as a parameter to avoid hardcoding
  const oracleAddress = m.getParameter("oracleAddress");

  // 1. Pre-calculate the Role Hashes locally (More secure and avoids gas/staticCall overhead)
  // keccak256("ORACLE_ROLE")
  const ORACLE_ROLE = ethers.solidityPackedKeccak256(["string"], ["ORACLE_ROLE"]);
  // keccak256("MINTER_ROLE")
  const MINTER_ROLE = ethers.solidityPackedKeccak256(["string"], ["MINTER_ROLE"]);

  // 2. Deploy VeriDripToken ($DRIP)
  // Constructor expects: address defaultAdmin, address initialMinter
  const token = m.contract("VeriDripToken", [deployer, deployer]);

  // 3. Deploy VeriDrip Main Protocol
  // Constructor expects: address _defaultPaymentToken
  const veridrip = m.contract("VeriDrip", [token]);

  // 4. Post-Deployment Setup: Permissions
  // Grant the Python Oracle permission to submit verdicts on the VeriDrip contract
  m.call(veridrip, "grantRole", [ORACLE_ROLE, oracleAddress]);

  // Grant the main VeriDrip contract permission to mint/reward via the Token contract
  m.call(token, "grantRole", [MINTER_ROLE, veridrip]);

  return { token, veridrip };
});