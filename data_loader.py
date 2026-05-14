""" 数据加载模块 - 最终修复版（兼容 GitHub Actions） """
import logging
import time
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
import akshare as ak
import tushare as ts
from datetime import datetime, timedelta
import requests

logger = logging.getLogger(__name__)

# ========= 黑名单 =========
BLACKLIST_KEYWORDS = {"ST", "*ST", "退"}

def is_blacklisted(name: str) -> bool:
    if not name:
        return True
    return any(k in name for k in BLACKLIST_KEYWORDS)


class DataLoader:
    """数据加载器（最终修复版）"""

    def __init__(self, config):
        self.config = config
        self.ts_pro = None
        self._spot_cache = None
        self._spot_cache_time = 0
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

    # ================= 对外入口 =================
    def get_stock_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            realtime = self.get_realtime_data(symbol)
            if not realtime:
                return {"code": symbol, "error": "实时数据失败"}

            if is_blacklisted(realtime.get("name", "")):
                return {"code": symbol, "error": "黑名单股票"}

            kline = self._get_kline_from_tushare(symbol)
            if kline is None or kline.empty:
                kline = self.get_kline_data(symbol)

            tech = self.calculate_technical_indicators(kline)

            return {
                "code": symbol,
                "name": realtime.get("name", symbol),
                "current_price": realtime.get("price", 0),
                "change_percent": realtime.get("pct_change", 0),
                "volume": realtime.get("volume", 0),
                "amount": realtime.get("amount", 0),
                "open": realtime.get("open", 0),
                "high": realtime.get("high", 0),
                "low": realtime.get("low", 0),
                "technical": tech,
            }
        except Exception as e:
            logger.error(f"获取股票数据失败 {symbol}: {e}")
            return {"code": symbol, "error": str(e)}

    # ================= K 线 =================
    def _get_kline_from_tushare(self, symbol: str) -> Optional[pd.DataFrame]:
        if not self.ts_pro:
            return None
        try:
            ts_code = f"{symbol}.SH" if symbol.startswith("6") else f"{symbol}.SZ"
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
                },
                inplace=True,
            )
            return self._clean_kline(df)
        except Exception:
            return None

    def get_kline_data(self, symbol: str) -> Optional[pd.DataFrame]:
        try:
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=(datetime.now() - timedelta(days=120)).strftime("%Y%m%d"),
                end_date=datetime.now().strftime("%Y%m%d"),
                adjust="qfq",
            )
            if df is None or df.empty:
                return None
            return self._clean_kline(df.tail(60))
        except Exception:
            return None

    def _clean_kline(self, df: pd.DataFrame) -> pd.DataFrame:
        cols = ["开盘", "最高", "最低", "收盘", "成交量"]
        for c in cols:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df.dropna(subset=cols, inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    # ================= 实时行情 =================
    def get_realtime_data(self, symbol: str):
        for func in [
            self._get_from_tencent,
            self._get_from_akshare_sina,
        ]:
            try:
                data = func(symbol)
                if data:
                    return data
            except Exception:
                continue
        return None

    def _get_from_tencent(self, symbol: str):
        market = "sh" if symbol.startswith("6") else "sz"
        url = f"http://qt.gtimg.cn/q={market}{symbol}"
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return None
        p = r.text.split("~")
        if len(p) < 35:
            return None
        return {
            "code": symbol,
            "name": p[1],
            "price": float(p[3] or 0),
            "pct_change": float(p[32] or 0),
            "volume": int(float(p[6] or 0)),
            "amount": float(p[37] or 0),
            "open": float(p[5] or 0),
            "high": float(p[33] or 0),
            "low": float(p[34] or 0),
        }

    def _get_from_akshare_sina(self, symbol: str):
        now = time.time()
        if now - self._spot_cache_time > 3 or self._spot_cache is None:
            self._spot_cache = ak.stock_zh_a_spot_em()
            self._spot_cache_time = now

        df = self._spot_cache
        row = df[df["代码"] == symbol]
        if row.empty:
            return None
        row = row.iloc[0]
        return {
            "code": symbol,
            "name": row["名称"],
            "price": float(row.get("最新价", 0)),
            "pct_change": float(row.get("涨跌幅", 0)),
            "volume": int(float(row.get("成交量", 0))),
            "amount": float(row.get("成交额", 0)),
            "open": float(row.get("今开", 0)),
            "high": float(row.get("最高", 0)),
            "low": float(row.get("最低", 0)),
        }

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

    # ================= ✅ 关键修复点 =================
    def get_market_index(self) -> Dict[str, Any]:
        """获取大盘指数（兼容 main.py）"""
        indices = {
            "000001": "上证指数",
            "399001": "深证成指",
            "399006": "创业板指",
        }
        result = {}
        for code, name in indices.items():
            try:
                data = self.get_realtime_data(code)
                if data:
                    result[code] = {
                        "name": name,
                        "price": data.get("price", 0),
                        "pct_change": data.get("pct_change", 0),
                    }
            except Exception:
                continue
        return result
