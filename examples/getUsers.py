import os
import sys
import json
import time
import requests
from dotenv import load_dotenv
from web3 import Web3

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from wedx import WedX

# Load environment variables
load_dotenv()
USER_ADDRESS = os.getenv('USER_ADDRESS')
USER_PRIVATE_KEY = os.getenv('USER_PRIVATE_KEY')

# RPC nodes (Use Alchemy if available)
CHAIN_RPCS = {
    'ethereum': os.getenv('RPC_ETHEREUM'),  # Mainnet    
    'base': os.getenv('RPC_BASE'),  # Base mainnet
    'arbitrum': os.getenv('RPC_ARBITRUM'),  # Arbitrum One mainnet
}

# Alchemy API Key
ALCHEMY_API_KEY = os.getenv('ALCHEMY_API_KEY')

# Load network data
with open('../network_data/network_data_v1.json') as f:
    network = json.load(f)

url = 'https://app.wedefin.com/exchange_data.json'
exchange_data = requests.get(url).json()

def fetch_logs_from_alchemy(chain, contract_address):
    if chain == 'ethereum':
        alchemy_url = f'https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}'
    elif chain == 'base':
        alchemy_url = f'https://base-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}'
    elif chain == 'arbitrum':
        alchemy_url = f'https://arb-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}'

    params = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_getLogs",
        "params": [{
            "fromBlock": "0x0",
            "toBlock": "latest",
            "address": contract_address,
        }]
    }

    response = requests.post(alchemy_url, json=params).json()
    transfers = response.get("result", {})

    hashes = []
    for item in transfers:
        hashes.append(item['transactionHash'])
    
    from_addresses = []

    for tx_hash in hashes:
        params = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_getTransactionByHash",
            "params": [tx_hash]
        }
        response = requests.post(alchemy_url, json=params).json()
        tx_data = response.get("result")
        from_addresses.append( w3.to_checksum_address(tx_data.get("from")) )

    return list(set(from_addresses))
 
# Process each chain
total_total_tvl_index = 0
total_total_tvl_pro = 0
for chain_id in CHAIN_RPCS.keys():
    print(f"\n🔹 Processing {chain_id.upper()}...")

    # Connect to Web3
    w3 = Web3(Web3.HTTPProvider(CHAIN_RPCS[chain_id]))
    if not w3.is_connected():
        raise ConnectionError(f"Failed to connect to {chain_id} network")

    # Fetch WEDX Group contract details
    group_contract_address = network[chain_id]['contractWEDXGroup']
    group_contract = w3.eth.contract(address=group_contract_address, abi=network[chain_id]['abiWEDXGroup'])
    index_deployer_address = group_contract.functions.getDeployerIndexAddress().call()
    pro_deployer_address = group_contract.functions.getDeployerProAddress().call()

    index_deployer =  w3.eth.contract(address=index_deployer_address, abi=network[chain_id]['abiWEDXDeployerIndex'])
    pro_deployer =  w3.eth.contract(address=pro_deployer_address, abi=network[chain_id]['abiWEDXDeployerPro'])

    # Get deployer addresses
    allAddress = group_contract.functions.getTreasuryAddress().call()

    # Fetch logs using Alchemy API
    print(f"📡 Fetching logs for {allAddress} on {chain_id}...")
    users = fetch_logs_from_alchemy(chain_id, allAddress)

    print(f"✅ Found {len(users)} logs for {allAddress} on {chain_id}")

    # Optional: Process logs if needed
    total_tvl_index = 0
    total_tvl_pro = 0
    for user in users:
        index_address = index_deployer.functions.getUserIndexPortfolioAddress(user).call()
        pro_address = pro_deployer.functions.getUserProPortfolioAddress(user).call()

        if index_address != '0x0000000000000000000000000000000000000000':
            index_contract = w3.eth.contract(address=index_address, abi=network[chain_id]['abiWEDXIndex'])
            asset_addresses = index_contract.functions.getAddresses().call()
            asset_amounts = index_contract.functions.getAssetsExtended().call()
            total_amount = 0
            for i in range(len(asset_addresses)):
                if asset_addresses[i].lower() != list(exchange_data[chain_id].keys())[-1]:
                    decimals = exchange_data[chain_id][asset_addresses[i].lower()]['inputTokens'][0]['decimals'] if exchange_data[chain_id][asset_addresses[i].lower()]['inputTokens'][0]['id'] == asset_addresses[i].lower() else exchange_data[chain_id][asset_addresses[i].lower()]['inputTokens'][1]['decimals']
                else:
                    decimals = 18
                total_amount += exchange_data[chain_id][asset_addresses[i].lower()]['prices'][-1][1] * asset_amounts[i] / 10 ** decimals
            print(f"Index total amount for {user}: {total_amount}")

        total_tvl_index += total_amount
        total_total_tvl_index += total_amount

        if pro_address != '0x0000000000000000000000000000000000000000':
            pro_contract = w3.eth.contract(address=pro_address, abi=network[chain_id]['abiWEDXPro'])
            asset_addresses = pro_contract.functions.getAddresses().call()
            asset_amounts = pro_contract.functions.getAssetsExtended().call()
            total_amount = 0
            for i in range(len(asset_addresses)):
                if asset_addresses[i].lower() != list(exchange_data[chain_id].keys())[-1]:
                    decimals = exchange_data[chain_id][asset_addresses[i].lower()]['inputTokens'][0]['decimals'] if exchange_data[chain_id][asset_addresses[i].lower()]['inputTokens'][0]['id'] == asset_addresses[i].lower() else exchange_data[chain_id][asset_addresses[i].lower()]['inputTokens'][1]['decimals']
                else:
                    decimals = 18
                total_amount += exchange_data[chain_id][asset_addresses[i].lower()]['prices'][-1][1] * asset_amounts[i] / 10 ** decimals
            print(f"Pro total amount for {user}: {total_amount}")
        
        total_tvl_pro += total_amount
        total_total_tvl_pro += total_amount
    
    print(f"{chain_id} TVL for index: {total_tvl_index}")
    print(f"{chain_id} TVL for pro: {total_tvl_pro}")
    print(f"{chain_id} TVL: {total_tvl_pro + total_tvl_index}")

print(f"TVL for index: {total_total_tvl_index}")
print(f"TVL for pro: {total_total_tvl_pro}")
print(f"Protocol TVL: {total_total_tvl_pro + total_total_tvl_index}")

