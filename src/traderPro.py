import json
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv
import os
import time
import requests
import math

f = open('../network_data/network_data_v1.json')
network = json.load(f)
f.close()

module_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(module_dir, '../.env')  
load_dotenv(dotenv_path=dotenv_path)
user_address = os.getenv('USER_ADDRESS')
user_private_key = os.getenv('USER_PRIVATE_KEY')
zero_address = "0x0000000000000000000000000000000000000000"
DISTRO_NORM = 10 ** 6

def get_chain_rpc(chain_id=42161):
    chain_urls = {
        8453: "https://mainnet.base.org",  # Base mainnet
        42161: "https://arbitrum.llamarpc.com",  # Arbitrum One mainnet
    }
    return chain_urls.get(chain_id, None)


def get_chain_name(chain_id=42161):
    chain_names = {
        8453: "base",  # Base mainnet
        42161: "arbitrum",  # Arbitrum One mainnet
    }
    return chain_names.get(chain_id, None)


def get_eth_balance(chain_id, address):
    chain_url = get_chain_rpc(chain_id)
    if not chain_url:
        raise ValueError(f"Unsupported chain ID: {chain_id}")

    w3 = Web3(Web3.HTTPProvider(chain_url))
    if not w3.is_connected():
        raise ConnectionError("Failed to connect to the network")

    if not w3.is_address(address):
        raise ValueError("Invalid Ethereum address")

    balance_wei = w3.eth.get_balance(address)
    balance_eth = w3.from_wei(balance_wei, 'ether')
    return balance_eth


def get_wedx_deployer_address(chain_id):
    chain_rpc = get_chain_rpc(chain_id)
    if not chain_rpc:
        raise ValueError(f"Unsupported chain ID: {chain_id}")

    w3 = Web3(Web3.HTTPProvider(chain_rpc))
    if not w3.is_connected():
        raise ConnectionError("Failed to connect to the network")

    group_contract_address = network[get_chain_name(chain_id)]['contractWEDXGroup']
    group_contract = w3.eth.contract(address=group_contract_address, abi=network[get_chain_name(chain_id)]['abiWEDXGroup'])
    deployer_contract_address = group_contract.functions.getDeployerProAddress().call()

    return deployer_contract_address


def get_trading_account_address(chain_id, user_id):
    chain_rpc = get_chain_rpc(chain_id)
    if not chain_rpc:
        raise ValueError(f"Unsupported chain ID: {chain_id}")

    w3 = Web3(Web3.HTTPProvider(chain_rpc))
    if not w3.is_connected():
        raise ConnectionError("Failed to connect to the network")

    group_contract_address = network[get_chain_name(chain_id)]['contractWEDXGroup']
    group_contract = w3.eth.contract(address=group_contract_address, abi=network[get_chain_name(chain_id)]['abiWEDXGroup'])
    deployer_contract_address = group_contract.functions.getDeployerProAddress().call()

    deployer_contract = w3.eth.contract(address=deployer_contract_address, abi=network[get_chain_name(chain_id)]['abiWEDXDeployerPro'])
    pro_account_address = deployer_contract.functions.getUserProPortfolioAddress(user=user_id).call()

    return pro_account_address


def create_trading_account_address(chain_id, user_id):
    pro_account_address = get_trading_account_address(chain_id, user_id)
    if pro_account_address != zero_address:
        return pro_account_address
    else:
        chain_rpc = get_chain_rpc(chain_id)
        if not chain_rpc:
            raise ValueError(f"Unsupported chain ID: {chain_id}")

        w3 = Web3(Web3.HTTPProvider(chain_rpc))
        if not w3.is_connected():
            raise ConnectionError("Failed to connect to the network")

        group_contract_address = network[get_chain_name(chain_id)]['contractWEDXGroup']
        group_contract = w3.eth.contract(address=group_contract_address, abi=network[get_chain_name(chain_id)]['abiWEDXGroup'])
        deployer_contract_address = group_contract.functions.getDeployerProAddress().call()

        deployer_contract = w3.eth.contract(address=deployer_contract_address, abi=network[get_chain_name(chain_id)]['abiWEDXDeployerPro'])
        contract_function = getattr(deployer_contract.functions, "createProPortfolio")

        # Get the account from the private key
        account = Account.from_key(user_private_key)

        # Estimate gas
        gas_estimate = contract_function().estimate_gas({'from': account.address})

        # Prepare the transaction
        transaction = contract_function().build_transaction({
            'chainId': chain_id,
            'gas': int(gas_estimate * 1.2),  # Add 20% buffer to gas estimate
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(account.address),
        })

        # Sign the transaction
        signed_txn = account.sign_transaction(transaction)

        # Send the transaction
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)

        # Wait for the transaction receipt
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print("Transaction hash: ", tx_receipt['transactionHash'].hex())

        time.sleep(1)
        pro_account_address = get_trading_account_address(chain_id, user_id)

        return pro_account_address


def deposit_eth(chain_id, user_id, eth_amount):
    pro_account_address = get_trading_account_address(chain_id, user_id)
    if pro_account_address == zero_address:
        raise ValueError("User does not have an account")
    else:
        chain_rpc = get_chain_rpc(chain_id)
        if not chain_rpc:
            raise ValueError(f"Unsupported chain ID: {chain_id}")

        w3 = Web3(Web3.HTTPProvider(chain_rpc))
        if not w3.is_connected():
            raise ConnectionError("Failed to connect to the network")

        pro_contract = w3.eth.contract(address=pro_account_address, abi=network[get_chain_name(chain_id)]['abiWEDXPro'])
        pro_contract_function = getattr(pro_contract.functions, "deposit")

        # Get the account from the private key
        account = Account.from_key(user_private_key)

        # Convert ETH amount to Wei
        value_in_wei = w3.to_wei(eth_amount, 'ether')

        # Estimate gas
        gas_estimate = pro_contract_function().estimate_gas({'from': account.address, 'value': value_in_wei})

        # Prepare the transaction
        transaction = pro_contract_function().build_transaction({
            'chainId': chain_id,
            'gas': int(gas_estimate * 1.2),  # Add 20% buffer to gas estimate
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(account.address),
            'value': value_in_wei
        })

        # Sign the transaction
        signed_txn = account.sign_transaction(transaction)

        # Send the transaction
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)

        # Wait for the transaction receipt
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print("Transaction hash: ", tx_receipt['transactionHash'].hex())

        return True


def get_assets_info(chain_id):
    chain_name = get_chain_name(chain_id)
    url = 'https://app.wedefin.com/exchange_data.json'
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
        return response.json()[chain_name]
    except requests.RequestException as e:
        print(f"An error occurred while fetching the JSON: {e}")
        return None


def normalize_distribution(distro):
    distro = distro.copy() 
    distro_size = len(distro)
    total = sum(distro)
    
    if total == 0:
        return distro
    
    # Normalize the distribution
    for i in range(distro_size):
        distro[i] = math.floor((distro[i] * DISTRO_NORM) / total)
    
    # Find max and min non-zero values
    total = 0
    index_max = 0
    index_min = 0
    value_max = 0
    value_min = 2 * DISTRO_NORM
    
    for i in range(distro_size):
        total += distro[i]
        if distro[i] > value_max and distro[i] != 0:
            value_max = distro[i]
            index_max = i
        if distro[i] < value_min and distro[i] != 0:
            value_min = distro[i]
            index_min = i
    
    # Adjust for rounding errors
    if total < DISTRO_NORM:
        distro[index_min] += DISTRO_NORM - total
    elif total > DISTRO_NORM:
        distro[index_max] -= total - DISTRO_NORM
    
    return distro


def create_ew_portfolio(chain_id):
    assets_info = get_assets_info(chain_id)
    assets_ew_portfolio_top_10_non_native = list(assets_info.keys())[:10]  #if the native asset is part of the portfolio then choose top 9, because the native asset will be added automatically

    distribution = [1.0 for i in range(len(assets_ew_portfolio_top_10_non_native))]
    distribution.append(0.0) #adding native allocation

    distribution = normalize_distribution(distribution)
    return assets_ew_portfolio_top_10_non_native, distribution


def main():

    chain = 42161

    print("User address: ", user_address)
    print("Current ETH balance: ", get_eth_balance(chain, user_address) )

    deployer_pro_address = get_wedx_deployer_address(chain_id=chain)
    print("Deployer address: ", deployer_pro_address)

    trading_account_address = get_trading_account_address(chain_id=chain, user_id=user_address)
    print( "User account: ", trading_account_address )

    if trading_account_address == zero_address:
        print( "User does not have an account yet" )

        trading_account_address = create_trading_account_address(chain_id=chain, user_id=user_address)
        print( "User account: ", trading_account_address )

#    deposit_eth(chain_id=chain, user_id=user_address, eth_amount=0.01)

    assets, portfolio = create_ew_portfolio(chain_id=chain) 
    print(assets, portfolio)


if __name__ == "__main__":
    main()