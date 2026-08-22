# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A funding-rate arbitrage bot that hedges a position across two exchanges (default: Bitget + Gate) and keeps
both sides balanced. It's a FastAPI "control plane" server plus two long-running worker processes, each
normally run as its own Docker container:

- **Server** (`Server/App.py`) — FastAPI app exposing `/bot1api/*`. Starts/stops the worker containers via the
  Docker CLI (`docker create`/`start`/`stop`, invoked with `subprocess`) and reports their running status.
- **ADLControl** (`MainProcess/ADLControl/`) — watches live positions on both exchanges via `ccxt.pro` websockets
  and auto-closes the excess side when position sizes diverge (auto-deleveraging).
- **AssetControl** (`MainProcess/AssetControl/`) — polls futures account balances on both exchanges; when the
  balance skew exceeds `max_diff_rate` (from `_settings/<ini>/balance.json`), it spawns `Transfer/Transfer.py`
  as a subprocess to move USDT from the richer exchange to the poorer one.
- **Transfer** (`MainProcess/AssetControl/Transfer/Transfer.py`) — a standalone script (not a long-running
  process) invoked once per transfer. Routes funds swap→spot→withdraw→deposit→spot→swap between exchanges,
  since most exchanges don't support direct futures-to-futures transfers between different platforms. Retries
  each step with `Core.Tool.try_this` and writes the outcome for the caller to pick up.
- **Notification/Discord.py** — optional log relay that reads shared logs and posts to a Discord webhook.

## Cross-process communication

Processes don't talk to each other over RPC. They communicate through the filesystem, which is why the shared
`frbot_logs` Docker volume (mounted at both `/app/logs` and the legacy `/home/ubuntu/fr_bot/logs`) matters:

- `logs/transfer_done.txt` — legacy plain-text status flag (`WAIT`/`OK`/`ERROR` + amount) written by
  `AssetControl/Main.py` before spawning `Transfer.py`, and by `Transfer.py` on completion.
- `logs/transfer_status.json` — same information as structured JSON, written atomically (write to `.tmp` then
  `os.replace`) so other containers/processes can read a consistent state.
- `logs/shared.log`, `logs/discord_simple.log`, `logs/<service>/syslog.log` — see Logging below.

## Configuration (`_settings/`)

Everything runtime-configurable lives outside the repo under `_settings/` (path resolution described below),
**not** in this codebase:

- `config.txt` — 3 lines: `exchange1`, `exchange2` (one of `binance|bitget|bitget_sub|gate`), and the name of
  the INI config subfolder (e.g. `1_bitget_gate_ini`) to use.
- `<ini>/balance.json` — `max_diff_rate` (percent) that triggers an asset transfer.
- `<ini>/transfer.json` — deposit addresses/chains/networks per exchange, used by `Transfer.py`.
- `<ini>/tp_sl.json`, `config.json` (Discord webhook) — as referenced by `Define.py`.
- `server.json` — list of `{name, host}` microservices the Server exposes/controls. `name` must be one of
  `adlcontrol` / `assetcontrol` / `discord` (case-insensitive) — see `MicroserviceManager.init_microservice`.

`Define.py` picks `root_path` based on OS: `C:\job\dim\fr_bot\` on Windows, `/home/ubuntu/fr_bot` elsewhere —
**this is not the git checkout directory**, it's a fixed deployment path. All `_settings` and log paths are
derived from `root_path`. Inside Docker images, the Dockerfiles copy the repo to
`/home/ubuntu/fr_bot/code` and symlink `/app/code` → it, so both the "new" and "legacy" paths resolve.

## Credentials — two different loaders (don't assume they're interchangeable)

- `Config.get_credentials()` (used by ADLControl and Transfer.py) reads AWS Secrets Manager secret
  `exchange_key` in region `ap-southeast-1`, expects a JSON blob keyed by exchange name, and hard-`sys.exit(1)`s
  if the secret can't be loaded (no local-file fallback).
- `Core/secret.py:get_secret()` (used by AssetControl/Main.py) reads a **different** secret,
  `bot1_exchange_key`, in region `ap-southeast-2`.

When touching credential loading, check which entrypoint you're editing — the two are not unified.

## Exchange access

- `fr_ccxt/_wrapper.py` (`CCXTWrapper`) is a thin synchronous wrapper around `ccxt` used for balance polling —
  it normalizes whatever shape `fetch_balance()`/`info` returns across exchanges into
  `{"balances": {"USDT": {"total": ..., "available": ...}}}`. Prefer extending its parsing helpers
  (`_parse_common_ccxt_balance`, `_parse_info_like_list`) over adding exchange-specific branches elsewhere.
- ADLControl and Transfer.py instantiate `ccxt`/`ccxt.pro` exchange clients directly (no shared factory) —
  `options['defaultType'] = 'swap'` is set manually on each.
- `Core/Define.py` defines the `EXCHANGE` enum and the only supported set: `BINANCE`, `BITGET`, `BITGET_SUB`,
  `GATE` (`BYBIT`/`OKX` exist in the enum but aren't wired up anywhere).

## Logging

`Core/Logger.py` provides `log_info/log_warning/log_error/log_debug(LogService, message, target=...)`. Each
service logger (`ASSET`, `ADL`, `TUNEL`, `TP_SL`, `SERVER`) fans out to up to three files depending on `target`:
`LogTarget.SHARED` → `shared.log`, `LogTarget.DISCORD` → `discord_simple.log` (INFO+ only, skipped entirely for
`TUNEL`), `LogTarget.SERVICE` → `logs/<service>/syslog.log`. Default target is `ALL` (goes to every handler).
Log directories are auto-created on first write, so an empty mounted volume is fine.

## Running things

There's no test/lint/build tooling configured beyond plain `unittest` — there's no pytest config, linter config,
or CI in this repo.

```bash
# Setup (Python 3.11)
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

# Run the FastAPI server locally (serves on 127.0.0.1:8000 via uvicorn)
python Server\App.py

# Run the test suite (unittest-based; only fr_ccxt has tests today)
python -m unittest discover -s tests
python -m unittest tests.test_fr_ccxt_wrapper -v   # single file
```

ADLControl and AssetControl (`MainProcess/*/Main.py`) are meant to run inside Docker, not directly — they
require `_settings` at `root_path` and live exchange credentials. Build/run them via:

```bash
docker build -f MainProcess\ADLControl\Dockerfile -t adlprocess .
docker build -f MainProcess\AssetControl\Dockerfile -t assetprocess .
```

Building/starting containers on a target host is normally done through the Server's
`PUT /bot1api/microservices/{id}/start` API rather than manual `docker create`, because that endpoint also
ensures the container has the correct `frbot_logs` volume mounts and recreates it if not (see
`Server/ServiceManager/MicroserviceManager.py`).

`install.sh` and `rebuild_docker.sh` are Ubuntu-only deployment scripts (systemd unit + Docker images) for a
real host at `/home/ubuntu/fr_bot`; they're not used for local development.

## Editing conventions specific to this repo

- Log/comments in this codebase are often written in Vietnamese; match the existing style when editing nearby
  code rather than converting everything to English.
- Modules that need `Define`/`Config`/`Core.*` add `sys.path.append(...)` at the top before importing them,
  since the worker scripts are executed directly (not as installed packages) and expect the repo root on
  `sys.path`. Follow this pattern for any new standalone entrypoint under `MainProcess/`.
