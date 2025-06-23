
import pandas as pd
from SmartApi import SmartConnect
import pyotp
from logzero import logger
from datetime import datetime, timedelta
import time
import talib
import plotly.graph_objects as go
import os
from dotenv import load_dotenv
import yfinance as yf
import json

load_dotenv();

folder_path="breakout_v2"

if not os.path.exists(folder_path):
    os.mkdir(folder_path)


def load_company_list_from_file(filename='company_list.json'):
    import os
    if not os.path.exists(filename):
        print(f"File {filename} does not exist.")
        return []
    with open(filename, 'r') as f:
        company_list = json.load(f)
    print(f"Loaded {len(company_list)} companies from {filename}")
    return company_list


class SmartApiConnection:
    def __init__(self, api_key, username, mpin, totp_token):
        self.api_key = api_key
        self.username = username
        self.mpin = mpin
        self.totp_token = totp_token
        self.smartApi = SmartConnect(api_key)
        self.authToken = None
        self.refreshToken = None
        self.feedToken = None

    def authenticate(self):
        try:
            totp = pyotp.TOTP(self.totp_token).now()
        except Exception as e:
            logger.error("Invalid TOTP Token.")
            raise e

        data = self.smartApi.generateSession(self.username, self.mpin, totp)
        if not data['status']:
            logger.error(data)
            return False
        self.authToken = data['data']['jwtToken']
        self.refreshToken = data['data']['refreshToken']
        self.feedToken = self.smartApi.getfeedToken()
        self.smartApi.generateToken(self.refreshToken)
        return True

    def get_smartapi(self):
        return self.smartApi
    
class StockDataManager:
    def __init__(self, smartapi_connection, scrip_master_file, nifty_list_file):
        self.smartApi = smartapi_connection.get_smartapi()
        self.scrip_master_file = scrip_master_file
        self.nifty_list_file = nifty_list_file
        self.scrip_master = None
        self.company_list = []

    def load_scrip_master(self):
        self.scrip_master = pd.read_json(self.scrip_master_file)

    def load_company_list(self):
        with open(self.scrip_master_file, 'r') as f:
            data = json.load(f)
        
        symbols = [
            item['symbol'].replace('-EQ', '') + '.NS'
            for item in data
            if '-EQ' in item.get('symbol', '')  # Verify JSON has 'symbol' key
            ]
    
        for idx, sym in enumerate(symbols):
            try:
                # Use .info instead of .fast_info for reliability
                info = yf.Ticker(sym).info
                market_cap = info.get('marketCap')  # Correct key name (capital C)
                
                # 5000 crore = 5,000,000,000 = 5e9 (not 5e10)
                if market_cap and market_cap > 5e9:
                    symbol_eq = sym.replace('.NS', '-EQ')
                    self.company_list.append(symbol_eq)
                    logger.info(f"{symbol_eq} has market cap: {market_cap}")
            except Exception as e:
                print(f"Failed {sym}: {str(e)}")
            
            # Rate limiting
            if idx < len(symbols) - 1:
                time.sleep(1) 

        

    def download_historical_data(self, company_list, from_date, to_date):
        all_historical_data = {}
        for company_name in company_list:
            try:
                company_data = self.scrip_master[self.scrip_master['symbol'].str.contains(company_name, case=False, na=False)]
                if not company_data.empty:
                    symbol_token = str(company_data.iloc[0]['token'])
                    print(f"token: {symbol_token}\n")
                    historicParam = {
                        "exchange": "NSE",
                        "symboltoken": symbol_token,
                        "interval": "ONE_DAY",
                        "fromdate": from_date,
                        "todate": to_date
                    }
                    time.sleep(0.5)
                    historic_data = self.smartApi.getCandleData(historicParam)
                    if historic_data['status']:
                        all_historical_data[company_name] = historic_data['data']
                        print(f"Successfully downloaded data for {company_name}")
                    else:
                        print(f"Failed to download data for {company_name}: {historic_data['message']}")
                else:
                    print(f"Token not found for {company_name}")
            except Exception as e:
                print(f"Error downloading data for {company_name}: {str(e)}")
        return all_historical_data 
    
    @staticmethod
    def convert_to_dataframe(historical_data):
        ohlc_data = {}
        for company, data in historical_data.items():
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            ohlc_data[company] = df
        return ohlc_data
    
    #---------------------------NEW CODE----------------------------
    
    def find_recent_breakouts(self, days=3, threshold=0.02):
        """Detect companies with recent or imminent breakouts"""
        if not self.historical_data:
            raise ValueError("Download historical data first using download_historical_data()")
            
        breakout_companies = []
        
        for company, df in self.historical_data.items():
            try:
                processed_df = self._process_dataframe(df)
                if self._detect_breakout(processed_df, days, threshold):
                    breakout_companies.append(company.split('-')[0])  # Remove '-EQ' suffix
                    self.show_candlestick_chart(df,company)
            except Exception as e:
                print(f"Error processing {company}: {str(e)}")
                continue
                
        return breakout_companies

    def _process_dataframe(self, df):
        """Clean and format the dataframe"""
        df = df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        df = df.sort_values('timestamp')
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
        return df.dropna()

    def _detect_breakout(self, df, days=3, threshold=0.02):  # Changed threshold to 2%
        """Stricter breakout detection for bigger moves"""
        
    
        # Add these new indicators:
        window = 50
        df['50_day_high'] = df['high'].rolling(window).max()
        df['200_sma'] = df['close'].rolling(200).mean()
        df['avg_volume_50'] = df['volume'].rolling(window).mean()
        df['rsi'] = talib.RSI(df['close'], timeperiod=14)
        
     
        # Modified bullish breakout conditions
        df['bullish_breakout'] = (
            (df['close'] > df['50_day_high'].shift(1)) &
            (df['volume'] >= 2 * df['avg_volume_50']) &  # Changed to 2x volume
            (df['close'] > df['200_sma']) &  # Added trend filter
            (df['rsi'] > 60)   # Added momentum filter
        )
        
        
        
        recent_data = df.tail(days)
        return recent_data['bullish_breakout'].any()  # Removed near_breakout check
    
    def show_candlestick_chart(self,df,company):
        df_plot=df.tail(200)
        #print(df_plot[['timestamp', 'open', 'high', 'low', 'close']])

        fig = go.Figure(data=[go.Candlestick(x=df_plot['timestamp'],
                open=df_plot['open'],
                high=df_plot['high'],
                low=df_plot['low'],
                close=df_plot['close'])])
        fig.update_layout(
            title={
                'text': f'{company}',
                'y':0.9,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top'
            },
            xaxis_rangeslider_visible=False,
            width=1200,  # Wider image for better clarity
            height=600,
            xaxis_title='Date',
            yaxis_title='Price'
        )
        fig.write_image(f"{folder_path}/{company}.png", width=1600, height=800, scale=2)
        #fig.show()
    
    
    #--------backtesting function---------------------------------------
    
    def backtest_breakout_strategy(self, holding_period=10, stop_loss_pct=None, take_profit_pct=None):
        """
        Backtest the breakout strategy for all companies in self.historical_data.
        - holding_period: days to hold after breakout (if no SL/TP hit)
        - stop_loss_pct: stop loss as negative percent (e.g. -0.05 for -5%)
        - take_profit_pct: take profit as positive percent (e.g. 0.10 for +10%)
        Returns a list of trade records.
        """
        results = []
    
        for company, df in self.historical_data.items():
            df = self._process_dataframe(df)
            # Identify breakout points using your existing logic
            df['breakout'] = self._detect_breakout_signals(df)
            for idx, row in df[df['breakout']].iterrows():
                entry_idx = idx
                entry_date = row['timestamp']
                entry_price = row['close']
    
                exit_idx = min(entry_idx + holding_period, len(df) - 1)
                exit_price = df.iloc[exit_idx]['close']
                exit_date = df.iloc[exit_idx]['timestamp']
    
                # Check for stop loss / take profit within holding period
                if stop_loss_pct or take_profit_pct:
                    for i in range(entry_idx + 1, exit_idx + 1):
                        price = df.iloc[i]['close']
                        change = (price - entry_price) / entry_price
                        if take_profit_pct and change >= take_profit_pct:
                            exit_price = price
                            exit_date = df.iloc[i]['timestamp']
                            break
                        if stop_loss_pct and change <= stop_loss_pct:
                            exit_price = price
                            exit_date = df.iloc[i]['timestamp']
                            break
    
                result = {
                    'company': company,
                    'entry_date': entry_date,
                    'entry_price': entry_price,
                    'exit_date': exit_date,
                    'exit_price': exit_price,
                    'return_pct': (exit_price - entry_price) / entry_price * 100
                }
                results.append(result)
        return results
    
    def backtest_breakout_with_trailing_sl(self, trailing_sl_pct=0.05):
        """
        Backtest breakout strategy with a trailing stop-loss.
        trailing_sl_pct: e.g., 0.05 for 5% trailing stop.
        Returns a list of trade records.
        """
        results = []
    
        for company, df in self.historical_data.items():
            df = self._process_dataframe(df)
            # Identify breakout points
            df['breakout'] = self._detect_breakout_signals(df)
            in_trade = False
            entry_idx = None
            entry_price = None
            highest_close = None
    
            for idx, row in df.iterrows():
                if not in_trade and row['breakout']:
                    # Enter trade
                    in_trade = True
                    entry_idx = idx
                    entry_price = row['close']
                    entry_date = row['timestamp']
                    highest_close = entry_price
                elif in_trade:
                    # Update highest close
                    if row['close'] > highest_close:
                        highest_close = row['close']
                    # Check trailing stop
                    if row['close'] <= highest_close * (1 - trailing_sl_pct):
                        exit_price = row['close']
                        exit_date = row['timestamp']
                        results.append({
                            'company': company,
                            'entry_date': entry_date,
                            'entry_price': entry_price,
                            'exit_date': exit_date,
                            'exit_price': exit_price,
                            'return_pct': (exit_price - entry_price) / entry_price * 100
                        })
                        in_trade = False
                        entry_idx = None
                        entry_price = None
                        highest_close = None
            # If trade open at end, close at last available price
            if in_trade:
                exit_price = df.iloc[-1]['close']
                exit_date = df.iloc[-1]['timestamp']
                results.append({
                    'company': company,
                    'entry_date': entry_date,
                    'entry_price': entry_price,
                    'exit_date': exit_date,
                    'exit_price': exit_price,
                    'return_pct': (exit_price - entry_price) / entry_price * 100
                })
        return results

    def _detect_breakout_signals(self, df):
        """
        Returns a boolean Series: True if that row is a breakout candle as per your rules.
        """
        window = 50
        df['50_day_high'] = df['high'].rolling(window).max()
        df['200_sma'] = df['close'].rolling(200).mean()
        df['avg_volume_50'] = df['volume'].rolling(window).mean()
        df['rsi'] = talib.RSI(df['close'], timeperiod=14)
        # Your breakout logic
        breakout = (
            (df['close'] > df['50_day_high'].shift(1)) &
            (df['volume'] >= 2 * df['avg_volume_50']) &
            (df['close'] > df['200_sma']) &
            (df['rsi'] > 60)
        )
        return breakout

if __name__ == "__main__":
    # Step 1: Create and authenticate the SmartAPI connection
    conn = SmartApiConnection(
       api_key=os.getenv('API_KEY'),
       username=os.getenv('BROKER_ID'),
       mpin=os.getenv('MPIN'),
       totp_token=os.getenv('TOTP_TOKEN')
    )
    
    if conn.authenticate():
        stock_mgr = StockDataManager(
            smartapi_connection=conn,
            scrip_master_file='OpenAPIScripMaster.json',
            nifty_list_file='ind_nifty500list.csv'
        )
        
        stock_mgr.load_scrip_master()
        #stock_mgr.load_company_list()
        
        #company_list = stock_mgr.company_list
        company_list = load_company_list_from_file()
        company_list=company_list
        
        
    to_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    from_date = (datetime.now() - timedelta(days=600)).strftime("%Y-%m-%d %H:%M")
    
    # Download historical data
    stock_mgr.historical_data = stock_mgr.download_historical_data(
        company_list=company_list,  
        from_date=from_date,
        to_date=to_date
    )

    stock_mgr.historical_data=stock_mgr.convert_to_dataframe(stock_mgr.historical_data) 
    breakout_stocks = stock_mgr.find_recent_breakouts()
    print("\nStocks with recent breakouts or near breakout levels:")
    print(breakout_stocks)


results = stock_mgr.backtest_breakout_strategy(holding_period=10, stop_loss_pct=-0.05, take_profit_pct=0.15)
df_results = pd.DataFrame(results)
print(df_results[['company', 'entry_date', 'entry_price', 'exit_date', 'exit_price', 'return_pct']])
print("Average return: {:.2f}%".format(df_results['return_pct'].mean()))

results = stock_mgr.backtest_breakout_with_trailing_sl(trailing_sl_pct=0.05)
df_results = pd.DataFrame(results)
print("Average return: {:.2f}%".format(df_results['return_pct'].mean()))
total_return = df_results['return_pct'].sum()
print(f"Total sum of returns: {total_return:.2f}%")







        