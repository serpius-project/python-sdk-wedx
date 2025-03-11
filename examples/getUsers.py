import os
import sys
import json
import time
import requests
from dotenv import load_dotenv
from web3 import Web3
import datetime
import pandas as pd

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

def get_latest_block_from_csv(chain):
    """Reads the latest block number from the saved CSV file if available."""
    csv_filename = f"daily_tvl_data_{chain}.csv"
    if os.path.exists(csv_filename):
        df = pd.read_csv(csv_filename)
        if not df.empty:
            return hex(df['block_number'].max())  # Get the latest block number
    return "0x0"  # Default to first block if no data exists

def get_users_csv(chain):
    csv_filename = f"daily_tvl_data_{chain}.csv"
    if os.path.exists(csv_filename):
        df = pd.read_csv(csv_filename)
        if not df.empty:
            return df['user_address'].unique().tolist()  
    return [] 

def fetch_logs_from_alchemy(chain, contract_address, from_block):
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
            "fromBlock": from_block,
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
    block_numbers = []

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
        block_numbers.append( int(tx_data.get("blockNumber"), 16) )

    return list(set(from_addresses)), block_numbers
 
# Process each chain
total_total_tvl_index = 0
total_total_tvl_pro = 0

# Get current timestamp
current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
chain_tvl_data = {}
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

    # Read latest block number from CSV
    latest_block = get_latest_block_from_csv(chain_id)
    print(f"📡 Fetching logs from block {latest_block} for {allAddress} on {chain_id}...")
    users, block_numbers = fetch_logs_from_alchemy(chain_id, allAddress, latest_block)
    print(f"✅ Found {len(users)} logs for {allAddress} on {chain_id}")

    # Optional: Process logs if needed
    total_tvl_index = 0
    total_tvl_pro = 0
    # Initialize TVL data list
    daily_tvl_data = []

    users = users + get_users_csv(chain_id)
    users = list(set(users))
    for user in users:
        index_address = index_deployer.functions.getUserIndexPortfolioAddress(user).call()
        pro_address = pro_deployer.functions.getUserProPortfolioAddress(user).call()

        total_amount_index = 0
        if index_address != '0x0000000000000000000000000000000000000000':
            index_contract = w3.eth.contract(address=index_address, abi=network[chain_id]['abiWEDXIndex'])
            asset_addresses = index_contract.functions.getAddresses().call()
            asset_amounts = index_contract.functions.getAssetsExtended().call()
            for i in range(len(asset_addresses)):
                if asset_addresses[i].lower() != list(exchange_data[chain_id].keys())[-1]:
                    decimals = exchange_data[chain_id][asset_addresses[i].lower()]['inputTokens'][0]['decimals'] if exchange_data[chain_id][asset_addresses[i].lower()]['inputTokens'][0]['id'] == asset_addresses[i].lower() else exchange_data[chain_id][asset_addresses[i].lower()]['inputTokens'][1]['decimals']
                else:
                    decimals = 18
                total_amount_index += exchange_data[chain_id][asset_addresses[i].lower()]['prices'][-1][1] * asset_amounts[i] / 10 ** decimals
            print(f"Index total amount for {user}: {total_amount_index}")

        total_tvl_index += total_amount_index
        total_total_tvl_index += total_amount_index

        total_amount_pro = 0
        if pro_address != '0x0000000000000000000000000000000000000000':
            pro_contract = w3.eth.contract(address=pro_address, abi=network[chain_id]['abiWEDXPro'])
            asset_addresses = pro_contract.functions.getAddresses().call()
            asset_amounts = pro_contract.functions.getAssetsExtended().call()
            for i in range(len(asset_addresses)):
                if asset_addresses[i].lower() != list(exchange_data[chain_id].keys())[-1]:
                    decimals = exchange_data[chain_id][asset_addresses[i].lower()]['inputTokens'][0]['decimals'] if exchange_data[chain_id][asset_addresses[i].lower()]['inputTokens'][0]['id'] == asset_addresses[i].lower() else exchange_data[chain_id][asset_addresses[i].lower()]['inputTokens'][1]['decimals']
                else:
                    decimals = 18
                total_amount_pro += exchange_data[chain_id][asset_addresses[i].lower()]['prices'][-1][1] * asset_amounts[i] / 10 ** decimals
            print(f"Pro total amount for {user}: {total_amount_pro}")
    
        total_tvl_pro += total_amount_pro
        total_total_tvl_pro += total_amount_pro
    
        # Append user data
        daily_tvl_data.append({
            "timestamp": current_timestamp,
            "user_address": user,
            "amount_index": total_amount_index,
            "amount_pro": total_amount_pro,
            "block_number": max(block_numbers)
        })


    print(f"{chain_id} TVL for index: {total_tvl_index}")
    print(f"{chain_id} TVL for pro: {total_tvl_pro}")
    print(f"{chain_id} TVL: {total_tvl_pro + total_tvl_index}")

    # Load existing CSV if it exists
    csv_filename = f"daily_tvl_data_{chain_id}.csv"
    if os.path.exists(csv_filename):
        existing_df = pd.read_csv(csv_filename)
        existing_df["timestamp"] = pd.to_datetime(existing_df["timestamp"])
        max_existing_timestamp = existing_df["timestamp"].max()
        new_data_df = pd.DataFrame(daily_tvl_data)
        new_data_df["timestamp"] = pd.to_datetime(new_data_df["timestamp"])
        new_data_df = new_data_df[new_data_df["timestamp"] > max_existing_timestamp]
        df_final = pd.concat([existing_df, new_data_df], ignore_index=True)
    else:
        df_final = pd.DataFrame(daily_tvl_data)

    # Save the updated DataFrame
    df_final.to_csv(csv_filename, index=False)
    print(f"✅ TVL data saved to {csv_filename}")

print(f"TVL for index: {total_total_tvl_index}")
print(f"TVL for pro: {total_total_tvl_pro}")
print(f"Protocol TVL: {total_total_tvl_pro + total_total_tvl_index}")

