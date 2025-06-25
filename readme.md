project/
│
├── config.yaml
├── exchange_api.py
├── funding_tracker.py
└── main.py# Funding & Position Tracker

A Python project to track funding fees and current positions across multiple exchanges, updating every minute. API configurations are managed via a config file.

## Project Structure## Features

- Track funding rates and open positions on multiple exchanges
- Configurable API keys and endpoints via `config.yaml`
- Automatic updates every minute

## Requirements

- Python 3.8+
- `requests`
- `PyYAML`
- `schedule`

Install dependencies:## Usage

1. Configure your API keys and exchange info in `config.yaml`.
2. Run the main script:## License

MIT License