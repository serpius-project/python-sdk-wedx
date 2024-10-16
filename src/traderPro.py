import os
import time
from dotenv import load_dotenv
from wedx import WedX

# Load environment variables
load_dotenv()
USER_ADDRESS = os.getenv('USER_ADDRESS')
USER_PRIVATE_KEY = os.getenv('USER_PRIVATE_KEY')

# Initialize the SDK
CHAIN_ID = 8453  # Base mainnet, 42161 for Arbitrum
wedx = WedX(CHAIN_ID, USER_ADDRESS, USER_PRIVATE_KEY)

def create_ew_portfolio():
    assets_info = wedx.get_assets_info()
    assets_ew_portfolio_top_10_non_native = list(assets_info.keys())[:10]

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

    while True:
        current_distro = wedx.get_distribution()
        current_assets = wedx.get_assets_addresses()
        new_assets, new_distribution = create_ew_portfolio()

        native_asset = wedx.network[wedx.get_chain_name()]['wrap_address']
        new_assets_with_native = new_assets.copy()
        new_assets_with_native.append(native_asset)

        change_threshold_allowance = wedx.get_distribution_threshold()

        update = wedx.are_distributions_different(current_distro, current_assets, new_distribution, new_assets_with_native, change_threshold_allowance)
        print(f'Update needed: {update}')

        if update:
            try:
                wedx.withdraw_from_lending(new_assets)
                wedx.set_portfolio(new_assets, new_distribution)
                wedx.earn_with_lending(new_assets)

                trader_data = wedx.get_trader_data()
                required_interactions = wedx.get_required_interactions()

                if len(trader_data[3]) == required_interactions:
                    wedx.rank_me()

            except ValueError as error:
                print(error)

        score = wedx.get_user_score()
        print(f'Current score: {score}')
        time.sleep(3600)  # Wait for an hour before the next update

if __name__ == "__main__":
    main()