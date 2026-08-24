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

- `config.txt` — 3 lines: `exchange1`, `exchange2` (one of `binance|bitget|gate`), and the name of
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

## Credentials — single unified loader

All three processes (ADLControl, AssetControl, Transfer.py) load credentials the same way:
`Config.get_credentials(exchange1, exchange2)` first tries AWS Secrets Manager secret `exchange_key` in region
`ap-southeast-1` (JSON blob keyed by exchange name); if that call fails (no AWS credentials, no network, etc.)
it falls back to a local JSON file with the same shape at `<root_path>/code/_settings/exchange_key.json`
(`Config.LOCAL_KEY_FILE`); if neither source yields data it hard-`sys.exit(1)`s. There used to be a second,
separate loader (`Core/secret.py`, secret `bot1_exchange_key` in `ap-southeast-2`) used only by AssetControl —
it has been removed; AssetControl now calls `Config.get_credentials()` like everything else.

Use `Tools/manage_keys.py` to view (masked) or update keys instead of hand-editing JSON — it does a
read-modify-write against the single exchange's block so other exchanges' credentials aren't touched. By
default it targets the AWS secret; pass `--local` to read/write `exchange_key.json` instead (handy for local
dev without AWS credentials). Credentials are only read once at process startup, so a key update requires
restarting the affected container(s) (`adlcontrol_container`, `assetcontrol_container`) to take effect —
`manage_keys.py set` prints this reminder, and `--restart` will do it for you.

## Exchange access

- `fr_ccxt/_wrapper.py` (`CCXTWrapper`) is a thin synchronous wrapper around `ccxt` used for balance polling —
  it normalizes whatever shape `fetch_balance()`/`info` returns across exchanges into
  `{"balances": {"USDT": {"total": ..., "available": ...}}}`. Prefer extending its parsing helpers
  (`_parse_common_ccxt_balance`, `_parse_info_like_list`) over adding exchange-specific branches elsewhere.
- ADLControl and Transfer.py instantiate `ccxt`/`ccxt.pro` exchange clients directly (no shared factory) —
  `options['defaultType'] = 'swap'` is set manually on each.
- `Core/Define.py` defines the `EXCHANGE` enum and the only supported set: `BINANCE`, `BITGET`, `GATE`
  (`BYBIT`/`OKX` exist in the enum but aren't wired up anywhere).

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

**Testing without real credentials/API calls**: set `DRY_RUN=1` before running `MainProcess/AssetControl/Main.py`
to swap in `Core/FakeExchange.py` instead of real ccxt clients — `Config.get_credentials()` is skipped entirely,
so no AWS/local `exchange_key.json` is needed. Seed each side's simulated USDT balance via
`DRY_RUN_BALANCE_<EXCHANGE1_NAME>` / `DRY_RUN_BALANCE_<EXCHANGE2_NAME>` (uppercase, default `1000`) to exercise
the balance-skew/transfer-decision logic in `AssetProcess.tick()`. In `DRY_RUN`, a triggered transfer is only
logged (`"[DRY_RUN] Would transfer ..."`) — `Transfer/Transfer.py` is never spawned and no state file is
written. `ADLControl` has no dry-run mode (its position-fetching logic is hardwired to Bitget's/Gate's live API
shapes) and `Transfer.py` itself isn't dry-run-capable yet (its ccxt clients are built as module-level globals).
Also see `Tools/verify_setup.py` for a read-only check of real, already-configured credentials.

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
