

# Stock Breakout Detection and Backtesting System

A comprehensive Python application for detecting stock breakouts and backtesting trading strategies using Angel One's SmartAPI. The system identifies stocks with recent breakouts based on technical indicators and provides backtesting capabilities with various exit strategies.

## Features

- **Automated Stock Screening**: Filters stocks by market cap (>5000 crores)
- **Breakout Detection**: Identifies stocks breaking above 50-day highs with volume confirmation
- **Technical Analysis**: Uses RSI, SMA, and volume indicators for signal validation
- **Backtesting Engine**: Tests strategies with multiple exit conditions
- **Visual Charts**: Generates candlestick charts for breakout stocks
- **Multiple Exit Strategies**: Fixed holding period, stop-loss/take-profit, and trailing stop-loss


## Prerequisites

- Python 3.7+
- Angel One trading account with API access
- Required Python packages (see requirements below)


## Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd stock-breakout-system
```

2. **Install required packages**:
```bash
pip install pandas smartapi-python pyotp logzero talib plotly yfinance python-dotenv
```

3. **Set up environment variables**:
Create a `.env` file in the project root:
```
API_KEY=your_angel_one_api_key
BROKER_ID=your_broker_id
MPIN=your_mpin
TOTP_TOKEN=your_totp_secret
```

4. **Download required data files**:

- `OpenAPIScripMaster.json` - Angel One scrip master file
- `company_list.json` - Pre-filtered company list (optional)


## Usage

### Basic Execution

```bash
python breakout_v2.py
```


### Key Components

#### **SmartApiConnection Class**

Handles authentication and connection to Angel One's SmartAPI:

```python
conn = SmartApiConnection(
    api_key=os.getenv('API_KEY'),
    username=os.getenv('BROKER_ID'),
    mpin=os.getenv('MPIN'),
    totp_token=os.getenv('TOTP_TOKEN')
)
```


#### **StockDataManager Class**

Main class for data management and analysis:

- `load_company_list()`: Filters stocks by market cap
- `download_historical_data()`: Fetches OHLCV data
- `find_recent_breakouts()`: Identifies breakout candidates
- `backtest_breakout_strategy()`: Tests trading strategies


### Breakout Criteria

The system identifies breakouts based on:

- **Price Action**: Close > 50-day high
- **Volume Confirmation**: Volume ≥ 2x average 50-day volume
- **Trend Filter**: Close > 200-day SMA
- **Momentum Filter**: RSI > 60


### Backtesting Strategies

#### **1. Fixed Holding Period**

```python
results = stock_mgr.backtest_breakout_strategy(
    holding_period=10,
    stop_loss_pct=-0.05,
    take_profit_pct=0.15
)
```


#### **2. Trailing Stop-Loss**

```python
results = stock_mgr.backtest_breakout_with_trailing_sl(
    trailing_sl_pct=0.05
)
```


## Configuration

### **Breakout Parameters**

- `days`: Number of recent days to check for breakouts (default: 3)
- `threshold`: Minimum price movement threshold (default: 2%)
- `window`: Rolling window for technical indicators (default: 50)


### **Backtesting Parameters**

- `holding_period`: Days to hold position (default: 10)
- `stop_loss_pct`: Stop-loss percentage (e.g., -0.05 for -5%)
- `take_profit_pct`: Take-profit percentage (e.g., 0.15 for +15%)
- `trailing_sl_pct`: Trailing stop-loss percentage (e.g., 0.05 for 5%)


## Output

### **Breakout Detection**

- List of stocks with recent breakouts
- Candlestick charts saved in `breakout_v2/` folder
- Console output with breakout details


### **Backtesting Results**

- Trade-by-trade results with entry/exit dates and prices
- Average return percentage
- Total cumulative returns
- Performance metrics


## File Structure

```
project/
├── breakout_v2.py                    # Main application file
├── .env                      # Environment variables
├── .gitignore               # Git ignore file
├── README.md                # This file
├── OpenAPIScripMaster.json  # Angel One scrip master
├── company_list.json        # Pre-filtered company list
└── breakout_v2/             # Output folder for charts
    ├── STOCK1-EQ.png
    ├── STOCK2-EQ.png
    └── ...
```


## Security Notes

- Never commit your `.env` file to version control
- Keep your API credentials secure
- Use paper trading for initial testing


## Customization

### **Adding New Indicators**

Modify the `_detect_breakout()` method to include additional technical indicators:

```python
df['macd'] = talib.MACD(df['close'])[^0]
df['bollinger_upper'] = talib.BBANDS(df['close'])[^0]
```


### **Custom Exit Strategies**

Create new backtesting methods following the pattern of existing functions.

## Troubleshooting

### **Common Issues**

1. **Authentication Failed**: Check API credentials in `.env` file
2. **No Data Retrieved**: Verify internet connection and API limits
3. **Missing Dependencies**: Install all required packages
4. **TOTP Errors**: Ensure TOTP token is correctly configured

### **Debug Mode**

Enable verbose logging by modifying the logger configuration:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```


## Performance Considerations

- **Rate Limiting**: Built-in delays prevent API rate limit issues
- **Memory Usage**: Large datasets may require chunking for processing
- **Execution Time**: Full backtesting can take several minutes


## Disclaimer

This software is for educational and research purposes only. Trading involves substantial risk of loss. Past performance does not guarantee future results. Always conduct thorough testing before using any trading strategy with real money.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Support

For issues and questions:

1. Check the troubleshooting section
2. Review Angel One API documentation
3. Create an issue in the repository


