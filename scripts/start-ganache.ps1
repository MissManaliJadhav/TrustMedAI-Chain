param(
    [int]$Port = 8545,
    [int]$Accounts = 10,
    [int]$DefaultBalanceEther = 1000
)

$ganacheCmd = "npx ganache@latest --chain.vm=ethereumjs --port $Port --accounts $Accounts --defaultBalanceEther $DefaultBalanceEther --wallet.unlockedAccounts 0"
Write-Host "Starting Ganache on http://localhost:$Port"
Write-Host "Command: $ganacheCmd"
Invoke-Expression $ganacheCmd
