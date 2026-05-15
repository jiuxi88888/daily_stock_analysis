# -*- coding: utf-8 -*-
""" A股股票分析器 - 固定股票 + 精选3只预测版 """
import os
import logging
import time
import random
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


# ================= 股票精选器（✅ 额外精选 Top 3） =================
class StockSelector:
    def __init__(self, data_loader, config):
        self.data_loader = data_loader
        self.config = config
        self.logger = logging.getLogger(__name__)

    def select_stocks(self, count=3):
        """
        在自选股基础上，额外精选 Top 3 只技术面最强的股票
        """
        self.logger.info("🎯 在自选股基础上精选 Top 3 只股票...")
        watchlist = self.config.stock_list
        if not watchlist:
            return []

        candidates = []
        for code in watchlist:
            try:
                data = self.data_loader.get_stock_data(code)
                if not data or data.get("error"):
                    continue

                tech = data.get("technical", {})
                score = tech.get("score", 0)
                if score < 4:
                    continue

                candidates.append({
                    "code": code,
                    "name": data.get("name", code),
                    "score": score
                })
            except Exception:
                continue

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:count]


# ================= AI 引擎（✅ 完整预测 + 涨幅） =================
class AIEngine:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.bianxie.ai/v1")
        self.model = os.getenv("AI_MODEL", "gpt-4o")

    def analyze_stock(self, stock_data):
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
            return {
                "ai_prediction": resp.choices[0].message.content.strip()
            }
        except Exception:
            return {
                "ai_prediction": "分析暂时不可用"
            }

    def _build_prompt(self, d):
        return f"""
你是一位资深A股量化分析师。
请基于以下数据，生成一份**完整的股票预测分析**，必须包含未来走势和涨幅预判。

股票：{d.get('name')}({d.get('code')}
当前价：{d.get('current_price')}
趋势：{d.get('technical', {}).get('trend')}
MACD：{d.get('technical', {}).get('macd_status')}
RSI：{d.get('technical', {}).get('rsi')}

请严格按照以下结构输出（Markdown格式，不要JSON，不要废话）：
1. 当前技术面定调
2. 未来3-5日走势预判（明确方向）
3. 预估涨幅区间（例如：预计上行空间约 2%~4%）
4. 操作建议（低吸 / 持股 / 风控位）

只输出分析内容。
"""


# ================= 主分析器 =================
class StockAnalyzer:
    def __init__(self, data_loader, ai_engine, config):
        self.data_loader = data_loader
        self.ai_engine = ai_engine
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.stock_selector = StockSelector(data_loader, config)

    def analyze_stocks(self, stock_codes):
        results = []
        for code in stock_codes:
            self.logger.info(f"📊 分析: {code}")
            data = self.data_loader.get_stock_data(code)
            if not data or data.get("error"):
                continue

            ai = self.ai_engine.analyze_stock(data)
            data.update(ai)
            data["is_selected"] = False
            results.append(data)
            time.sleep(random.uniform(1, 2))
        return results

    def select_and_analyze(self, count=3):
        selected = self.stock_selector.select_stocks(count)
        results = self.analyze_stocks([s["code"] for s in selected])
        for r in results:
            r["is_selected"] = True
        return results
