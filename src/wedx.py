import json
from web3 import Web3
from eth_account import Account
import time
import requests
import math

class WedX:
    def __init__(self, chain_id, user_address, user_private_key, chain_rpcs):
        self.chain_id = chain_id
        self.user_address = user_address
        self.user_private_key = user_private_key
        self.zero_address = "0x0000000000000000000000000000000000000000"
        self.DISTRO_NORM = 10 ** 6
        self.chain_rpc = chain_rpcs

        # Load network data
        with open('../network_data/network_data_v1.json') as f:
            self.network = json.load(f)

        self.w3 = Web3(Web3.HTTPProvider(self.get_chain_rpc()))
        if not self.w3.is_connected():
            raise ConnectionError("Failed to connect to the network")

    def get_chain_rpc(self):
        return self.chain_rpc.get(self.chain_id, None)

    def get_chain_name(self):
        chain_names = {
            8453: "base",  # Base mainnet
            42161: "arbitrum",  # Arbitrum One mainnet
        }
        return chain_names.get(self.chain_id, None)

    def normalize_distribution(self, distro):
        distro = distro.copy() 
        distro_size = len(distro)
        total = sum(distro)
        
        if total == 0:
            return distro
        
        # Normalize the distribution
        for i in range(distro_size):
            distro[i] = math.floor((distro[i] * self.DISTRO_NORM) / total)
        
        # Find max and min non-zero values
        total = 0
        index_max = 0
        index_min = 0
        value_max = 0
        value_min = 2 * self.DISTRO_NORM
        
        for i in range(distro_size):
            total += distro[i]
            if distro[i] > value_max and distro[i] != 0:
                value_max = distro[i]
                index_max = i
            if distro[i] < value_min and distro[i] != 0:
                value_min = distro[i]
                index_min = i
        
        # Adjust for rounding errors
        if total < self.DISTRO_NORM:
            distro[index_min] += self.DISTRO_NORM - total
        elif total > self.DISTRO_NORM:
            distro[index_max] -= total - self.DISTRO_NORM
        
        return distro

    def are_distributions_different(self, distro1, addresses1, distro2, addresses2, threshold):
        if len(distro1) != len(distro2) or len(addresses1) != len(addresses2):
            return True
        
        addresses1 = addresses1.copy()
        addresses2 = addresses2.copy()

        for i in range(len(addresses1)):
            addresses1[i] = addresses1[i].lower()
            addresses2[i] = addresses2[i].lower()

        dict1 = dict(zip(addresses1, distro1))
        dict2 = dict(zip(addresses2, distro2))
        
        if set(addresses1) != set(addresses2):
            return True
        
        total_diff = sum(abs(dict1[addr] - dict2[addr]) for addr in addresses1)
        print(f'Distributions differ by {100 * total_diff / self.DISTRO_NORM / 2}%, expected {100 * threshold / self.DISTRO_NORM}%')
        return total_diff > 2 * threshold

    def get_eth_balance(self, address):
        if not self.w3.is_address(address):
            raise ValueError("Invalid Ethereum address")
        balance_wei = self.w3.eth.get_balance(address)
        return self.w3.from_wei(balance_wei, 'ether')

    def get_wedx_deployer_address(self):
        group_contract_address = self.network[self.get_chain_name()]['contractWEDXGroup']
        group_contract = self.w3.eth.contract(address=group_contract_address, abi=self.network[self.get_chain_name()]['abiWEDXGroup'])
        return group_contract.functions.getDeployerProAddress().call()

    def get_trading_account_address(self):
        group_contract_address = self.network[self.get_chain_name()]['contractWEDXGroup']
        group_contract = self.w3.eth.contract(address=group_contract_address, abi=self.network[self.get_chain_name()]['abiWEDXGroup'])
        deployer_contract_address = group_contract.functions.getDeployerProAddress().call()
        deployer_contract = self.w3.eth.contract(address=deployer_contract_address, abi=self.network[self.get_chain_name()]['abiWEDXDeployerPro'])
        return deployer_contract.functions.getUserProPortfolioAddress(user=self.user_address).call()

    def get_manager_account_address(self):
        group_contract_address = self.network[self.get_chain_name()]['contractWEDXGroup']
        group_contract = self.w3.eth.contract(address=group_contract_address, abi=self.network[self.get_chain_name()]['abiWEDXGroup'])
        return group_contract.functions.getAssetManagerAddress().call()

    def create_trading_account_address(self):
        pro_account_address = self.get_trading_account_address()
        if pro_account_address != self.zero_address:
            return pro_account_address

        group_contract_address = self.network[self.get_chain_name()]['contractWEDXGroup']
        group_contract = self.w3.eth.contract(address=group_contract_address, abi=self.network[self.get_chain_name()]['abiWEDXGroup'])
        deployer_contract_address = group_contract.functions.getDeployerProAddress().call()
        deployer_contract = self.w3.eth.contract(address=deployer_contract_address, abi=self.network[self.get_chain_name()]['abiWEDXDeployerPro'])

        account = Account.from_key(self.user_private_key)
        
        # Estimate gas
        gas_estimate = deployer_contract.functions.createProPortfolio().estimate_gas({'from': account.address})

        tx = deployer_contract.functions.createProPortfolio().build_transaction({
            'chainId': self.chain_id,
            'gas': int(gas_estimate * 1.2),  # Add 20% buffer to gas estimate
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(account.address),
        })

        signed_tx = account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Transaction hash: {tx_receipt}")
        time.sleep(1)
        return self.get_trading_account_address()

    def deposit_eth(self, eth_amount):
        pro_account_address = self.get_trading_account_address()
        if pro_account_address == self.zero_address:
            raise ValueError("User does not have an account")

        pro_contract = self.w3.eth.contract(address=pro_account_address, abi=self.network[self.get_chain_name()]['abiWEDXPro'])
        account = Account.from_key(self.user_private_key)
        value_in_wei = self.w3.to_wei(eth_amount, 'ether')

        # Estimate gas
        gas_estimate = pro_contract.functions.deposit().estimate_gas({'from': account.address, 'value': value_in_wei})

        tx = pro_contract.functions.deposit().build_transaction({
            'chainId': self.chain_id,
            'gas': int(gas_estimate * 1.2),  # Add 20% buffer to gas estimate
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(account.address),
            'value': value_in_wei
        })

        signed_tx = account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Transaction hash: {tx_receipt}")
        return tx_receipt

    def withdraw_eth(self, perc_amount):
        pro_account_address = self.get_trading_account_address()
        if pro_account_address == self.zero_address:
            raise ValueError("User does not have an account")

        pro_contract = self.w3.eth.contract(address=pro_account_address, abi=self.network[self.get_chain_name()]['abiWEDXPro'])
        account = Account.from_key(self.user_private_key)

        # Estimate gas
        gas_estimate = pro_contract.functions.withdraw(perc_amount).estimate_gas({'from': account.address})

        tx = pro_contract.functions.withdraw(perc_amount).build_transaction({
            'chainId': self.chain_id,
            'gas': int(gas_estimate * 1.2),  # Add 20% buffer to gas estimate
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(account.address)
        })

        signed_tx = account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Transaction hash: {tx_receipt}")
        return tx_receipt

    def get_assets_info(self):
        url = 'https://app.wedefin.com/exchange_data.json'
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()[self.get_chain_name()]
        except requests.RequestException as e:
            print(f"An error occurred while fetching the JSON: {e}")
            return None

    def set_portfolio(self, assets, portfolio):
        pro_account_address = self.get_trading_account_address()
        if pro_account_address == self.zero_address:
            raise ValueError("User does not have an account")

        pro_contract = self.w3.eth.contract(address=pro_account_address, abi=self.network[self.get_chain_name()]['abiWEDXPro'])
        account = Account.from_key(self.user_private_key)

        # Estimate gas
        gas_estimate = pro_contract.functions.setPortfolio(assets, portfolio).estimate_gas({'from': account.address})

        tx = pro_contract.functions.setPortfolio(assets, portfolio).build_transaction({
            'chainId': self.chain_id,
            'gas': int(gas_estimate * 1.2),  # Add 20% buffer to gas estimate
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(account.address)
        })

        signed_tx = account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Transaction hash: {tx_receipt}")
        return tx_receipt

    def get_distribution(self):
        pro_account_address = self.get_trading_account_address()
        if pro_account_address == self.zero_address:
            raise ValueError("User does not have an account")

        pro_contract = self.w3.eth.contract(address=pro_account_address, abi=self.network[self.get_chain_name()]['abiWEDXPro'])
        return pro_contract.functions.getActualDistribution().call()

    def get_distribution_threshold(self):
        pro_account_address = self.get_trading_account_address()
        if pro_account_address == self.zero_address:
            raise ValueError("User does not have an account")

        pro_contract = self.w3.eth.contract(address=pro_account_address, abi=self.network[self.get_chain_name()]['abiWEDXPro'])
        return pro_contract.functions.getMinPercAllowance().call()

    def get_assets_addresses(self):
        pro_account_address = self.get_trading_account_address()
        if pro_account_address == self.zero_address:
            raise ValueError("User does not have an account")

        pro_contract = self.w3.eth.contract(address=pro_account_address, abi=self.network[self.get_chain_name()]['abiWEDXPro'])
        return pro_contract.functions.getAddresses().call()

    def get_user_score(self):
        manager_account_address = self.get_manager_account_address()
        if manager_account_address == self.zero_address:
            raise ValueError("Error retrieving manager contract address")

        manager_contract = self.w3.eth.contract(address=manager_account_address, abi=self.network[self.get_chain_name()]['abiWEDXManager'])
        return manager_contract.functions.getTraderScore(self.user_address).call()

    def get_trader_data(self):
        manager_account_address = self.get_manager_account_address()
        if manager_account_address == self.zero_address:
            raise ValueError("Error retrieving manager contract address")

        manager_contract = self.w3.eth.contract(address=manager_account_address, abi=self.network[self.get_chain_name()]['abiWEDXManager'])
        return manager_contract.functions.getTraderData(self.user_address).call()

    def get_required_interactions(self):
        manager_account_address = self.get_manager_account_address()
        if manager_account_address == self.zero_address:
            raise ValueError("Error retrieving manager contract address")

        manager_contract = self.w3.eth.contract(address=manager_account_address, abi=self.network[self.get_chain_name()]['abiWEDXManager'])
        return manager_contract.functions.getNPoints().call()

    def earn_with_lending(self, assets):
        pro_account_address = self.get_trading_account_address()
        if pro_account_address == self.zero_address:
            raise ValueError("User does not have an account")

        pro_contract = self.w3.eth.contract(address=pro_account_address, abi=self.network[self.get_chain_name()]['abiWEDXPro'])
        account = Account.from_key(self.user_private_key)

        protocol_id = [0 for _ in range(len(assets))]
        
        # Estimate gas
        gas_estimate = pro_contract.functions.supplyLendTokens(assets, protocol_id).estimate_gas({'from': account.address})

        tx = pro_contract.functions.supplyLendTokens(assets, protocol_id).build_transaction({
            'chainId': self.chain_id,
            'gas': int(gas_estimate * 1.2),  # Add 20% buffer to gas estimate
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(account.address)
        })

        signed_tx = account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Transaction hash: {tx_receipt}")
        return tx_receipt

    def withdraw_from_lending(self, assets):
        pro_account_address = self.get_trading_account_address()
        if pro_account_address == self.zero_address:
            raise ValueError("User does not have an account")

        pro_contract = self.w3.eth.contract(address=pro_account_address, abi=self.network[self.get_chain_name()]['abiWEDXPro'])
        account = Account.from_key(self.user_private_key)

        # Estimate gas
        gas_estimate = pro_contract.functions.withdrawLendTokens(assets).estimate_gas({'from': account.address})
        base_fee = self.w3.eth.get_block('pending')['baseFeePerGas']
        priority_fee = self.w3.eth.max_priority_fee

        tx = pro_contract.functions.withdrawLendTokens(assets).build_transaction({
            'chainId': self.chain_id,
            'gas': int(gas_estimate * 1.2),  # Add 20% buffer to gas estimate
#            'gasPrice': self.w3.eth.gas_price,
            'maxFeePerGas': int( base_fee + priority_fee * 1.5 ),  # Increase total fee
            'maxPriorityFeePerGas': int( priority_fee * 1.5 ),     # Increase priority fee
            'nonce': self.w3.eth.get_transaction_count(account.address)
        })

        signed_tx = account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Transaction hash: {tx_receipt}")
        return tx_receipt

    def rank_me(self):
        pro_account_address = self.get_trading_account_address()
        if pro_account_address == self.zero_address:
            raise ValueError("User does not have an account")

        pro_contract = self.w3.eth.contract(address=pro_account_address, abi=self.network[self.get_chain_name()]['abiWEDXPro'])
        account = Account.from_key(self.user_private_key)

        # Estimate gas
        gas_estimate = pro_contract.functions.rankMe().estimate_gas({'from': account.address})

        tx = pro_contract.functions.rankMe().build_transaction({
            'chainId': self.chain_id,
            'gas': int(gas_estimate * 1.2),  # Add 20% buffer to gas estimate
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(account.address)
        })

        signed_tx = account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Transaction hash: {tx_receipt}")
        return tx_receipt