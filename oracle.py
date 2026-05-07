#!/usr/bin/env python3
"""
VeriDrip Oracle – AI‑powered cold chain integrity verifier

Usage:
  # Manual mode (process one specific shipment)
  python3 oracle.py --shipment <shipment_id_hex>

  # Automatic mode (listen to new shipments and process them instantly)
  python3 oracle.py --auto

Example:
  python3 oracle.py --shipment f86031a8240689412330b8b52f17c3ee84832e450c24229bb5e00edb978934e0
"""

import json
import os
import sys
import time
import argparse
import numpy as np
import joblib
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
from dotenv import load_dotenv

# ------------------------------
# Load environment variables
# ------------------------------
load_dotenv()

PRIVATE_KEY = os.getenv("PRIVATE_KEY")
WEB3_PROVIDER_URL = os.getenv("WEB3_PROVIDER_URL", "https://testnet.chainlab.fun")
VERIDRIP_CONTRACT_ADDRESS = os.getenv("VERIDRIP_CONTRACT_ADDRESS")
ABI_PATH = os.getenv("VERIDRIP_CONTRACT_ABI_PATH", "./artifacts/contracts/VeriDrip.sol/VeriDrip.json")
MODEL_PATH = os.getenv("AI_MODEL_PATH", "./cold_chain_model.pkl")

if not PRIVATE_KEY:
    raise ValueError("PRIVATE_KEY not set in .env file")
if not VERIDRIP_CONTRACT_ADDRESS:
    raise ValueError("VERIDRIP_CONTRACT_ADDRESS not set in .env file")

# ------------------------------
# Web3 connection and contract
# ------------------------------
w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER_URL))
if not w3.is_connected():
    raise ConnectionError(f"Failed to connect to {WEB3_PROVIDER_URL}")

oracle = Account.from_key(PRIVATE_KEY)
print(f"Oracle address: {oracle.address}")

with open(ABI_PATH, "r") as f:
    veridrip_abi = json.load(f)["abi"]

veridrip = w3.eth.contract(
    address=Web3.to_checksum_address(VERIDRIP_CONTRACT_ADDRESS),
    abi=veridrip_abi
)

# ------------------------------
# AI Model loading (real or fallback)
# ------------------------------
model = None
scaler = None
try:
    loaded = joblib.load(MODEL_PATH)
    model = loaded['classifier']
    scaler = loaded['scaler']
    print("✅ Real AI model loaded from", MODEL_PATH)
except Exception as e:
    print(f"⚠️ No AI model found – using fallback simulation. ({e})")
    model = None
    scaler = None

# ------------------------------
# Feature extraction (must match training)
# ------------------------------
def extract_features(iot_data: dict) -> list:
    """Convert raw IoT sensor data into the 6-feature vector expected by the model."""
    temp_readings = iot_data.get('temperature_readings', [20.0])
    temp_variance = np.std(temp_readings) / (np.mean(temp_readings) + 1e-6)
    avg_humidity = iot_data.get('avg_humidity', 60.0)
    max_vibration = iot_data.get('max_vibration', 0.05)
    duration_hours = iot_data.get('duration_hours', 24)
    door_open_count = iot_data.get('door_open_count', 0)
    gps_deviation_km = iot_data.get('gps_deviation_km', 0.0)
    return [temp_variance, avg_humidity, max_vibration, duration_hours, door_open_count, gps_deviation_km]

# ------------------------------
# AI Verdict generation
# ------------------------------
def generate_ai_verdict(shipment_id: bytes, iot_data: dict) -> tuple[int, int, bytes, str]:
    """Returns (new_status, confidence, breach_proof, new_ipfs_hash)."""
    print(f"AI analyzing shipment: {shipment_id.hex()}")

    if model is None:
        new_status = 3
        confidence = 95
        breach_proof = w3.keccak(text="simulated_breach_evidence")
        new_ipfs_hash = "QmSimulatedBreachDataHash"
        print("Using fallback simulation")
        return new_status, confidence, breach_proof, new_ipfs_hash

    features = extract_features(iot_data)
    features_scaled = scaler.transform([features])
    predicted_class = int(model.predict(features_scaled)[0])
    confidence_proba = model.predict_proba(features_scaled)[0]
    confidence = int(confidence_proba.max() * 100)

    status_map = {0: 1, 1: 2, 2: 3}
    new_status = status_map.get(predicted_class, 1)

    breach_proof = w3.keccak(text=str(features))
    new_ipfs_hash = "QmRealDataHash"   # Replace with actual IPFS upload

    print(f"Real AI verdict: status={new_status}, confidence={confidence}, proof={breach_proof.hex()}, ipfs={new_ipfs_hash}")
    return new_status, confidence, breach_proof, new_ipfs_hash

# ------------------------------
# Signing (exactly as Solidity expects)
# ------------------------------
def sign_verdict(shipment_id: bytes, new_status: int, confidence: int,
                 breach_proof: bytes, new_ipfs_hash: str) -> bytes:
    encoded = w3.codec.encode(
        ["bytes32", "uint256", "uint8", "bytes32", "string"],
        [shipment_id, new_status, confidence, breach_proof, new_ipfs_hash]
    )
    message_hash = w3.keccak(encoded)
    print("Message hash (Python):", message_hash.hex())
    signable = encode_defunct(primitive=message_hash)
    signed = w3.eth.account.sign_message(signable, private_key=PRIVATE_KEY)
    return signed.signature

# ------------------------------
# On‑chain submission
# ------------------------------
def submit_verdict(shipment_id: bytes, new_status: int, confidence: int,
                   breach_proof: bytes, new_ipfs_hash: str, signature: bytes):
    print(f"Submitting verdict for {shipment_id.hex()}...")
    try:
        tx = veridrip.functions.submitAIVerdict(
            shipment_id, new_status, confidence, breach_proof, new_ipfs_hash, signature
        ).build_transaction({
            'from': oracle.address,
            'nonce': w3.eth.get_transaction_count(oracle.address),
            'gas': 500000,
            'gasPrice': w3.eth.gas_price
        })
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"Transaction hash: {tx_hash.hex()}")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Confirmed in block {receipt.blockNumber}, status: {receipt.status}")
        if receipt.status == 1:
            print("✅ Verdict submitted successfully!")
        else:
            print("❌ Transaction failed.")
    except Exception as e:
        print(f"Error submitting verdict: {e}")

# ------------------------------
# Fetch IoT data (placeholder – replace with real data source)
# ------------------------------
def fetch_iot_data(shipment_id: bytes, ipfs_data_hash: str = None) -> dict:
    """
    In production: retrieve sensor data from IPFS using the ipfs_data_hash
    or from your own database. For demo, return a static sample.
    """
    # Placeholder – replace with actual logic
    return {
        'temperature_readings': [22.5, 23.1, 28.7, 29.2, 26.8],
        'avg_humidity': 70.0,
        'max_vibration': 0.12,
        'duration_hours': 48,
        'door_open_count': 3,
        'gps_deviation_km': 12.5
    }

# ------------------------------
# Process one shipment (core logic) – WITH STATUS CHECK
# ------------------------------
def process_shipment(shipment_id: bytes, iot_data: dict = None):
    # Check current status to avoid re‑submitting for already‑breached shipments
    try:
        shipment_data = veridrip.functions.shipments(shipment_id).call()
        # The status is the third field (index 2)
        current_status = shipment_data[2]
        if current_status == 3:
            print(f"⏭️ Shipment {shipment_id.hex()} already breached. Skipping.")
            return
    except Exception as e:
        print(f"⚠️ Could not fetch shipment status: {e}. Proceeding anyway...")

    if iot_data is None:
        iot_data = fetch_iot_data(shipment_id)
    new_status, confidence, proof, ipfs_hash = generate_ai_verdict(shipment_id, iot_data)
    sig = sign_verdict(shipment_id, new_status, confidence, proof, ipfs_hash)
    submit_verdict(shipment_id, new_status, confidence, proof, ipfs_hash, sig)

# ------------------------------
# Manual mode
# ------------------------------
def manual_mode(shipment_id_hex: str):
    raw_hex = shipment_id_hex.replace("0x", "")
    try:
        shipment_id = bytes.fromhex(raw_hex)
    except ValueError:
        print("Invalid hex string for shipment ID")
        sys.exit(1)
    process_shipment(shipment_id)

# ------------------------------
# Automatic (event‑driven) mode – polls and processes new events
# ------------------------------
def auto_mode():
    print("🔄 Listening for new ShipmentRegistered events (polling every 5 seconds)...")
    event_abi = veridrip.events.ShipmentRegistered._get_event_abi()
    event_signature = f"{event_abi['name']}({','.join([i['type'] for i in event_abi['inputs']])})"
    event_topic = Web3.keccak(text=event_signature).hex()
    print(f"Event signature: {event_signature}")
    print(f"Event topic: {event_topic}")

    # Look back up to 10 blocks to catch recent events (adjust as needed)
    last_block = max(0, w3.eth.block_number - 10)
    print(f"Starting from block {last_block}")

    while True:
        try:
            current_block = w3.eth.block_number
            if current_block > last_block:
                filter_params = {
                    'fromBlock': last_block + 1,
                    'toBlock': current_block,
                    'address': veridrip.address,
                    'topics': [event_topic]
                }
                raw_logs = w3.eth.get_logs(filter_params)
                print(f"Polled blocks {last_block+1}-{current_block}, found {len(raw_logs)} logs")
                for log in raw_logs:
                    decoded = veridrip.events.ShipmentRegistered().process_log(log)
                    shipment_id = decoded['args']['shipmentId']
                    print(f"\n🚚 New shipment detected: {shipment_id.hex()}")
                    process_shipment(shipment_id, None)  # None triggers default placeholder IoT data
                last_block = current_block
        except Exception as e:
            print(f"Error polling events: {e}")
            import traceback
            traceback.print_exc()
        time.sleep(5)

# ------------------------------
# Main entry point
# ------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VeriDrip Oracle")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--shipment", type=str, help="Manual mode: process one shipment (hex ID)")
    group.add_argument("--auto", action="store_true", help="Automatic mode: listen for new shipments")

    args = parser.parse_args()

    if args.shipment:
        manual_mode(args.shipment)
    elif args.auto:
        auto_mode()