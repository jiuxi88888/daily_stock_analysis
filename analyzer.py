# -*- coding: utf-8 -*-
""" A股股票分析器 - 最终版 v2.0 """
import os
import sys
import logging
import time
import random
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


# ================= 技术指标 =================
class TechnicalIndicators:
    @staticmethod
    def calculate_ma(prices, period):
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period

    @staticmethod
    def calculate_macd(prices, fast=12, slow=26, signal=9):
        if len(prices) < slow:
            return {'macd': None, 'signal': None, 'histogram': None}

        ema_fast = [sum(prices[:fast]) / fast]
        ema_slow = [sum(prices[:slow]) / slow]
        mul_fast = 2 / (fast + 1)
        mul_slow = 2 / (slow + 1)

        for p in prices[fast:]:
            ema_fast.append((p - ema_fast[-1]) * mul_fast + ema_fast[-1])
        for p in prices[slow:]:
            ema_slow.append((p - ema_slow[-1]) * mul_slow + ema_slow[-1])

        dif = ema_fast[-1] - ema_slow[-1]
        macd_line = [ema_fast[i] - ema_slow[i] for i in range(len(ema_fast))]
        dea = sum(macd_line[-signal:]) / signal
        return {'macd': dif, 'signal': dea, 'histogram': (dif - dea) * 2}

    @staticmethod
    def calculate_rsi(prices, period=14):
        if len(prices) < period + 1:
            return None
        gains, losses = [], []
        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]
            gains.append(change if change > 0 else 0)
            losses.append(-change if change < 0 else 0)
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss == 0:
            return 100
        return 100 - (100 / (1 + avg_gain / avg_loss))


# ================= 股票精选器（✅ 核心修复） =================
class StockSelector:
    def __init__(self, data_loader, config):
        self.data_loader = data_loader
        self.config = config
        self.logger = logging.getLogger(__name__)

    def select_stocks(self, count=8):
        self.logger.info(f"🎯 开始精选股票（目标: {count}只）...")
        watchlist = self.config.stock_list
        if not watchlist:
            self.logger.warning("⚠️ 自选股为空，无法精选")
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
                    "score": score,
                    "reason": f"技术评分 {score}｜趋势 {tech.get('trend')}"
                })
            except Exception as e:
                self.logger.warning(f"⚠️ 精选失败 {code}: {e}")

        candidates.sort(key=lambda x: x["score"], reverse=True)
        selected = candidates[:count]
        self.logger.info(f"✅ 精选完成，共 {len(selected)} 只")
        return selected


# ================= AI 引擎 =================
class AIEngine:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.bianxie.ai/v1")
        self.model = os.getenv("AI_MODEL", "gpt-4o")
        self.logger.info(f"🤖 AI引擎初始化: {self.base_url}/{self.model}")

    def analyze_stock(self, stock_data):
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
            prompt = self._build_prompt(stock_data)
            resp = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            return self._parse(resp.choices[0].message.content)
        except Exception:
            return {
                "advice": "观望",
                "score": 50,
                "summary": "AI分析不可用",
                "risk": "",
                "trend": "震荡"
            }

    def _build_prompt(self, d):
        return f"""
你是A股分析师。
股票：{d.get('name')}({d.get('code')})
价格：{d.get('current_price')}
技术评分：{d.get('technical', {}).get('score')}
趋势：{d.get('technical', {}).get('trend')}
MACD：{d.get('technical', {}).get('macd_status')}
RSI：{d.get('technical', {}).get('rsi')}

请给出：建议(买入/观望/卖出)、评分(0-100)、一句话理由。
返回JSON格式。
"""

    def _parse(self, text):
        import json
        try:
            return json.loads(text[text.find("{"):text.rfind("}") + 1])
        except:
            return {
                "advice": "观望",
                "score": 50,
                "summary": text[:80],
                "risk": "",
                "trend": "震荡"
            }


# ================= 主分析器 =================
class StockAnalyzer:
    def __init__(self, data_loader, ai_engine, config):
        self.data_loader = data_loader
        self.ai_engine = ai_engine
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.tech_indicator = TechnicalIndicators()
        self.stock_selector = StockSelector(data_loader, config)

    def analyze_stocks(self, stock_codes):
        results = []
        for code in stock_codes:
            self.logger.info(f"📊 分析: {code}")
            data = self.data_loader.get_stock_data(code)
            if not data or data.get("error"):
                results.append({"code": code, "error": "数据失败"})
                continue

            data["technical"] = self._calc_tech(data)
            ai = self.ai_engine.analyze_stock(data)
            data.update(ai)
            data["decision"] = self._decide(data)
            data["is_selected"] = False
            results.append(data)
            time.sleep(random.uniform(1, 2))
        return results

    def select_and_analyze(self, count=8):
        selected = self.stock_selector.select_stocks(count)
        results = self.analyze_stocks([s["code"] for s in selected])
        for r in results:
            r["is_selected"] = True
            for s in selected:
                if s["code"] == r["code"]:
                    r["selection_reason"] = s.get("reason", "")
        return results

    def _calc_tech(self, data):
        hist = data.get("price_history", [])
        closes = [h["close"] for h in hist]
        tech = {}

        if len(closes) < 20:
            return tech

        ma5 = sum(closes[-5:]) / 5
        ma20 = sum(closes[-20:]) / 20
        tech["trend"] = "up" if closes[-1] > ma20 else "down"

        macd = self.tech_indicator.calculate_macd(closes)
        rsi = self.tech_indicator.calculate_rsi(closes)

        score = 0
        score += 3 if tech["trend"] == "up" else 0
        if macd.get("macd", 0) > macd.get("signal", 0):
            score += 2
        if rsi and 40 <= rsi <= 70:
            score += 1

        tech["score"] = score
        tech["macd_status"] = "金叉" if macd.get("macd", 0) > macd.get("signal", 0) else "死叉"
        tech["rsi"] = rsi
        return tech

    def _decide(self, data):
        score = data.get("ai_score", 50)
        if score >= 70:
            return "🟢 买入"
        elif score >= 40:
            return "🟡 观望"
        return "🔴 卖出"
