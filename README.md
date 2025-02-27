# TradingBot

TradingBot is a Python-based algorithmic trading tool that connects to a WebSocket server (e.g., MTS) to execute two-leg trading strategies based on spread data. It manages trading rules, logs orders and trades to JSON files, and offers a simple CLI menu for interaction.

## Features

- Real-time WebSocket connection for market data
- Automated buy/sell order execution based on spread rules
- Persistent storage of rules, orders, and trades in JSON
- Event logging to `data/logs/mtslog.json`
- CLI menu for viewing history and logs
- Multiprocessing for handling WebSocket and events

## Prerequisites

- Python 3.11+ (tested with 3.11)
- macOS (tested), Linux, or Windows (adjust `os.system` calls as needed)
- Access to a WebSocket server (default: `ws://192.168.173.244:1234`) or a mock server for testing

## Installation

1. **Clone the Repository** (if hosted, otherwise skip):
   ```bash
   git clone https://github.com/yourusername/tradingbot.git
   cd tradingbot
