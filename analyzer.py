# -*- coding: utf-8 -*-
""" A股股票分析器 - 自选股分析（含预测） """
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
        self.api_key = config.openai_api_key
        self.base_url = config.openai_base_url
        self.model = config.openai_model

        if not self.api_key:
            self.logger.warning("⚠️ OpenAI API Key 未配置")

    def analyze_stock(self, stock_data):
        if not self.api_key:
            return {"ai_prediction": "⚠️ OpenAI API Key 未配置"}

        try:
            import openai
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=30
            )

            prompt = self._build_prompt(stock_data)
            resp = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )

            content = resp.choices[0].message.content.strip()
            return {"ai_prediction": content or "暂无有效分析"}

        except Exception as e:
            self.logger.error(f"AI分析失败 {stock_data.get('code')}: {e}")
            return {"ai_prediction": f"⚠️ AI分析暂时不可用"}

    def _build_prompt(self, d):
        return f"""
你是一位资深A股量化分析师。
请基于以下数据，生成一份**包含未来走势与涨幅预判**的股票分析。

股票：{d.get('name')}({d.get('code')})
当前价：{d.get('current_price')}
涨跌幅：{d.get('pct_chg', 'N/A')}%
趋势：{d.get('technical', {}).get('trend', 'N/A')}
MACD：{d.get('technical', {}).get('macd_status', 'N/A')}
RSI：{d.get('technical', {}).get('rsi', 'N/A')}

请严格按照以下结构输出（Markdown格式，语言简练）：
1. 当前技术面定调
2. 未来3-5日走势预判（明确方向）
3. 预估涨幅区间（例如：预计上行空间约 2%~4%）
4. 操作建议（低吸 / 持股 / 风控位）

只输出分析内容，不要返回JSON或多余解释。
"""


# ================= 主分析器 =================
class StockAnalyzer:
    def __init__(self, data_loader, ai_engine, config):
        self.data_loader = data_loader
        self.ai_engine = ai_engine
        self.config = config
        self.logger = logging.getLogger(__name__)

    def analyze_stocks(self, stock_codes):
        """分析指定股票列表"""
        results = []

        for code in stock_codes:
            self.logger.info(f"📊 分析: {code}")

            data = self.data_loader.get_stock_data(code)
            if not data or data.get("error"):
                self.logger.warning(f"⚠️ 获取 {code} 数据失败")
                continue

            ai = self.ai_engine.analyze_stock(data)
            data.update(ai)

            # 兜底字段
            data.setdefault("ai_prediction", "暂无AI分析")
            data.setdefault("close", data.get("current_price", 0))
            data.setdefault("pct_chg", 0)

            results.append(data)

            # 防限流
            time.sleep(random.uniform(1, 2))

        return results
