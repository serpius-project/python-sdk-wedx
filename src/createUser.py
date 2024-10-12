from eth_account import Account

def create_wallet():
    account = Account.create()
    private_key = account._private_key.hex()
    address = account.address

    print(f"New wallet created:")
    print(f"Address: {address}")
    print(f"Private Key: {private_key}")

    return private_key, address


def get_chain_url(chain_id):
    chain_urls = {
        8453: "https://mainnet.base.org",  # Base mainnet
        42161: "https://arbitrum.llamarpc.com",  # Arbitrum One mainnet
    }
    return chain_urls.get(chain_id, None)


def main():
    # Create a new wallet
    private_key, address = create_wallet()

    
if __name__ == "__main__":
    main()