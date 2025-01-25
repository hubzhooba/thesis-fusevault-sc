# thesis-fusevault-sc
FuseVault API combines the power of blockchain, IPFS, and traditional storage to mitigate the limitations of on-chain storage while maintaining security and decentralization.


Instructions to run for Windows:

- Make sure Python is installed on your computer
- Create a virtual environment with `python -m venv venv`
- Activate the virtual environment by running `venv/Scripts/activate`
- Install dependencies with `pip install -r requirements.txt`
- Create a `.env` file in the root project folder, then add the `MONGODB_URI` variable
- Run the FastAPI server with `uvicorn main:app --reload`
- Access the server on `http://127.0.0.1:8000/` (default setting)
- Once finished, run `deactivate` to exit the virtual environment

Instructions to run for macOS:

- Make sure Python is installed on your computer
- Create a virtual environment with `python3 -m venv venv`
- Activate the virtual environment by running `source venv/bin/activate`
- Install dependencies with `pip install -r requirements.txt`
- Create a `.env` file in the root project folder, then add the `MONGODB_URI` variable
- Install SSL certificates on your system using `/Applications/Python\ 3.x/Install\ Certificates.command` (replace 3.x with your Python version)
- Run the FastAPI server with `uvicorn main:app --reload`
- Access the server on `http://127.0.0.1:8000/` (default setting)
- Once finished, run `deactivate` to exit the virtual environment

To view API documentation and execute operation methods:
- Access the server on default url:`http://127.0.0.1:8000/docs` 

To add dependencies:
- Add the new dependency in a new line to `requirements.in`
- Run `pip-compile requirements.in` (ensure you are in the virtual environment)
- Rerun `pip install -r requirements.txt`


# Using the Pre-Deployed Contract
- If you do not want to deploy your own instance of the contract, you can use the pre-deployed contract instance.
- IF YOU NEED TO DEPLOY YOUR OWN INSTANCE OF THE CONTRACT SCROLL TO THE NEXT SECTION.
- Update your .env file with the following details:
```
MONGO_URI=mongodb+srv://admin:admin@fusevault.4viqu.mongodb.net/?retryWrites=true&w=majority&appName=Fusevault
WALLET_ADDRESS=0x00823FB00C2cDf1841d52bC91affB661Df39466F
PRIVATE_KEY=d3e25b3f050f2c669e47c23bbfed8a141c532ed0fd1ca5f13b055e716414a997
INFURA_URL=https://sepolia.infura.io/v3/d08109f8a361490d8222169780f7aaa1
CONTRACT_ADDRESS=0x369ca86929735eb467c6abcf51b98542b4671b62
```
- Start the server `uvicorn main:app --reload`
  
# Smart Contract Developers
- Deploying the Smart Contract Yourself
Follow these steps to deploy the smart contract:
1. Download MetaMask Wallet 
3. Set Up Your MetaMask Wallet:
   - Switch to the Sepolia Testnet in your MetaMask settings.
   - Export your private key:
   - Go to your wallet settings → Security & Privacy → Export Private Key.
   - Copy your private key.
4. Set Up the .env File:
```
MONGO_URI=mongodb+srv://admin:admin@fusevault.4viqu.mongodb.net/?retryWrites=true&w=majority&appName=Fusevault
WALLET_ADDRESS=[INSERT YOUR METAMASK WALLET ADDRESS]
PRIVATE_KEY=[PASTE YOUR PRIVATE KEY]
INFURA_URL=https://sepolia.infura.io/v3/d08109f8a361490d8222169780f7aaa1
CONTRACT_ADDRESS=[INSERT CONTRACT ADDRESS]
```
5. Open Remix IDE
- In the Deploy & Run Transactions panel:
  - Choose Injected Provider - MetaMask as your environment.
  - Ensure your MetaMask wallet is connected.
- Open CIDstorage.sol and save it then deploy.
- Retrieve the Contract Address (After deployment, expand the deployed contract in the Remix IDE.)
- Copy the contract address and paste it into your .env file
- Start the server `uvicorn main:app --reload`
