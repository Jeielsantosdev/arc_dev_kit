# Arc DevKit — Mainnet Readiness Checklist

Arc mainnet is expected summer 2026. This checklist tracks what the DevKit
needs before `ARC_NETWORK=mainnet` is a safe, supported default — the path
to v1.0. It complements `SPRINTS_2026H2.md` (Sprint 1's multi-network
groundwork is what makes this checklist possible: a network switch should be
*configuration only*, never a code change).

## 1. Network configuration

- [ ] `arc_devkit/networks.py` — `NETWORKS["mainnet"]` filled in with real values:
  - [ ] `chain_id`
  - [ ] `rpc_url` (at least one reliable public endpoint)
  - [ ] `explorer_url`
  - [ ] `contracts.usdc`
  - [ ] `contracts.eurc` (if EURC is live on Arc mainnet at launch)
  - [ ] `contracts.cctp_token_messenger` + a documented CCTP domain ID (`arc_devkit/bridge/`)
  - [ ] `contracts.gateway` (if applicable)
- [ ] Run `arcdevkit network check-mainnet` — must report all checks configured
- [ ] Dry-run the network switch in a scratch `.env` (`ARC_NETWORK=mainnet`,
      no `ARC_RPC_URL`/`ARC_CHAIN_ID` override) and confirm `arcdevkit status`
      connects successfully
- [ ] Confirm testnet remains the default (`DEFAULT_NETWORK` in
      `arc_devkit/networks.py`) until mainnet is genuinely stable — flipping
      the default is a deliberate, separate decision

## 2. Contract address validation

- [ ] Cross-check every mainnet address above against Circle/Arc's official
      docs (docs.arc.io) or verified block explorer source — never trust a
      single unverified source for a mainnet contract address
- [ ] `arc_devkit/stablecoins/token.py` — replace `USDC_ARC_TESTNET_ADDRESS`
      usage with the resolved network's `contracts.usdc` wherever it's still
      hardcoded as a testnet default
- [ ] `arc_devkit/paymaster/detector.py` — update `detect_paymaster()` once a
      real paymaster contract/bundler is published (currently always
      `available=False`)
- [ ] `arc_devkit/agents/identity.py` / `jobs.py` — confirm whether Arc
      publishes canonical ERC-8004/ERC-8183 registry addresses, or whether
      these remain bring-your-own-registry indefinitely

## 3. Guardrails & safety defaults

- [ ] Re-verify `MAX_SPEND_PER_DAY_USDC` / `AGENT_ALLOWED_RECIPIENTS`
      guidance in `.env.example` — mainnet USDC has real value; empty
      guardrails should be loudly discouraged in docs, not just a warning log
- [ ] Confirm `ENV=production` behavior (mandatory `API_KEY`, HSTS, HTTPS
      redirect in `arc_devkit/api/main.py`) is documented as required for any
      mainnet-facing deployment of the REST API
- [ ] Re-run the security sweep (`bandit -r arc_devkit -ll`, `pip-audit`) with
      mainnet-relevant code paths exercised, not just testnet defaults

## 4. Breaking-change communication

- [ ] Publish a migration note in `CHANGELOG.md` (see `cliff.toml` /
      git-cliff) for the release that flips any mainnet-related default
- [ ] Call out in `README.md` and `docs/` that testnet and mainnet USDC/EURC
      contract addresses differ — code that hardcodes a testnet address will
      silently misbehave on mainnet
- [ ] Version the release as a **major** bump if any default behavior changes
      (e.g. `DEFAULT_NETWORK` flips from `testnet` to `mainnet`)

## 5. Path to v1.0

- [ ] All items above checked for at least one full release cycle on mainnet
      without a rollback
- [ ] `arcdevkit network check-mainnet` green in CI against real mainnet config
- [ ] No outstanding "not published yet" placeholders in `CLAUDE.md`'s
      module descriptions for bridge/paymaster/agent-economy features that
      are meant to be live at v1.0
