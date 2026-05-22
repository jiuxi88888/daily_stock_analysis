# -*- coding: utf-8 -*-
""" A股股票分析器 - 只分析自选股 """
import os
import logging
import time
import random
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


# ================= AI 引擎 =================
class AIEngine:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        # ✅ 核心修复：从 config 实例读取配置
        self.api_key = config.openai_api_key
        self.base_url = config.openai_base_url
        self.model = config.openai_model
        
        if not self.api_key:
            self.logger.warning("⚠️ OpenAI API Key 未配置")
        else:
            self.logger.info(f"✅ AI 引擎配置: {self.model}")

    def analyze_stock(self, stock_data):
        if not self.api_key:
            return {
                "ai_prediction": "⚠️ OpenAI API Key 未配置"
            }
        
        try:
            import openai
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=30
            )
            prompt = self._build_prompt(stock_data)
            
            self.logger.debug(f"调用AI分析: {stock_data.get('code')}")
            
            resp = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            content = resp.choices[0].message.content.strip()
            
            if not content:
                return {"ai_prediction": "AI返回空内容"}
                
            return {
                "ai_prediction": content
            }
            
        except Exception as e:
            self.logger.error(f"AI分析失败 {stock_data.get('code', '')}: {e}")
            return {
                "ai_prediction": f"⚠️ AI分析暂时不可用: {str(e)[:50]}"
            }

    def _build_prompt(self, d):
        return f"""
你是一位资深A股量化分析师。
请基于以下数据，生成一份简洁的股票分析。

股票：{d.get('name')}({d.get('code')})
当前价：{d.get('current_price')}
涨跌幅：{d.get('pct_chg', 'N/A')}%
趋势：{d.get('technical', {}).get('trend', 'N/A')}
MACD：{d.get('technical', {}).get('macd_status', 'N/A')}
RSI：{d.get('technical', {}).get('rsi', 'N/A')}

请输出分析内容（Markdown格式）：
1. 技术面分析
2. 短期趋势判断
3. 操作建议

保持简洁明了。
"""


# ================= 主分析器 =================
class StockAnalyzer:
    def __init__(self, data_loader, ai_engine, config):
        self.data_loader = data_loader
        self.ai_engine = ai_engine
        self.config = config
        self.logger = logging.getLogger(__name__)

    def analyze_stocks(self, stock_codes):
        """分析指定股票列表，返回分析结果"""
        results = []
        for code in stock_codes:
            self.logger.info(f"📊 分析: {code}")
            
            # 获取股票数据
            data = self.data_loader.get_stock_data(code)
            if not data or data.get("error"):
                self.logger.warning(f"⚠️ 获取 {code} 数据失败")
                continue

            # AI分析
            ai = self.ai_engine.analyze_stock(data)
            data.update(ai)
            
            # 确保有必要的字段
            if "ai_prediction" not in data or not data["ai_prediction"]:
                data["ai_prediction"] = "暂无AI分析"
            
            # 添加基础信息用于报告
            if "close" not in data:
                data["close"] = data.get("current_price", 0)
            if "pct_chg" not in data:
                data["pct_chg"] = 0
            
            results.append(data)
            
            # 延迟避免限流
            time.sleep(random.uniform(1, 2))
            
        return results
