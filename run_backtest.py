from strategy import MidnightRangeStrategy
from data_fetcher import get_forex_data
import pandas as pd

def main():
    # Initialize strategy
    strategy = MidnightRangeStrategy()
    
    # Get data for testing
    print("Fetching data...")
    data = get_forex_data('GBPUSD', '2024-01-08', '2024-01-09')
    
    if data is None:
        print("Failed to get data")
        return
        
    print("Running backtest...")
    trades, metrics = strategy.run_backtest(data)
    
    print("\nBacktest Results:")
    print(f"Total Trades: {metrics['total_trades']}")
    print(f"Win Rate: {metrics['win_rate']:.2f}%")
    print(f"Total PnL: {metrics['total_pnl']:.5f}")
    print(f"Average Win: {metrics['avg_win']:.5f}")
    print(f"Average Loss: {metrics['avg_loss']:.5f}")
    
    if len(trades) > 0:
        print("\nTrade Details:")
        print(trades[['time', 'price', 'direction', 'exit_time', 'exit_price', 'pnl']].head())

if __name__ == "__main__":
    main()