#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聚宽模拟交易模块 - 基于邱国鹭《投资中最简单的事》和李杰《股市进阶之道》
提供与聚宽平台的模拟交易对接功能
"""

import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.stock_analyzer import StockAnalyzer
from strategies.value_investing_strategy import ValueInvestingStrategy

class SimulatedTrading:
    """聚宽模拟交易接口"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or "config/jq_config.json"
        self.config = self._load_config()
        self.analyzer = StockAnalyzer()
        self.strategy = ValueInvestingStrategy()
        
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # 默认配置
            return {
                "initial_capital": 1000000,
                "commission_rate": 0.0003,
                "stamp_duty_rate": 0.001,
                "slippage": 0.0001,
                "risk_per_trade": 0.02,
                "max_position_size": 0.2,
                "stop_loss_pct": 0.08,
                "take_profit_pct": 0.20
            }
    
    def generate_trading_signals(self, stock_list: List[str] = None) -> Dict[str, Any]:
        """
        生成交易信号
        
        Args:
            stock_list: 股票列表，如果为None则使用策略默认选股
            
        Returns:
            交易信号字典
        """
        if stock_list is None:
            # 使用价值投资策略选股
            stock_list = self.strategy.select_stocks()
        
        signals = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "buy_signals": [],
            "sell_signals": [],
            "hold_signals": [],
            "strategy_info": {
                "name": "Value Investing Strategy",
                "framework": "邱国鹭四要素 + 李杰能力圈理论",
                "version": "1.0.0"
            }
        }
        
        for symbol in stock_list:
            try:
                # 获取股票分析结果
                analysis = self.analyzer.analyze_stock(symbol)
                
                # 基于邱国鹭四要素生成信号
                signal = self._generate_signal_from_analysis(analysis)
                
                if signal["action"] == "buy":
                    signals["buy_signals"].append({
                        "symbol": symbol,
                        "price": signal.get("price", 0),
                        "quantity": signal.get("quantity", 0),
                        "reason": signal.get("reason", ""),
                        "investment_grade": analysis.get("investment_grade", "medium"),
                        "value_score": analysis.get("value_score", 50)
                    })
                elif signal["action"] == "sell":
                    signals["sell_signals"].append({
                        "symbol": symbol,
                        "price": signal.get("price", 0),
                        "reason": signal.get("reason", ""),
                        "investment_grade": analysis.get("investment_grade", "low"),
                        "value_score": analysis.get("value_score", 30)
                    })
                else:
                    signals["hold_signals"].append({
                        "symbol": symbol,
                        "investment_grade": analysis.get("investment_grade", "medium"),
                        "value_score": analysis.get("value_score", 50)
                    })
                    
            except Exception as e:
                print(f"Error analyzing {symbol}: {e}")
                continue
        
        return signals
    
    def _generate_signal_from_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        基于股票分析结果生成交易信号
        
        Args:
            analysis: 股票分析结果
            
        Returns:
            交易信号
        """
        value_score = analysis.get("value_score", 50)
        investment_grade = analysis.get("investment_grade", "medium")
        current_price = analysis.get("current_price", 0)
        
        # 邱国鹭四要素决策逻辑
        if value_score >= 80 and investment_grade == "high":
            # 高价值、高评分 - 买入
            quantity = self._calculate_position_size(current_price)
            return {
                "action": "buy",
                "price": current_price,
                "quantity": quantity,
                "reason": "高价值投资机会，符合邱国鹭四要素标准"
            }
        elif value_score <= 40 and investment_grade == "low":
            # 低价值、低评分 - 卖出
            return {
                "action": "sell",
                "price": current_price,
                "reason": "投资价值低，不符合价值投资原则"
            }
        else:
            # 持有或观望
            return {
                "action": "hold",
                "price": current_price,
                "reason": "投资价值中等，继续持有观察"
            }
    
    def _calculate_position_size(self, price: float) -> int:
        """
        计算仓位大小
        
        Args:
            price: 股票价格
            
        Returns:
            股票数量
        """
        risk_amount = self.config["initial_capital"] * self.config["risk_per_trade"]
        max_position_value = self.config["initial_capital"] * self.config["max_position_size"]
        
        # 基于风险计算数量
        risk_quantity = int(risk_amount / (price * self.config["stop_loss_pct"]))
        max_quantity = int(max_position_value / price)
        
        return min(risk_quantity, max_quantity, 1000)  # 限制最大1000股
    
    def format_for_jq_platform(self, signals: Dict[str, Any]) -> str:
        """
        格式化为聚宽平台兼容的格式
        
        Args:
            signals: 交易信号
            
        Returns:
            聚宽策略代码字符串
        """
        jq_code = f'''
# 聚宽量化策略 - 基于价值投资理念
# 生成时间: {signals["timestamp"]}
# 策略框架: 邱国鹭四要素 + 李杰能力圈理论

def initialize(context):
    """初始化策略"""
    # 设置参数
    g.capital = {self.config["initial_capital"]}
    g.commission = {self.config["commission_rate"]}
    g.stamp_duty = {self.config["stamp_duty_rate"]}
    g.slippage = {self.config["slippage"]}
    g.stop_loss = {self.config["stop_loss_pct"]}
    g.take_profit = {self.config["take_profit_pct"]}
    
    # 交易标的
    g.buy_stocks = {[signal["symbol"] for signal in signals["buy_signals"]]}
    g.sell_stocks = {[signal["symbol"] for signal in signals["sell_signals"]]}
    
    # 设置定时运行
    run_daily(trade, time='09:30')

def trade(context):
    """交易逻辑"""
    # 卖出信号
    for stock in g.sell_stocks:
        if stock in context.portfolio.positions:
            order_target(stock, 0)
            log.info(f"卖出 {{stock}} - 投资价值低")
    
    # 买入信号
    available_cash = context.portfolio.available_cash
    buy_count = len(g.buy_stocks)
    
    if buy_count > 0:
        cash_per_stock = available_cash / buy_count
        
        for stock in g.buy_stocks:
            if stock not in context.portfolio.positions:
                # 计算买入数量
                current_price = get_price(stock, count=1, end_date=context.current_dt)[0]
                quantity = int(cash_per_stock / current_price)
                
                if quantity > 0:
                    order(stock, quantity)
                    log.info(f"买入 {{stock}} - 数量: {{quantity}}, 价格: {{current_price:.2f}}")

def handle_data(context, data):
    """处理实时数据"""
    pass

def after_trading_end(context):
    """收盘后处理"""
    log.info(f"当日持仓: {{list(context.portfolio.positions.keys())}}")
    log.info(f"可用资金: {{context.portfolio.available_cash:.2f}}")
    log.info(f"总资产: {{context.portfolio.total_value:.2f}}")
'''
        return jq_code
    
    def save_signals_to_file(self, signals: Dict[str, Any], filename: str = None):
        """
        保存交易信号到文件
        
        Args:
            signals: 交易信号
            filename: 文件名
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"trading_signals_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(signals, f, ensure_ascii=False, indent=2)
        
        print(f"交易信号已保存到: {filename}")
    
    def save_jq_strategy_to_file(self, signals: Dict[str, Any], filename: str = None):
        """
        保存聚宽策略代码到文件
        
        Args:
            signals: 交易信号
            filename: 文件名
        """
        jq_code = self.format_for_jq_platform(signals)
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"jq_strategy_{timestamp}.py"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(jq_code)
        
        print(f"聚宽策略已保存到: {filename}")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python simulated_trading.py <action> [参数...]")
        print("支持的操作:")
        print("  generate_signals [股票代码列表]  # 生成交易信号")
        print("  create_jq_strategy [股票代码列表]  # 创建聚宽策略")
        return
    
    action = sys.argv[1]
    trading = SimulatedTrading()
    
    if action == "generate_signals":
        stock_list = sys.argv[2:] if len(sys.argv) > 2 else None
        signals = trading.generate_trading_signals(stock_list)
        print(json.dumps(signals, ensure_ascii=False, indent=2))
        trading.save_signals_to_file(signals)
        
    elif action == "create_jq_strategy":
        stock_list = sys.argv[2:] if len(sys.argv) > 2 else None
        signals = trading.generate_trading_signals(stock_list)
        jq_code = trading.format_for_jq_platform(signals)
        print(jq_code)
        trading.save_jq_strategy_to_file(signals)
        
    else:
        print(f"未知操作: {action}")

if __name__ == "__main__":
    main()