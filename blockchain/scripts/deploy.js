const { ethers } = require("hardhat");

async function main() {
  const ContractFactory = await ethers.getContractFactory("FuseVaultRegistry");
  const contract = await ContractFactory.deploy(); // Start deployment

  // Wait for full deployment
  const deployedContract = await contract.waitForDeployment();

  // Get the actual deployed address
  const address = await deployedContract.getAddress();
  console.log("FuseVaultRegistry deployed to:", address);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
