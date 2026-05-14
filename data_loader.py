""" 数据加载模块 - 升级版 """
import logging
import time
import random
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
import akshare as ak
import tushare as ts
from datetime import datetime, timedelta
import requests

logger = logging.getLogger(__name__)

class DataLoader:
    """数据加载器"""
    def __init__(self, config):
        self.config = config
        self.ts_pro = None
        self._init_tushare()

    def _init_tushare(self):
        """初始化Tushare"""
        if self.config.tushare_token:
            try:
                ts.set_token(self.config.tushare_token)
                self.ts_pro = ts.pro_api()
                logger.info("✅ Tushare 初始化成功")
            except Exception as e:
                logger.error(f"❌ Tushare 初始化失败: {e}")

    def get_stock_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取股票完整数据"""
        try:
            realtime = self.get_realtime_data(symbol)
            if not realtime:
                return {'code': symbol, 'error': '获取实时数据失败'}
            
            # 尝试获取K线
            kline = self._get_kline_from_tushare(symbol)
            if kline is None or kline.empty:
                logger.info(f"🔄 tushare获取失败，尝试akshare: {symbol}")
                kline = self.get_kline_data(symbol, count=60)
            
            tech = self.calculate_technical_indicators(kline)
            
            result = {
                'code': symbol,
                'name': realtime.get('name', symbol),
                'current_price': realtime.get('price', 0),
                'change_percent': realtime.get('pct_change', 0),
                'change_amount': realtime.get('change', 0),
                'volume': realtime.get('volume', 0),
                'amount': realtime.get('amount', 0),
                'open': realtime.get('open', 0),
                'high': realtime.get('high', 0),
                'low': realtime.get('low', 0),
                'volume_ratio': tech.get('volume_ratio', 1),
                'turnover_rate': 0,
                'ma5': tech.get('ma5', 0),
                'ma10': tech.get('ma10', 0),
                'ma20': tech.get('ma20', 0),
                'price_history': self._kline_to_history(kline),
                'technical': tech
            }
            return result
        except Exception as e:
            logger.error(f"获取股票数据失败 {symbol}: {e}")
            return {'code': symbol, 'error': str(e)}

    def _get_kline_from_tushare(self, symbol: str, count: int = 60) -> Optional[pd.DataFrame]:
        """从Tushare获取K线数据"""
        if not self.ts_pro:
            logger.warning(f"⚠️ Tushare未初始化，跳过: {symbol}")
            return None
        try:
            ts_code = f"{symbol}.SZ" if not symbol.startswith('6') else f"{symbol}.SH"
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=count * 2)).strftime('%Y%m%d')
            
            logger.info(f"📊 尝试tushare获取K线: {symbol} ({ts_code})")
            
            df = self.ts_pro.daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            
            if df is not None and not df.empty:
                df = df.sort_values('trade_date')
                df = df.tail(count)
                df = df.rename(columns={
                    'trade_date': '日期',
                    'open': '开盘',
                    'high': '最高',
                    'low': '最低',
                    'close': '收盘',
                    'volume': '成交量'
                })
                logger.info(f"✅ Tushare K线成功 {symbol}: {len(df)}条")
                return df
            else:
                logger.warning(f"⚠️ Tushare返回空数据: {symbol}")
        except Exception as e:
            logger.warning(f"⚠️ Tushare K线失败 {symbol}: {e}")
        return None

    def _kline_to_history(self, kline_df: Optional[pd.DataFrame]) -> List[Dict]:
        """K线转历史数据"""
        if kline_df is None or kline_df.empty:
            return []
        history = []
        for _, row in kline_df.iterrows():
            history.append({
                'date': str(row.get('日期', '')),
                'open': float(row.get('开盘', 0)),
                'high': float(row.get('最高', 0)),
                'low': float(row.get('最低', 0)),
                'close': float(row.get('收盘', 0)),
                'volume': int(row.get('成交量', 0))
            })
        return history

    def get_realtime_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取实时数据"""
        source_str = getattr(self.config, 'realtime_source_priority', 'tencent,akshare_sina,efinance')
        sources = [s.strip() for s in source_str.split(',')]
        
        for source in sources:
            if source == 'tushare':
                continue
            try:
                if source == 'tencent':
                    data = self._get_from_tencent(symbol)
                elif source == 'akshare_sina':
                    data = self._get_from_akshare_sina(symbol)
                elif source == 'efinance':
                    data = self._get_from_efinance(symbol)
                if data:
                    return data
            except Exception as e:
                logger.warning(f"⚠️ {source} 获取失败: {e}")
        return None

    def _get_from_tencent(self, symbol: str) -> Optional[Dict[str, Any]]:
        """腾讯行情"""
        try:
            market = 'sh' if symbol.startswith('6') else 'sz'
            url = f"http://qt.gtimg.cn/q={market}{symbol}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                parts = response.text.split('~')
                if len(parts) > 30:
                    return {
                        'code': symbol,
                        'name': parts[1] if len(parts) > 1 else symbol,
                        'price': float(parts[3]) if parts[3] else 0.0,
                        'change': float(parts[4]) if parts[4] else 0.0,
                        'pct_change': float(parts[32]) if len(parts) > 32 and parts[32] else 0.0,
                        'volume': int(parts[6]) if len(parts) > 6 and parts[6] else 0,
                        'amount': float(parts[37]) if len(parts) > 37 and parts[37] else 0.0,
                        'open': float(parts[5]) if parts[5] else 0.0,
                        'high': float(parts[33]) if parts[33] else 0.0,
                        'low': float(parts[34]) if parts[34] else 0.0,
                        'source': 'tencent'
                    }
        except:
            pass
        return None

    def _get_from_akshare_sina(self, symbol: str) -> Optional[Dict[str, Any]]:
        """新浪行情"""
        try:
            df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                stock_data = df[df['代码'] == symbol]
                if not stock_data.empty:
                    row = stock_data.iloc[0]
                    return {
                        'code': symbol,
                        'name': row.get('名称', ''),
                        'price': float(row.get('最新价', 0)),
                        'change': float(row.get('涨跌额', 0)),
                        'pct_change': float(row.get('涨跌幅', 0)),
                        'volume': int(row.get('成交量', 0)),
                        'amount': float(row.get('成交额', 0)),
                        'open': float(row.get('今开', 0)),
                        'high': float(row.get('最高', 0)),
                        'low': float(row.get('最低', 0)),
                        'source': 'akshare_sina'
                    }
        except:
            pass
        return None

    def _get_from_efinance(self, symbol: str) -> Optional[Dict[str, Any]]:
        """efinance"""
        try:
            stock_code = symbol.replace('.SH', '').replace('.SZ', '')
            df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                start_date=(datetime.now() - timedelta(days=30)).strftime('%Y%m%d'),
                end_date=datetime.now().strftime('%Y%m%d'), adjust="")
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                return {
                    'code': symbol,
                    'name': symbol,
                    'price': float(latest.get('收盘', 0)),
                    'pct_change': float(latest.get('涨跌幅', 0)),
                    'volume': int(latest.get('成交量', 0)),
                    'source': 'efinance'
                }
        except:
            pass
        return None

    def get_market_index(self) -> Dict[str, Any]:
        """获取大盘指数"""
        indices = {'000001': '上证指数', '399001': '深证成指', '399006': '创业板指'}
        result = {}
        for code, name in indices.items():
            try:
                data = self.get_realtime_data(code)
                if data:
                    result[code] = {'name': name, 'price': data.get('price', 0), 'pct_change': data.get('pct_change', 0)}
            except:
                continue
        return result

    def get_kline_data(self, symbol: str, period: str = 'daily', count: int = 60) -> Optional[pd.DataFrame]:
        """获取K线数据"""
        try:
            stock_code = symbol.replace('.SH', '').replace('.SZ', '')
            df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                start_date=(datetime.now() - timedelta(days=count * 2)).strftime('%Y%m%d'),
                end_date=datetime.now().strftime('%Y%m%d'), adjust="")
            if df is not None and not df.empty:
                return df.tail(count)
        except Exception as e:
            logger.warning(f"K线获取失败 {symbol}: {e}")
        return None

    def calculate_technical_indicators(self, kline_df: Optional[pd.DataFrame]) -> Dict[str, Any]:
        """计算技术指标"""
        if kline_df is None or kline_df.empty:
            return {'volume_ratio': 1}
        try:
            close = kline_df['收盘'].astype(float)
            high = kline_df['最高'].astype(float)
            low = kline_df['最低'].astype(float)
            volume = kline_df['成交量'].astype(float)

            indicators = {}
            indicators['ma5'] = round(close.tail(5).mean(), 2)
            indicators['ma10'] = round(close.tail(10).mean(), 2)
            indicators['ma20'] = round(close.tail(20).mean(), 2)

            # MACD
            exp1 = close.ewm(span=12, adjust=False).mean()
            exp2 = close.ewm(span=26, adjust=False).mean()
            macd = 2 * (exp1 - exp2)
            signal = macd.ewm(span=9, adjust=False).mean()
            indicators['macd'] = round(macd.iloc[-1], 3)
            indicators['macd_signal'] = round(signal.iloc[-1], 3)
            indicators['macd_histogram'] = round(macd.iloc[-1] - signal.iloc[-1], 3)
            indicators['macd_status'] = '金叉（看涨）' if indicators['macd'] > 0 and indicators['macd'] > indicators['macd_signal'] else ('死叉（看跌）' if indicators['macd'] < 0 and indicators['macd'] < indicators['macd_signal'] else '震荡')

            # KDJ
            n = 9
            low_n = low.rolling(window=n).min()
            high_n = high.rolling(window=n).max()
            rsv = (close - low_n) / (high_n - low_n) * 100
            k = rsv.ewm(com=2, adjust=False).mean()
            d = k.ewm(com=2, adjust=False).mean()
            j = 3 * k - 2 * d
            indicators['kdj_k'] = round(k.iloc[-1], 2)
            indicators['kdj_d'] = round(d.iloc[-1], 2)
            indicators['kdj_j'] = round(j.iloc[-1], 2)
            indicators['kdj_signal'] = '金叉' if indicators['kdj_k'] > indicators['kdj_d'] else ('死叉' if indicators['kdj_k'] < indicators['kdj_d'] else '震荡')

            # RSI
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            indicators['rsi'] = round((100 - (100 / (1 + rs))).iloc[-1], 2)
            indicators['rsi_signal'] = '超买' if indicators['rsi'] > 70 else ('超卖' if indicators['rsi'] < 30 else '正常')

            # 布林带
            bb_period = 20
            if len(close) >= bb_period:
                bb_std = close.rolling(window=bb_period).std()
                bb_ma = close.rolling(window=bb_period).mean()
                indicators['boll_upper'] = round((bb_ma + 2 * bb_std).iloc[-1], 2)
                indicators['boll_middle'] = round(bb_ma.iloc[-1], 2)
                indicators['boll_lower'] = round((bb_ma - 2 * bb_std).iloc[-1], 2)
                current_price = close.iloc[-1]
                indicators['boll_signal'] = '突破上轨（强势）' if current_price > indicators['boll_upper'] else ('突破下轨（弱势）' if current_price < indicators['boll_lower'] else '轨道内')

            # 量比
            vol_ma5 = volume.tail(5).mean()
            indicators['volume_ratio'] = round(volume.iloc[-1] / vol_ma5, 2) if vol_ma5 > 0 else 1
            indicators['volume_signal'] = '放量' if volume.iloc[-1] > vol_ma5 * 1.5 else ('缩量' if volume.iloc[-1] < vol_ma5 * 0.5 else '正常')

            return indicators
        except Exception as e:
            logger.error(f"技术指标计算失败: {e}")
            return {'volume_ratio': 1}
