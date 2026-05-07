// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";

/**
 * @title VeriDrip - AI-Verified Cold Chain Integrity Protocol
 * @notice Final gas-optimized, secure, and production-ready version with Custom Errors.
 */
contract VeriDrip is AccessControl, ReentrancyGuard, Pausable {
    using ECDSA for bytes32;

    bytes32 public constant ORACLE_ROLE = keccak256("ORACLE_ROLE");
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");

    uint8 public constant MIN_CONFIDENCE = 75;

    IERC20 public defaultPaymentToken;

    // ====================== Custom Errors ======================
    error ShipmentExists();
    error ShipmentNotFound();
    error InsufficientConfidence(uint8 provided, uint8 minimum);
    error InvalidStatus();
    error InvalidOracleSignature(address signer);
    error NotShipper();
    error NoInsuranceToClaim();
    error InvalidRecipient();
    error InsufficientBalance();
    error ETHTransferFailed();

    struct Shipment {
        // Slot 1 (packed)
        address shipper;
        uint64 departureTime;
        uint8 status;
        // 3 bytes free

        // Slot 2
        uint256 insuranceAmount;

        // Slot 3 (packed)
        address tokenUsed;
        uint64 lastUpdated;
        // 4 bytes free

        // Slot 4
        bytes32 breachProof;

        // Dynamic
        string ipfsDataHash;
    }

    mapping(bytes32 => Shipment) public shipments;

    // Events
    event ShipmentRegistered(bytes32 indexed shipmentId, address indexed shipper, uint256 insuranceAmount, address tokenUsed);
    event VerdictSubmitted(bytes32 indexed shipmentId, uint256 newStatus, uint8 confidence, bytes32 breachProof, string ipfsHash);
    event InsuranceClaimed(bytes32 indexed shipmentId, address indexed claimant, uint256 amount, address token);
    event Withdrawn(address indexed token, address indexed to, uint256 amount);
    event DefaultPaymentTokenUpdated(address newToken);

    constructor(address _defaultPaymentToken) {
        defaultPaymentToken = IERC20(_defaultPaymentToken);
        
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(ADMIN_ROLE, msg.sender);
        _grantRole(ORACLE_ROLE, msg.sender);
    }

    // ====================== Core Functions ======================

    function registerShipment(
        bytes32 shipmentId,
        string calldata ipfsDataHash,
        uint256 insuranceAmount
    ) external whenNotPaused {
        if (shipments[shipmentId].departureTime != 0) revert ShipmentExists();

        address tokenToUse = address(defaultPaymentToken);

        if (insuranceAmount > 0 && tokenToUse != address(0)) {
            IERC20(tokenToUse).transferFrom(msg.sender, address(this), insuranceAmount);
        }

        shipments[shipmentId] = Shipment({
            shipper: msg.sender,
            departureTime: uint64(block.timestamp),
            status: 1,
            insuranceAmount: insuranceAmount,
            tokenUsed: tokenToUse,
            lastUpdated: uint64(block.timestamp),
            breachProof: bytes32(0),
            ipfsDataHash: ipfsDataHash
        });

        emit ShipmentRegistered(shipmentId, msg.sender, insuranceAmount, tokenToUse);
    }

    function submitAIVerdict(
        bytes32 shipmentId,
        uint256 newStatus,
        uint8 confidence,
        bytes32 breachProof,
        string calldata newIpfsHash,
        bytes calldata signature
    ) external onlyRole(ORACLE_ROLE) whenNotPaused {
        Shipment storage shipment = shipments[shipmentId];
        if (shipment.departureTime == 0) revert ShipmentNotFound();
        if (confidence < MIN_CONFIDENCE) revert InsufficientConfidence(confidence, MIN_CONFIDENCE);
        if (newStatus == shipment.status || newStatus > 3) revert InvalidStatus();

        // Safe hashing
        bytes32 messageHash = keccak256(
            abi.encode(shipmentId, newStatus, confidence, breachProof, newIpfsHash)
        );
        bytes32 ethSignedMessageHash = MessageHashUtils.toEthSignedMessageHash(messageHash);
        address signer = ethSignedMessageHash.recover(signature);

        if (!hasRole(ORACLE_ROLE, signer)) revert InvalidOracleSignature(signer);

        shipment.status = uint8(newStatus);
        shipment.ipfsDataHash = newIpfsHash;
        shipment.breachProof = breachProof;
        shipment.lastUpdated = uint64(block.timestamp);

        emit VerdictSubmitted(shipmentId, newStatus, confidence, breachProof, newIpfsHash);
    }

    function claimInsurance(bytes32 shipmentId) external nonReentrant {
        Shipment storage shipment = shipments[shipmentId];
        if (shipment.status != 3) revert NoInsuranceToClaim();
        if (shipment.shipper != msg.sender) revert NotShipper();
        if (shipment.insuranceAmount == 0) revert NoInsuranceToClaim();

        uint256 amount = shipment.insuranceAmount;
        address tokenAddress = shipment.tokenUsed;
        shipment.insuranceAmount = 0;

        if (tokenAddress != address(0)) {
            IERC20(tokenAddress).transfer(msg.sender, amount);
        } else {
            (bool success, ) = payable(msg.sender).call{value: amount}("");
            if (!success) revert ETHTransferFailed();
        }

        emit InsuranceClaimed(shipmentId, msg.sender, amount, tokenAddress);
    }

    // ====================== Withdrawal Pattern ======================
    function withdrawToken(
        address tokenAddress,
        address payable to,
        uint256 amount
    ) external onlyRole(ADMIN_ROLE) nonReentrant {
        if (to == address(0)) revert InvalidRecipient();

        if (tokenAddress == address(0)) {
            if (address(this).balance < amount) revert InsufficientBalance();
            (bool success, ) = to.call{value: amount}("");
            if (!success) revert ETHTransferFailed();
        } else {
            IERC20 token = IERC20(tokenAddress);
            if (token.balanceOf(address(this)) < amount) revert InsufficientBalance();
            token.transfer(to, amount);
        }

        emit Withdrawn(tokenAddress, to, amount);
    }

    function withdrawAll(address tokenAddress, address payable to) external onlyRole(ADMIN_ROLE) nonReentrant {
        if (to == address(0)) revert InvalidRecipient();

        if (tokenAddress == address(0)) {
            uint256 amount = address(this).balance;
            (bool success, ) = to.call{value: amount}("");
            if (!success) revert ETHTransferFailed();
            emit Withdrawn(address(0), to, amount);
        } else {
            IERC20 token = IERC20(tokenAddress);
            uint256 amount = token.balanceOf(address(this));
            token.transfer(to, amount);
            emit Withdrawn(tokenAddress, to, amount);
        }
    }

    // ====================== Pausable ======================
    function pause() external onlyRole(ADMIN_ROLE) {
        _pause();
    }

    function unpause() external onlyRole(ADMIN_ROLE) {
        _unpause();
    }

    // ====================== Admin Management ======================
    function addOracle(address oracle) external onlyRole(ADMIN_ROLE) {
        grantRole(ORACLE_ROLE, oracle);
    }

    function removeOracle(address oracle) external onlyRole(ADMIN_ROLE) {
        revokeRole(ORACLE_ROLE, oracle);
    }

    function setDefaultPaymentToken(address _newDefaultToken) external onlyRole(ADMIN_ROLE) {
        defaultPaymentToken = IERC20(_newDefaultToken);
        emit DefaultPaymentTokenUpdated(_newDefaultToken);
    }

    receive() external payable {}
}