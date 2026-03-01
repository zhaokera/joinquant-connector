#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聚宽策略测试文件
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from strategies.value_investing_strategy import ValueInvestingStrategy
from utils.stock_analyzer import StockAnalyzer

class TestJoinQuantStrategy(unittest.TestCase):
    """聚宽策略测试"""
    
    def setUp(self):
        """测试前准备"""
        self.strategy = ValueInvestingStrategy()
        self.analyzer = StockAnalyzer()
    
    def test_strategy_initialization(self):
        """测试策略初始化"""
        self.assertIsNotNone(self.strategy)
        self.assertEqual(self.strategy.strategy_name, "邱国鹭李杰价值投资策略")
    
    def test_stock_analysis_integration(self):
        """测试股票分析集成"""
        # 测试股票池获取
        stock_pool = self.strategy.get_stock_pool()
        self.assertIsInstance(stock_pool, list)
        
        # 测试单个股票分析
        if stock_pool:
            test_stock = stock_pool[0]
            analysis = self.analyzer.analyze_stock(test_stock)
            self.assertIn('investment_grade', analysis)
            self.assertIn('value_score', analysis)
    
    def test_risk_management(self):
        """测试风险管理"""
        risk_params = self.strategy.get_risk_parameters()
        self.assertGreaterEqual(risk_params['max_position'], 0)
        self.assertLessEqual(risk_params['max_position'], 1.0)
        self.assertGreater(risk_params['stop_loss'], 0)
    
    def test_backtest_parameters(self):
        """测试回测参数"""
        backtest_config = self.strategy.get_backtest_config()
        self.assertIn('start_date', backtest_config)
        self.assertIn('end_date', backtest_config)
        self.assertIn('benchmark', backtest_config)

if __name__ == '__main__':
    unittest.main()