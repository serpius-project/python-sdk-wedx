import os
import sys
import time
from dotenv import load_dotenv

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from wedx import WedX

# Load environment variables
load_dotenv()
USER_ADDRESS = os.getenv('USER_ADDRESS')
USER_PRIVATE_KEY = os.getenv('USER_PRIVATE_KEY')

#RPC nodes url. Replace them with yours if preferred
CHAIN_RPCS = {
    1: os.getenv('RPC_ETHEREUM'), # Ethereum mainnet
    8453: os.getenv('RPC_BASE'),  # Base mainnet
    42161: os.getenv('RPC_ARBITRUM'),  # Arbitrum One mainnet
}

# Initialize the SDK
CHAIN_ID = 8453  # 8453 for Base mainnet, 42161 for Arbitrum
wedx = WedX(CHAIN_ID, USER_ADDRESS, USER_PRIVATE_KEY, CHAIN_RPCS)

def create_ew_portfolio():
    assets_info = wedx.get_assets_info()
    assets_ew_portfolio_top_10_non_native = []
    for key in assets_info.keys():
        if assets_info[key]['inputTokens'][0]['symbol'] == 'WETH':
            asset = assets_info[key]['inputTokens'][1]['id']
        else:
            asset = assets_info[key]['inputTokens'][0]['id']
        if assets_info[key]['gtScore'] >= 75.0 and assets_info[key]['totalValueLockedUSD'] >= 500_000 and assets_info[key]['whitelisted'] == True and len(assets_info[key]['websites']) > 0:
            assets_ew_portfolio_top_10_non_native.append(asset)
        if len(assets_ew_portfolio_top_10_non_native) == 10:
            break

    for a in range(len(assets_ew_portfolio_top_10_non_native)):
        assets_ew_portfolio_top_10_non_native[a] = wedx.w3.to_checksum_address(assets_ew_portfolio_top_10_non_native[a])

    distribution = [1.0 for _ in range(len(assets_ew_portfolio_top_10_non_native))]
    distribution.append(0.0)  # adding native allocation

    distribution = wedx.normalize_distribution(distribution)
    return assets_ew_portfolio_top_10_non_native, distribution

#Example of using it:
def main():
    print("User address:", USER_ADDRESS)
    print("Current ETH balance:", wedx.get_eth_balance(USER_ADDRESS))

    deployer_pro_address = wedx.get_wedx_deployer_address()
    print("Deployer address:", deployer_pro_address)

    trading_account_address = wedx.get_trading_account_address()
    print("User account:", trading_account_address)

    if trading_account_address == wedx.zero_address:
        print("User does not have an account yet")
        trading_account_address = wedx.create_trading_account_address()
        print("User account:", trading_account_address)
        if trading_account_address == wedx.zero_address:
            raise('There was an error creating the new account')
        wedx.deposit_eth(0.01)  # Deposit 0.01 ETH

    current_distro = wedx.get_distribution()
    current_assets = wedx.get_assets_addresses()
    new_assets, new_distribution = create_ew_portfolio()

    print(current_distro)
    print(current_assets)

    native_asset = wedx.network[wedx.get_chain_name()]['wrap_address']
    new_assets_with_native = new_assets.copy()
    new_assets_with_native.append(native_asset)

    print(new_distribution)
    print(new_assets_with_native)

    change_threshold_allowance = 1.5 * wedx.get_distribution_threshold()

    update = wedx.are_distributions_different(current_distro, current_assets, new_distribution, new_assets_with_native, change_threshold_allowance)
    print(f'Update needed: {update}')
    trader_data = wedx.get_trader_data()
    required_interactions = wedx.get_required_interactions()
    print(f'Interactions: {len(trader_data[3])} / {required_interactions}')

    if update:
        # try:
        #     wedx.withdraw_from_lending(current_assets)
        # except ValueError as error:
        #     print(error)
        # time.sleep(5)
        try:
            wedx.set_portfolio(new_assets, new_distribution)
        except ValueError as error:
            print(error)
        time.sleep(5)
        # try:
        #     wedx.earn_with_lending(new_assets)
        # except ValueError as error:
        #     print(error)
        # time.sleep(5)
        try:
            trader_data = wedx.get_trader_data()
            required_interactions = wedx.get_required_interactions()
            print(f'Interactions: {len(trader_data[3])} / {required_interactions}')

            if len(trader_data[3]) == required_interactions:
                wedx.rank_me()

        except ValueError as error:
            print(error)

    score = wedx.get_user_score()
    print(f'Current score: {score}')

if __name__ == "__main__":
    main()