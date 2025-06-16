# Sponsorship Smart Contract Architecture

## 1. Overview

The `Sponsorship` smart contract is the economic core of the "Canary Network." It is the mechanism through which a **Sponsor** (e.g., a data publisher) funds the Quality of Service for a specific data stream, and **Node Operators** stake DATA tokens to provide that service in exchange for rewards. This contract directly connects the demand for high-performance data delivery with the supply of network resources.

## 2. Core Concepts

- **Lifecycle**: A Sponsorship is created for a specific `streamId`. It is funded with DATA tokens that are released over a defined period. Operators can join by staking their own DATA, and they earn a proportional share of the funding stream.
- **Rewards**: Rewards are distributed based on participation and are amplified by the "Probabilistic Proof-of-Delivery" lottery mechanism.
- **Slashing**: An Operator's stake is at risk. If they fail to provide the service (as verified by the dispute resolution process), a portion of their stake is slashed.

## 3. State Variables

The contract must store the following information:

```solidity
// --- Sponsorship Configuration ---
address public sponsor; // The address that created and primarily funds the sponsorship
string public streamId; // The identifier of the stream being sponsored
uint256 public totalStaked; // The total amount of DATA staked by all operators in this sponsorship
uint256 public remainingFunding; // The amount of DATA left to be distributed
uint256 public fundingRate; // The rate at which funds are released per second
uint256 public minOperatorStake; // The minimum stake required for an operator to join
bool public isActive; // Flag to indicate if the sponsorship is active or has been cancelled

// --- Operator Management ---
mapping(address => uint256) public operatorStakes; // Maps an operator's address to their stake amount
address[] public operators; // An array of all participating operator addresses

// --- Governance & Control ---
address public governance; // The address (initially multi-sig, later DAO) that can adjust parameters
address public disputeResolver; // The address of the contract that handles slashing logic
```

## 4. Core Functions

### For Sponsors

- `createSponsorship(string memory streamId, uint256 fundingAmount, uint256 duration, uint256 minStake)`
  - Creates a new Sponsorship, setting the initial parameters. `fundingRate` is calculated from `fundingAmount` and `duration`.
  - Requires a DATA token `approve` and `transferFrom` call.
- `addFunding(uint256 fundingAmount, uint256 newDuration)`
  - Allows the sponsor (or anyone) to add more funding and extend the lifetime of the Sponsorship.
- `cancelSponsorship()`
  - Allows the sponsor to gracefully end the Sponsorship after the current funding period. Remaining funds can be reclaimed.

### For Node Operators

- `joinSponsorship(uint256 stakeAmount)`
  - Allows a Node Operator to join. They must stake at least `minOperatorStake`.
  - Requires a DATA token `approve` and `transferFrom` call.
  - Adds the operator to the `operators` array and updates `totalStaked`.
- `leaveSponsorship()`
  - Allows an operator to withdraw their stake and any unclaimed rewards after a mandatory "cooldown" period. This prevents operators from abandoning the stream instantly.

### For Reward & Slashing Mechanisms

- `claimReward(bytes memory proofOfDelivery)`
  - Called by an Operator to claim their share of the rewards.
  - The `proofOfDelivery` could be the winning "lottery ticket" from the probabilistic mechanism, entitling them to a bonus reward.
- `slash(address operator, uint256 penaltyAmount)`
  - **Only callable by the `disputeResolver` contract.**
  - Reduces the `operator`'s stake by `penaltyAmount`. A portion of the penalty could be burned, and another portion awarded to the challenger who raised the dispute.

### Governance Functions

- `setDisputeResolver(address newResolver)`
  - **Only callable by `governance`.**
- `setGovernance(address newGovernance)`
  - **Only callable by `governance`.**

## 5. Events

The contract should emit events for all significant state changes to ensure transparency.

- `SponsorshipCreated(string streamId, address sponsor, uint256 initialFunding)`
- `FundingAdded(address funder, uint256 amount)`
- `OperatorJoined(address operator, uint256 stakeAmount)`
- `OperatorLeft(address operator, uint256 stakeReturned)`
- `RewardClaimed(address operator, uint256 rewardAmount)`
- `OperatorSlashed(address operator, uint256 penaltyAmount)`

## 6. Next Steps

This high-level architecture provides a solid foundation. The next step is to detail the logic within each function, particularly the reward calculation formula and the precise interaction with the `disputeResolver` contract. 