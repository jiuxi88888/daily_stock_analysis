# -*- coding: utf-8 -*-
"""
数据加载模块 - GitHub Actions 专用稳定版
（不使用实时行情，只用 Tushare 日线）
"""
import logging
import os
from typing import Dict, Any, Optional
import pandas as pd
from datetime import datetime, timedelta
import tushare as ts

logger = logging.getLogger(__name__)

# ========= 黑名单 =========
BLACKLIST_KEYWORDS = {"ST", "*ST", "退"}


def is_blacklisted(name: str) -> bool:
    if not name:
        return True
    return any(k in name for k in BLACKLIST_KEYWORDS)


class DataLoader:
    """数据加载器（GitHub Actions 专用）"""

    def __init__(self, config):
        self.config = config
        self.ts_pro = None
        self._init_tushare()

    # ================= 初始化 =================
    def _init_tushare(self):
        token = getattr(self.config, "tushare_token", None)
        if token:
            try:
                ts.set_token(token)
                self.ts_pro = ts.pro_api()
                logger.info("✅ Tushare 初始化成功")
            except Exception as e:
                logger.error(f"❌ Tushare 初始化失败: {e}")

    # ================= 对外入口（✅ 核心修复） =================
    def get_stock_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        GitHub Actions 专用：
        - ❌ 不调用实时行情
        - ✅ 只用 Tushare 日线
        """
        try:
            # 1️⃣ 获取 K 线
            kline = self._get_kline_from_tushare(symbol)
            if kline is None or kline.empty:
                return {"code": symbol, "error": "K线数据失败"}

            # 2️⃣ 黑名单过滤
            name = self.get_stock_name(symbol)
            if is_blacklisted(name):
                return {"code": symbol, "error": "黑名单股票"}

            # 3️⃣ 技术指标
            tech = self.calculate_technical_indicators(kline)

            # 4️⃣ 取最新一根 K 线作为“当前行情”
            last = kline.iloc[-1]

            return {
                "code": symbol,
                "name": name,
                "current_price": last["收盘"],
                "change_percent": last.get("涨跌幅", 0),
                "volume": last.get("成交量", 0),
                "amount": 0,
                "open": last["开盘"],
                "high": last["最高"],
                "low": last["最低"],
                "technical": tech,
            }

        except Exception as e:
            logger.error(f"获取股票数据失败 {symbol}: {e}")
            return {"code": symbol, "error": str(e)}

    # ================= K 线（Tushare 日线） =================
    def _get_kline_from_tushare(self, symbol: str) -> Optional[pd.DataFrame]:
        if not self.ts_pro:
            return None

        try:
            ts_code = self.normalize_code(symbol)
            end = datetime.now().strftime("%Y%m%d")
            start = (datetime.now() - timedelta(days=120)).strftime("%Y%m%d")

            df = self.ts_pro.daily(
                ts_code=ts_code,
                start_date=start,
                end_date=end,
                adj="qfq",
            )

            if df is None or df.empty:
                return None

            df = df.sort_values("trade_date").tail(60)
            df.rename(
                columns={
                    "trade_date": "日期",
                    "open": "开盘",
                    "high": "最高",
                    "low": "最低",
                    "close": "收盘",
                    "vol": "成交量",
                    "pct_chg": "涨跌幅",
                },
                inplace=True,
            )

            return df

        except Exception as e:
            logger.warning(f"Tushare 获取失败 {symbol}: {e}")
            return None

    # ================= 技术指标 =================
    def calculate_technical_indicators(self, kline_df: pd.DataFrame) -> Dict[str, Any]:
        if kline_df is None or kline_df.empty:
            return {}

        close = kline_df["收盘"].astype(float)
        high = kline_df["最高"].astype(float)
        low = kline_df["最低"].astype(float)
        volume = kline_df["成交量"].astype(float)

        tech = {}
        tech["ma5"] = close.tail(5).mean()
        tech["ma10"] = close.tail(10).mean()
        tech["ma20"] = close.tail(20).mean()
        tech["trend"] = "up" if close.iloc[-1] > tech["ma20"] else "down"

        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        hist = macd - signal

        tech["macd"] = macd.iloc[-1]
        tech["macd_signal"] = signal.iloc[-1]
        tech["macd_histogram"] = hist.iloc[-1]

        if macd.iloc[-1] > signal.iloc[-1] and hist.iloc[-1] > 0:
            tech["macd_status"] = "有效金叉"
        elif macd.iloc[-1] < signal.iloc[-1] and hist.iloc[-1] < 0:
            tech["macd_status"] = "有效死叉"
        else:
            tech["macd_status"] = "震荡"

        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss
        tech["rsi"] = 100 - (100 / (1 + rs)).iloc[-1]

        vol_ma5 = volume.tail(5).mean()
        tech["volume_ratio"] = volume.iloc[-1] / vol_ma5 if vol_ma5 else 1

        score = 0
        score += 3 if tech["trend"] == "up" else -1
        if "有效金叉" in tech["macd_status"]:
            score += 2
        elif "有效死叉" in tech["macd_status"]:
            score -= 2
        if tech["volume_ratio"] > 1.5:
            score += 1
        if 40 <= tech["rsi"] <= 70:
            score += 1
        elif tech["rsi"] > 80 or tech["rsi"] < 20:
            score -= 1

        tech["score"] = max(0, min(score, 10))
        tech["signal_level"] = (
            "强" if tech["score"] >= 7 else "中" if tech["score"] >= 4 else "弱"
        )
        return tech

    # ================= 工具 =================
    def normalize_code(self, code: str) -> str:
        code = str(code).strip()
        if code.endswith((".SH", ".SZ")):
            return code
        if code.startswith("6"):
            return f"{code}.SH"
        elif code.startswith(("0", "3")):
            return f"{code}.SZ"
        return code

    def get_stock_name(self, symbol: str) -> str:
        try:
            ts_code = self.normalize_code(symbol)
            df = self.ts_pro.stock_basic(ts_code=ts_code, fields="name")
            return df.iloc[0]["name"] if not df.empty else symbol
        except Exception:
            return symbol

    # ================= 大盘指数（兼容 main.py） =================
    def get_market_index(self) -> Dict[str, Any]:
        indices = {
            "000001": "上证指数",
            "399001": "深证成指",
            "399006": "创业板指",
        }
        result = {}
        for code, name in indices.items():
            try:
                ts_code = f"{code}.SH" if code.startswith("0") else f"{code}.SZ"
                df = self.ts_pro.index_daily(
                    ts_code=ts_code,
                    start_date=(datetime.now() - timedelta(days=5)).strftime("%Y%m%d"),
                    end_date=datetime.now().strftime("%Y%m%d"),
                )
                if df is not None and not df.empty:
                    last = df.iloc[-1]
                    result[code] = {
                        "name": name,
                        "price": last["close"],
                        "pct_change": last.get("pct_chg", 0),
                    }
            except Exception:
                continue
        return result
