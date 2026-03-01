#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聚宽量化交易连接器 - 主入口
基于邱国鹭《投资中最简单的事》和李杰《股市进阶之道》的投资理念
"""

import sys
import os
import json
import argparse
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategies.value_investing_strategy import ValueInvestingStrategy
from simulation.simulated_trading import SimulatedTradingSystem
from utils.stock_analyzer import StockAnalyzer

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='聚宽量化交易连接器')
    parser.add_argument('--action', type=str, required=True,
                       choices=['backtest', 'simulate', 'analyze', 'generate_signals'],
                       help='执行的操作类型')
    parser.add_argument('--start_date', type=str, help='回测开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end_date', type=str, help='回测结束日期 (YYYY-MM-DD)')
    parser.add_argument('--symbol', type=str, help='股票代码 (如: 600000.XSHG)')
    parser.add_argument('--initial_capital', type=float, default=1000000.0,
                       help='初始资金 (默认: 100万)')
    parser.add_argument('--strategy_config', type=str, 
                       default='config/jq_config.json',
                       help='策略配置文件路径')
    
    args = parser.parse_args()
    
    try:
        # 加载策略配置
        with open(args.strategy_config, 'r', encoding='utf-8') as f:
            strategy_config = json.load(f)
        
        if args.action == 'backtest':
            if not args.start_date or not args.end_date:
                raise ValueError("回测需要提供 start_date 和 end_date 参数")
            
            # 执行回测
            strategy = ValueInvestingStrategy(strategy_config)
            results = strategy.run_backtest(
                start_date=args.start_date,
                end_date=args.end_date,
                initial_capital=args.initial_capital
            )
            print(json.dumps(results, ensure_ascii=False, indent=2))
            
        elif args.action == 'simulate':
            # 启动模拟交易
            sim_system = SimulatedTradingSystem(strategy_config)
            results = sim_system.start_simulation(
                initial_capital=args.initial_capital
            )
            print(json.dumps(results, ensure_ascii=False, indent=2))
            
        elif args.action == 'analyze':
            if not args.symbol:
                raise ValueError("分析需要提供 symbol 参数")
            
            # 股票分析
            analyzer = StockAnalyzer()
            analysis = analyzer.analyze_stock(args.symbol)
            print(json.dumps(analysis, ensure_ascii=False, indent=2))
            
        elif args.action == 'generate_signals':
            # 生成交易信号
            strategy = ValueInvestingStrategy(strategy_config)
            signals = strategy.generate_trading_signals()
            print(json.dumps(signals, ensure_ascii=False, indent=2))
            
        else:
            raise ValueError(f"未知的操作类型: {args.action}")
            
    except Exception as e:
        error_result = {
            "error": str(e),
            "action": args.action,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        print(json.dumps(error_result, ensure_ascii=False, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    main()