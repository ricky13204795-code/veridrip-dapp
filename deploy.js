const hre = require("hardhat");

async function main() {
  // Check network
  const network = await hre.ethers.provider.getNetwork();
  console.log("Connected to network:", network);

  // Check signers
  const signers = await hre.ethers.getSigners();
  console.log("Number of signers:", signers.length);
  
  if (signers.length === 0) {
    console.error("❌ No signers available. Check your private key in .env");
    return;
  }
  
  const deployer = signers[0];
  console.log("Deploying with:", deployer.address);
  const balance = await hre.ethers.provider.getBalance(deployer.address);
  console.log("Balance:", hre.ethers.formatEther(balance), "ETH");
  
  // Deploy VeriDripToken
  const Token = await hre.ethers.getContractFactory("VeriDripToken");
  const token = await Token.deploy(deployer.address, deployer.address);
  await token.waitForDeployment();
  const tokenAddress = await token.getAddress();
  console.log("✅ VeriDripToken deployed to:", tokenAddress);

  // Deploy VeriDrip main contract
  const VeriDrip = await hre.ethers.getContractFactory("VeriDrip");
  const veridrip = await VeriDrip.deploy(tokenAddress);
  await veridrip.waitForDeployment();
  const veridripAddress = await veridrip.getAddress();
  console.log("✅ VeriDrip deployed to:", veridripAddress);

  // Grant MINTER_ROLE on token to VeriDrip contract
  const MINTER_ROLE = await token.MINTER_ROLE();
  await token.grantRole(MINTER_ROLE, veridripAddress);
  console.log("✅ MINTER_ROLE granted to VeriDrip");

  // Grant ORACLE_ROLE to deployer (change this address later if needed)
  const ORACLE_ROLE = await veridrip.ORACLE_ROLE();
  await veridrip.grantRole(ORACLE_ROLE, deployer.address);
  console.log("✅ ORACLE_ROLE granted to deployer");

  console.log("\n🎉 Deployment complete!");
  console.log("Token address:", tokenAddress);
  console.log("VeriDrip address:", veridripAddress);
}

main().catch(console.error);