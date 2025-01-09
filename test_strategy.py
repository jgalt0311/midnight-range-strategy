import unittest
from strategy import MidnightRangeStrategy
from data_fetcher import get_forex_data
import pandas as pd
import pytz

class TestMidnightRangeStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = MidnightRangeStrategy()
        self.symbol = 'GBPUSD'
        
    def test_midnight_range_calculation(self):
        # Get test data
        data = get_forex_data(self.symbol, '2024-01-08', '2024-01-09')
        self.assertIsNotNone(data, "Failed to get test data")
        
        # Calculate midnight range
        levels = self.strategy.calculate_midnight_range(data)
        
        # Verify levels are calculated
        self.assertIsNotNone(levels, "Failed to calculate midnight range levels")
        self.assertTrue('range_high' in levels, "Missing range_high")
        self.assertTrue('range_low' in levels, "Missing range_low")
        self.assertTrue('midpoint' in levels, "Missing midpoint")
        
    def test_trade_generation(self):
        # Get test data
        data = get_forex_data(self.symbol, '2024-01-08', '2024-01-09')
        self.assertIsNotNone(data, "Failed to get test data")
        
        # Run backtest
        trades, metrics = self.strategy.run_backtest(data)
        
        # Verify trades are generated
        self.assertIsInstance(trades, pd.DataFrame, "Trades should be a DataFrame")
        self.assertIsInstance(metrics, dict, "Metrics should be a dictionary")
        
    def test_time_window_validation(self):
        # Test time validation
        test_time = datetime(2024, 1, 8, 3, 30, tzinfo=pytz.UTC)
        self.assertTrue(self.strategy.is_valid_time(test_time), "Should be valid trading time")
        
        test_time = datetime(2024, 1, 8, 4, 0, tzinfo=pytz.UTC)
        self.assertFalse(self.strategy.is_valid_time(test_time), "Should not be valid trading time")

if __name__ == '__main__':
    unittest.main()