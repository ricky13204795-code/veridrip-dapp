cat > README.md << 'EOF'
# VeriDrip – AI‑Verified Cold Chain Integrity Protocol

## Smart Contracts (ChainLab Testnet)

- **VeriDrip**: `0x22C362d61063ba51bd3a1c269b8B0E65dFC2BB11`
- **VeriDripToken**: `0x55880776237BA00dFb52a019B82749681370FD76`

## Prerequisites

- Node.js v18+
- Python 3.11+
- MetaMask (configured to ChainLab testnet: RPC `https://testnet.chainlab.fun`, chainId `31337`)

## Installation and Compile and Testing steps

```bash
git clone https://github.com/ricky13204795-code/veridrip-dapp.git
cd veridrip-dapp
npm install
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

## Compile
```bash
npx hardhat compile

## Deploy to ChainLab Testnet
-Create .env file
-PRIVATE_KEY=your_private_key
-WEB3_PROVIDER_URL=https://testnet.chainlab.fun
-VERIDRIP_CONTRACT_ADDRESS=0x22C362d61063ba51bd3a1c269b8B0E65dFC2BB11
-AI_MODEL_PATH=./cold_chain_model.pkl

```bash
npx hardhat run deploy.js --network chainlab

## Run AI oracle
```bash
python3 oracle.py --auto

## Run the frontend
```bash
python3 -m http.server 8080

## AutoTest
```bash
rm test/Counter.ts
npx hardhat test

## ManualTest
```bash
npx hardhat console --network chainlab
const veridrip = await ethers.getContractAt("VeriDrip", "0x22C362d61063ba51bd3a1c269b8B0E65dFC2BB11");
const id = ethers.keccak256(ethers.toUtf8Bytes("test"));
await veridrip.registerShipment(id, "QmTest", 0); You may need tochange the shipment ID as I registered this

