from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.live import StockDataStream, CryptoDataStream
from config import ALPACA_API_KEY, ALPACA_SECRET_KEY, IS_PAPER

trading_client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=IS_PAPER)
stock_data_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
crypto_data_client = CryptoHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)

def get_account():
    return trading_client.get_account()

def get_positions():
    return trading_client.get_all_positions()

def get_orders():
    return trading_client.get_orders()

def get_buying_power():
    account = get_account()
    return float(account.buying_power)

def get_equity():
    account = get_account()
    return float(account.equity)
