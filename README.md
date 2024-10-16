# WEDX SDK

The WEDX SDK is a Python library that allows users to interact with the WEDX smart contracts for portfolio management and trading on supported blockchain networks.

## Features

- Create and manage trading accounts
- Set and update portfolio distributions
- Deposit and withdraw ETH
- Interact with lending protocols
- Retrieve user scores and trader data
- Implement custom portfolio strategies
- Create new Ethereum wallets

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/serpius-project/python-sdk-wedx.git
   cd python-sdk-wedx
   ```

2. Install the required dependencies:
   ```
   pip install web3 python-dotenv
   ```
   (Note: A `requirements.txt` file will be added in future updates for easier dependency management)

## Configuration

1. Create a `.env` file in the root directory of the project.
2. Add your Ethereum address and private key to the `.env` file:
   ```
   USER_ADDRESS=your_ethereum_address
   USER_PRIVATE_KEY=your_private_key
   ```

If you don't have an Ethereum wallet, you can use the provided `createUser.py` script in the `examples` folder to create one:

```
python createUser.py
```

This script will generate a new Ethereum address and private key. Make sure to securely store the private key and never share it with anyone.

## Usage

Here's a basic example of how to use the WEDX SDK:

```python
import os
from dotenv import load_dotenv
from wedx import WedX

# Load environment variables
load_dotenv()
USER_ADDRESS = os.getenv('USER_ADDRESS')
USER_PRIVATE_KEY = os.getenv('USER_PRIVATE_KEY')

# RPC nodes url. Replace them with yours if preferred
CHAIN_RPCS = {
    8453: "https://mainnet.base.org",  # Base mainnet
    42161: "https://arbitrum.llamarpc.com",  # Arbitrum One mainnet
}

# Initialize the SDK
CHAIN_ID = 8453  # 8453 for Base mainnet, 42161 for Arbitrum
wedx = WedX(CHAIN_ID, USER_ADDRESS, USER_PRIVATE_KEY, CHAIN_RPCS)

# Get user's trading account address
trading_account_address = wedx.get_trading_account_address()
print("Trading account address:", trading_account_address)

# Get user's current score
score = wedx.get_user_score()
print("Current score:", score)
```

## Implementing Custom Strategies

You can implement custom portfolio strategies using the WEDX SDK. Here are examples of how to create equal-weighted and TVL-weighted portfolios:

### Equal-Weighted Portfolio

```python
def create_ew_portfolio(wedx):
    assets_info = wedx.get_assets_info()
    assets_ew_portfolio_top_10_non_native = list(assets_info.keys())[:10]

    for a in range(len(assets_ew_portfolio_top_10_non_native)):
        assets_ew_portfolio_top_10_non_native[a] = wedx.w3.to_checksum_address(assets_ew_portfolio_top_10_non_native[a])

    distribution = [1.0 for _ in range(len(assets_ew_portfolio_top_10_non_native))]
    distribution.append(0.0)  # adding native allocation

    distribution = wedx.normalize_distribution(distribution)
    return assets_ew_portfolio_top_10_non_native, distribution

# Use the strategy
new_assets, new_distribution = create_ew_portfolio(wedx)
wedx.set_portfolio(new_assets, new_distribution)
```

### TVL-Weighted Portfolio

```python
def create_tvlw_portfolio(wedx):
    assets_info = wedx.get_assets_info()
    assets_ew_portfolio_top_10_non_native = list(assets_info.keys())[:10]

    tvls = []
    for asset in assets_ew_portfolio_top_10_non_native:
        tvls.append(float(assets_info[asset]['totalValueLockedUSD']))

    for a in range(len(assets_ew_portfolio_top_10_non_native)):
        assets_ew_portfolio_top_10_non_native[a] = wedx.w3.to_checksum_address(assets_ew_portfolio_top_10_non_native[a])

    distribution = [tvls[i] for i in range(len(assets_ew_portfolio_top_10_non_native))]
    distribution.append(0.0)  # adding native allocation

    distribution = wedx.normalize_distribution(distribution)
    return assets_ew_portfolio_top_10_non_native, distribution

# Use the strategy
new_assets_tvl, new_distribution_tvl = create_tvlw_portfolio(wedx)
wedx.set_portfolio(new_assets_tvl, new_distribution_tvl)
```

## Examples

You can find an example usage of the WEDX SDK in the `examples` folder. The `traderPro.py` script demonstrates how to create equal-weighted and TVL-weighted portfolios, and how to automate portfolio management using the WEDX SDK.

To run the example:

1. Ensure you've set up your `.env` file in the root directory with your `USER_ADDRESS` and `USER_PRIVATE_KEY`.
2. Navigate to the `examples` folder:
   ```
   cd examples
   ```
3. Run the example script:
   ```
   python traderPro.py
   ```

This script showcases various functionalities of the WEDX SDK, including:
- Creating and managing trading accounts
- Setting up different portfolio strategies (equal-weighted and TVL-weighted)
- Interacting with lending protocols
- Retrieving user scores and trader data
- Automating portfolio updates based on predefined conditions

Feel free to modify this script or create new ones to experiment with different strategies and SDK features.

## Supported Networks

- Base Mainnet (Chain ID: 8453)
- Arbitrum One Mainnet (Chain ID: 42161)

You can get the RPC URL for a specific chain using the following function:

```python
def get_chain_url(chain_id):
    chain_urls = {
        8453: "https://mainnet.base.org",  # Base mainnet
        42161: "https://arbitrum.llamarpc.com",  # Arbitrum One mainnet
    }
    return chain_urls.get(chain_id, None)
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request to the [WEDX SDK repository](https://github.com/serpius-project/python-sdk-wedx).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This SDK is for educational and experimental purposes only. Always do your own research and understand the risks involved in cryptocurrency trading and DeFi protocols before using this SDK or interacting with smart contracts. Be especially careful with private keys and never share them or store them in unsecured locations.