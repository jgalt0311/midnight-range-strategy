from datetime import datetime, time, timedelta
import numpy as np
import pandas as pd
import pytz
from typing import Optional, Dict, List, Tuple

class MidnightRangeStrategy:
    def __init__(self, tick_size: float = 0.0001):
        self.tick_size = tick_size
        self.est_tz = pytz.timezone('US/Eastern')
        self.key_levels: Dict[str, float] = {}
        self.midnight_range_calculated = False
        self.current_position = None
        self.last_trade_time = None
        self.trades = []
        
    def calculate_midnight_range(self, data: pd.DataFrame) -> Optional[Dict[str, float]]:
        try:
            data_est = data.copy()
            data_est.index = pd.to_datetime(data_est.index).tz_convert(self.est_tz)
            
            midnight_data = data_est[
                (data_est.index.hour == 0) & 
                (data_est.index.minute < 30)
            ]
            
            if len(midnight_data) < 2:
                return None
                
            range_high = midnight_data['high'].max()
            range_low = midnight_data['low'].min()
            range_size = range_high - range_low
            
            self.key_levels = {
                'range_high': range_high,
                'range_low': range_low,
                'midpoint': range_low + (range_size / 2),
                'std_dev_up': range_high + range_size,
                'std_dev_down': range_low - range_size,
                'open': midnight_data['open'].iloc[0]
            }
            
            self.midnight_range_calculated = True
            return self.key_levels
            
        except Exception as e:
            print(f"Error calculating midnight range: {e}")
            return None

    def is_near_key_level(self, price: float, max_distance: int = 4) -> Tuple[bool, Optional[str]]:
        max_dist_price = max_distance * self.tick_size
        
        for level_name, level_price in self.key_levels.items():
            if abs(price - level_price) <= max_dist_price:
                return True, level_name
                
        return False, None

    def is_valid_time(self, current_time: datetime) -> bool:
        if isinstance(current_time, pd.Timestamp):
            current_time = current_time.to_pydatetime()
            
        est_time = current_time.astimezone(self.est_tz).time()
        return (est_time.hour == 3 and 25 <= est_time.minute <= 35)

    def process_bar(self, bar: pd.Series) -> Optional[Dict]:
        if not self.midnight_range_calculated:
            return None
            
        current_time = bar.name
        current_price = bar['close']
        
        # Check for valid trading time
        if not self.is_valid_time(current_time):
            return None
            
        # Check if price is near key level
        is_near, level_name = self.is_near_key_level(current_price)
        if not is_near:
            return None
            
        # Generate trade signal
        if current_price > self.key_levels['midpoint']:
            direction = 'SHORT'
            stop_loss = current_price + (10 * self.tick_size)
            target = self.key_levels['midpoint']
        else:
            direction = 'LONG'
            stop_loss = current_price - (10 * self.tick_size)
            target = self.key_levels['midpoint']
            
        return {
            'time': current_time,
            'price': current_price,
            'direction': direction,
            'stop_loss': stop_loss,
            'target': target,
            'level_name': level_name
        }

    def run_backtest(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        self.trades = []
        self.current_position = None
        
        if self.calculate_midnight_range(data) is None:
            return pd.DataFrame(), {}
            
        for idx, row in data.iterrows():
            # Update current position if exists
            if self.current_position:
                # Check for target or stop hit
                if self.current_position['direction'] == 'LONG':
                    if row['high'] >= self.current_position['target']:
                        self.trades.append({
                            **self.current_position,
                            'exit_time': idx,
                            'exit_price': self.current_position['target'],
                            'outcome': 'target',
                            'pnl': self.current_position['target'] - self.current_position['price']
                        })
                        self.current_position = None
                    elif row['low'] <= self.current_position['stop_loss']:
                        self.trades.append({
                            **self.current_position,
                            'exit_time': idx,
                            'exit_price': self.current_position['stop_loss'],
                            'outcome': 'stop',
                            'pnl': self.current_position['stop_loss'] - self.current_position['price']
                        })
                        self.current_position = None
                else:  # SHORT
                    if row['low'] <= self.current_position['target']:
                        self.trades.append({
                            **self.current_position,
                            'exit_time': idx,
                            'exit_price': self.current_position['target'],
                            'outcome': 'target',
                            'pnl': self.current_position['price'] - self.current_position['target']
                        })
                        self.current_position = None
                    elif row['high'] >= self.current_position['stop_loss']:
                        self.trades.append({
                            **self.current_position,
                            'exit_time': idx,
                            'exit_price': self.current_position['stop_loss'],
                            'outcome': 'stop',
                            'pnl': self.current_position['price'] - self.current_position['stop_loss']
                        })
                        self.current_position = None
            
            # Look for new signals if no position
            if not self.current_position:
                signal = self.process_bar(pd.Series(row))
                if signal:
                    self.current_position = signal
        
        # Calculate metrics
        if self.trades:
            trades_df = pd.DataFrame(self.trades)
            metrics = {
                'total_trades': len(self.trades),
                'winning_trades': len(trades_df[trades_df['pnl'] > 0]),
                'total_pnl': trades_df['pnl'].sum(),
                'win_rate': len(trades_df[trades_df['pnl'] > 0]) / len(self.trades) * 100,
                'avg_win': trades_df[trades_df['pnl'] > 0]['pnl'].mean() if len(trades_df[trades_df['pnl'] > 0]) > 0 else 0,
                'avg_loss': trades_df[trades_df['pnl'] <= 0]['pnl'].mean() if len(trades_df[trades_df['pnl'] <= 0]) > 0 else 0
            }
        else:
            trades_df = pd.DataFrame()
            metrics = {
                'total_trades': 0,
                'winning_trades': 0,
                'total_pnl': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0
            }
            
        return trades_df, metrics