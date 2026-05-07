import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";

const VeriDripModule = buildModule("VeriDripModule", (m) => {
  // Parameters for VeriDripToken constructor
  const defaultAdmin = m.getAccount(0); // Uses the first account as admin
  const initialMinter = m.getAccount(0); // Uses the first account as initial minter

  // Deploy VeriDripToken
  const veriDripToken = m.contract("VeriDripToken", [defaultAdmin, initialMinter]);

  // Deploy VeriDrip core contract, passing the token address
  const veriDrip = m.contract("VeriDrip", [veriDripToken]);

  return { veriDrip, veriDripToken };
});

export default VeriDripModule;
