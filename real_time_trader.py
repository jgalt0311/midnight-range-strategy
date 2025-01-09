import websocket
import json
import threading
from datetime import datetime
import pytz
from strategy import MidnightRangeStrategy
import os
from dotenv import load_dotenv
import pandas as pd

class RealTimeTrader:
    def __init__(self):
        load_dotenv()  # Load API key from .env file
        self.api_key = os.getenv('TRADERMADE_API_KEY')
        self.strategy = MidnightRangeStrategy()
        self.current_data = []
        self.est_tz = pytz.timezone('US/Eastern')
        self.ws = None
        self.is_connected = False
        self.current_position = None
        
    def on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            
            if 'data' in data:
                # Process tick data
                tick = data['data']
                timestamp = datetime.fromtimestamp(tick['t']/1000, tz=pytz.UTC)
                est_time = timestamp.astimezone(self.est_tz)
                
                # Add to current minute's data
                self.current_data.append({
                    'timestamp': timestamp,
                    'price': float(tick['p']),
                    'bid': float(tick.get('b', tick['p'])),
                    'ask': float(tick.get('a', tick['p']))
                })
                
                # Process data when we have enough for a new 1-minute candle
                self._process_minute_data(est_time)
                
        except Exception as e:
            print(f"Error processing message: {e}")
            
    def _process_minute_data(self, current_time):
        """Process accumulated tick data into 1-minute candles"""
        if not self.current_data:
            return
            
        # Only process when we have a new minute
        if len(self.current_data) > 1:
            first_tick = self.current_data[0]
            last_tick = self.current_data[-1]
            
            if first_tick['timestamp'].minute != last_tick['timestamp'].minute:
                # Create OHLC data
                prices = [tick['price'] for tick in self.current_data]
                candle = pd.Series({
                    'open': prices[0],
                    'high': max(prices),
                    'low': min(prices),
                    'close': prices[-1],
                    'timestamp': first_tick['timestamp']
                })
                
                # Check for trading opportunities
                self._check_trading_signals(candle)
                
                # Clear current data, keeping the last tick for next candle
                self.current_data = [self.current_data[-1]]
                
    def _check_trading_signals(self, candle):
        """Check for trading signals based on strategy"""
        # Initialize midnight range if needed
        if not self.strategy.midnight_range_calculated:
            # You would need historical data here
            # For now, we'll skip until we have enough data
            return
            
        # Check for trading opportunities
        signal = self.strategy.process_bar(candle)
        if signal and not self.current_position:
            self._execute_trade(signal)
            
    def _execute_trade(self, signal):
        """Execute a trade based on the signal"""
        print(f"\nExecuting trade:")
        print(f"Time: {signal['time']}")
        print(f"Direction: {signal['direction']}")
        print(f"Entry Price: {signal['price']}")
        print(f"Stop Loss: {signal['stop_loss']}")
        print(f"Target: {signal['target']}")
        
        # Here you would integrate with your broker's API
        self.current_position = signal
        
    def on_error(self, ws, error):
        """Handle WebSocket errors"""
        print(f"Error: {error}")
        
    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close"""
        print("WebSocket connection closed")
        self.is_connected = False
        
    def on_open(self, ws):
        """Handle WebSocket connection open"""
        print("WebSocket connection opened")
        self.is_connected = True
        
        # Subscribe to GBPUSD stream
        subscribe_message = {
            "userKey": self.api_key,
            "symbol": "GBPUSD"
        }
        ws.send(json.dumps(subscribe_message))
        
    def start(self):
        """Start the real-time trading system"""
        websocket.enableTrace(True)
        self.ws = websocket.WebSocketApp(
            "wss://marketdata.tradermade.com/feedadv",
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
        
        # Run WebSocket connection in a separate thread
        wst = threading.Thread(target=self.ws.run_forever)
        wst.daemon = True
        wst.start()
        
    def stop(self):
        """Stop the real-time trading system"""
        if self.ws:
            self.ws.close()
            
if __name__ == "__main__":
    trader = RealTimeTrader()
    trader.start()
    
    try:
        # Keep the main thread running
        while True:
            cmd = input("Enter 'q' to quit: ")
            if cmd.lower() == 'q':
                break
    except KeyboardInterrupt:
        print("\nStopping trader...")
    finally:
        trader.stop()