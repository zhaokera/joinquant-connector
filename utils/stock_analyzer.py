#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票分析工具模块 - 基于邱国鹭《投资中最简单的事》和李杰《股市进阶之道》
为聚宽策略提供价值投资分析信号
"""

import json
import subprocess
import os
from typing import Dict, List, Any

class StockAnalyzer:
    """股票分析器 - 集成现有的OpenClaw股票分析技能"""
    
    def __init__(self, stock_analyzer_path: str = "/Users/zhaok/.openclaw/skills/openclaw-stock-analyzer"):
        self.stock_analyzer_path = stock_analyzer_path
        
    def get_value_investing_analysis(self, symbol: str) -> Dict[str, Any]:
        """
        获取价值投资分析结果
        基于邱国鹭四要素：估值、品质、时机、仓位
        """
        try:
            # 调用现有的股票分析技能
            cmd = [
                "python3", 
                f"{self.stock_analyzer_path}/main.py",
                "--action", "value_investing_analysis",
                "--symbol", symbol
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return {"error": f"分析失败: {result.stderr}"}
                
        except Exception as e:
            return {"error": f"异常: {str(e)}"}
    
    def get_technical_analysis(self, symbol: str, indicators: List[str] = None) -> Dict[str, Any]:
        """获取技术分析结果"""
        try:
            indicators = indicators or ["macd", "rsi", "kdj"]
            indicator_str = ",".join(indicators)
            
            cmd = [
                "python3",
                f"{self.stock_analyzer_path}/main.py",
                "--action", "technical_analysis",
                "--symbol", symbol,
                "--indicator", indicator_str
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return {"error": f"技术分析失败: {result.stderr}"}
                
        except Exception as e:
            return {"error": f"异常: {str(e)}"}
    
    def get_fundamental_analysis(self, symbol: str) -> Dict[str, Any]:
        """获取基本面分析结果"""
        try:
            cmd = [
                "python3",
                f"{self.stock_analyzer_path}/main.py",
                "--action", "fundamental_analysis",
                "--symbol", symbol
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return {"error": f"基本面分析失败: {result.stderr}"}
                
        except Exception as e:
            return {"error": f"异常: {str(e)}"}
    
    def generate_buy_signal(self, symbol: str) -> Dict[str, Any]:
        """
        生成买入信号
        综合价值投资分析、技术分析和基本面分析
        """
        # 获取价值投资分析
        value_analysis = self.get_value_investing_analysis(symbol)
        
        if "error" in value_analysis:
            return {"signal": "hold", "reason": value_analysis["error"]}
        
        # 获取技术分析
        tech_analysis = self.get_technical_analysis(symbol)
        
        if "error" in tech_analysis:
            return {"signal": "hold", "reason": tech_analysis["error"]}
        
        # 获取基本面分析
        fundamental_analysis = self.get_fundamental_analysis(symbol)
        
        if "error" in fundamental_analysis:
            return {"signal": "hold", "reason": fundamental_analysis["error"]}
        
        # 综合判断 - 基于邱国鹭四要素
        signal_score = 0
        reasons = []
        
        # 1. 估值要素 (30%权重)
        valuation_score = value_analysis.get("qiu_guolu_elements", {}).get("valuation_score", 0)
        if valuation_score >= 70:
            signal_score += 30
            reasons.append("估值合理，具备安全边际")
        elif valuation_score >= 50:
            signal_score += 15
            reasons.append("估值中等")
        else:
            reasons.append("估值偏高")
        
        # 2. 品质要素 (30%权重)  
        quality_score = value_analysis.get("qiu_guolu_elements", {}).get("quality_score", 0)
        if quality_score >= 70:
            signal_score += 30
            reasons.append("公司品质优秀，护城河稳固")
        elif quality_score >= 50:
            signal_score += 15
            reasons.append("公司品质良好")
        else:
            reasons.append("公司品质一般")
        
        # 3. 时机要素 (20%权重)
        timing_score = value_analysis.get("qiu_guolu_elements", {}).get("timing_score", 0)
        if timing_score >= 70:
            signal_score += 20
            reasons.append("时机合适，市场情绪积极")
        elif timing_score >= 50:
            signal_score += 10
            reasons.append("时机中等")
        else:
            reasons.append("时机不佳")
        
        # 4. 技术面确认 (20%权重)
        tech_signals = tech_analysis.get("signals", {})
        tech_positive = sum(1 for v in tech_signals.values() if v == "positive")
        tech_total = len(tech_signals)
        
        if tech_total > 0:
            tech_ratio = tech_positive / tech_total
            if tech_ratio >= 0.7:
                signal_score += 20
                reasons.append("技术面强势")
            elif tech_ratio >= 0.5:
                signal_score += 10
                reasons.append("技术面中性")
            else:
                reasons.append("技术面弱势")
        
        # 生成最终信号
        if signal_score >= 80:
            signal = "strong_buy"
        elif signal_score >= 60:
            signal = "buy"
        elif signal_score >= 40:
            signal = "hold"
        else:
            signal = "sell"
        
        return {
            "signal": signal,
            "score": signal_score,
            "reasons": reasons,
            "analysis": {
                "value": value_analysis,
                "technical": tech_analysis,
                "fundamental": fundamental_analysis
            }
        }
    
    def get_stock_pool(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """批量获取股票池分析结果"""
        results = []
        for symbol in symbols:
            signal = self.generate_buy_signal(symbol)
            signal["symbol"] = symbol
            results.append(signal)
        return results