const { expect } = require("chai");

describe("VeriDrip Contract", function () {
  let veridrip, token, owner, oracle;
  const shipmentId = ethers.keccak256(ethers.toUtf8Bytes("test_shipment"));

  beforeEach(async function () {
    [owner, oracle] = await ethers.getSigners();
    const Token = await ethers.getContractFactory("VeriDripToken");
    token = await Token.deploy(owner.address, owner.address);
    const VeriDrip = await ethers.getContractFactory("VeriDrip");
    veridrip = await VeriDrip.deploy(await token.getAddress());
    const ORACLE_ROLE = await veridrip.ORACLE_ROLE();
    await veridrip.grantRole(ORACLE_ROLE, oracle.address);
  });

  it("Should register a shipment", async function () {
    // Capture the token address (defaultPaymentToken)
    const tokenAddress = await token.getAddress();
    await expect(veridrip.connect(owner).registerShipment(shipmentId, "QmTest", 0))
      .to.emit(veridrip, "ShipmentRegistered")
      .withArgs(shipmentId, owner.address, 0, tokenAddress); // Expect token address, not zero
  });

  it("Should not register duplicate shipment", async function () {
    await veridrip.connect(owner).registerShipment(shipmentId, "QmTest", 0);
    await expect(veridrip.connect(owner).registerShipment(shipmentId, "QmTest", 0))
      .to.be.revertedWithCustomError(veridrip, "ShipmentExists");
  });

  it("Should submit AI verdict (oracle only)", async function () {
    await veridrip.connect(owner).registerShipment(shipmentId, "QmTest", 0);
    const newStatus = 3;
    const confidence = 95;
    const breachProof = ethers.keccak256(ethers.toUtf8Bytes("proof"));
    const newIpfsHash = "QmNew";
    const encoded = ethers.AbiCoder.defaultAbiCoder().encode(
      ["bytes32", "uint256", "uint8", "bytes32", "string"],
      [shipmentId, newStatus, confidence, breachProof, newIpfsHash]
    );
    const messageHash = ethers.keccak256(encoded);
    const signature = await oracle.signMessage(ethers.getBytes(messageHash));
    await expect(veridrip.connect(oracle).submitAIVerdict(
      shipmentId, newStatus, confidence, breachProof, newIpfsHash, signature
    )).to.emit(veridrip, "VerdictSubmitted");
  });
});
