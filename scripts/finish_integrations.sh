#!/usr/bin/env bash
#
# Everything that needs credentials and a network route, in order.
#
# Built and tested against a local EVM in CI; this is the same path pointed at
# Base Sepolia and the live ACP API. Run it from the repository root.
#
#   ./scripts/finish_integrations.sh
#
# It checks every prerequisite before touching anything, so a missing key or an
# unfunded wallet fails in the first ten seconds rather than halfway through a
# deployment.

set -euo pipefail

PY="${PY:-.venv/bin/python}"
fail() { printf '\n  %s\n' "$*" >&2; exit 1; }
step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

[ -x "$PY" ] || fail "no interpreter at $PY — run: python -m venv .venv && .venv/bin/pip install -e 'packages/succession[dev,service,acp,chain]'"

step "Preflight"

for var in BASE_SEPOLIA_RPC_URL DEPLOYER_PRIVATE_KEY SELLER_PRIVATE_KEY BUYER_PRIVATE_KEY; do
  [ -n "${!var:-}" ] || fail "$var is not set. See the README's 'Finishing the integrations'."
done

# Reachability first: a 403 from an egress policy looks nothing like an RPC
# error once web3 has wrapped it, and finding out mid-deploy is worse.
"$PY" - <<'PYCHECK' || fail "cannot reach BASE_SEPOLIA_RPC_URL"
import os, sys
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
w3 = Web3(Web3.HTTPProvider(os.environ["BASE_SEPOLIA_RPC_URL"], request_kwargs={"timeout": 20}))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
if not w3.is_connected():
    sys.exit(1)
print(f"  chain id {w3.eth.chain_id}")
from eth_account import Account
for name in ("DEPLOYER_PRIVATE_KEY", "SELLER_PRIVATE_KEY", "BUYER_PRIVATE_KEY"):
    a = Account.from_key(os.environ[name])
    bal = w3.from_wei(w3.eth.get_balance(a.address), "ether")
    flag = "" if bal > 0 else "   <-- UNFUNDED"
    print(f"  {name:<22} {a.address}  {bal} ETH{flag}")
PYCHECK

step "Contracts"
( cd contracts && npm install --silent && npm run build --silent )

step "Virtuals ACP"
if [ -n "${ACP_ENTITY_ID:-}" ]; then
  "$PY" -m succession.acp_cli status
  "$PY" -m succession.acp_cli snapshot --out web/public/acp-snapshot.json
  echo "  ACP history captured. Sync it into a seller tenant with:"
  echo "    $PY -m succession.acp_cli sync --db <store.db> --tenant <tenant>"
else
  echo "  skipped — ACP_ENTITY_ID unset."
  echo "  Register through the ACP Tech Playbook first, then export:"
  echo "    WHITELISTED_WALLET_PRIVATE_KEY, AGENT_WALLET_ADDRESS, ACP_ENTITY_ID"
fi

step "Deploy to Base Sepolia"
"$PY" scripts/deploy_base_sepolia.py

step "Run 5 real transfers"
"$PY" scripts/run_transfers.py --count 5 --corrupt 3

step "Done"
echo "  deployments/base-sepolia.json   addresses"
echo "  deployments/transfers.json      every tx hash and both roots"
echo
echo "  Fold the ledger into the hosted UI so it shows real transactions:"
echo "    $PY scripts/record_run.py"
