// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title VeriDrip Protocol Token ($DRIP)
 * @author Ricky Chung
 * @notice Implements utility for cold-chain integrity staking and insurance settlement.
 */
contract VeriDripToken is ERC20, ERC20Burnable, ERC20Permit, AccessControl {
    bytes32 public constant ORACLE_ROLE = keccak256("ORACLE_ROLE");
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");

    // Custom Errors for Gas Efficiency (OpenZeppelin v5 style)
    error UnauthorizedAction(address account, bytes32 role);

    constructor(address defaultAdmin, address initialMinter)
        ERC20("VeriDrip", "DRIP")
        ERC20Permit("VeriDrip")
    {
        _grantRole(DEFAULT_ADMIN_ROLE, defaultAdmin);
        _grantRole(MINTER_ROLE, initialMinter);
        
        // Initial Supply: 100 Million DRIP (18 Decimals)
        _mint(defaultAdmin, 100_000_000 * 10**decimals());
    }

    /**
     * @notice Minting is restricted to authorized protocol controllers (e.g., Insurance Escrow)
     */
    function mint(address to, uint256 amount) public {
        if (!hasRole(MINTER_ROLE, msg.sender)) {
            revert UnauthorizedAction(msg.sender, MINTER_ROLE);
        }
        _mint(to, amount);
    }

    /**
     * @notice Incentivizes high-integrity logistics providers.
     * Logic: Can be called by the Oracle after a successful, breach-free delivery.
     */
    function rewardIntegrity(address carrier, uint256 rewardAmount) external {
        if (!hasRole(ORACLE_ROLE, msg.sender)) {
            revert UnauthorizedAction(msg.sender, ORACLE_ROLE);
        }
        _transfer(address(this), carrier, rewardAmount);
    }

    // Required overrides for Solidity inheritance
    function _update(address from, address to, uint256 value)
        internal
        override(ERC20)
    {
        super._update(from, to, value);
    }
}

