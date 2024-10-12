import json
from web3 import Web3
from dotenv import load_dotenv
import os


f = open('../network_data/network_data_v1.json')
network = json.load(f)
f.close()

module_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(module_dir, '../.env')  
load_dotenv(dotenv_path=dotenv_path)
user_address = os.getenv('USER_ADDRESS')
zero_address = "0x0000000000000000000000000000000000000000"


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


if __name__ == "__main__":
    main()