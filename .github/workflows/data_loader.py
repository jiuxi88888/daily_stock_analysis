"""
数据加载模块 - 从多个数据源获取股票数据
"""
import logging
import time
import random
from typing import Dict, List, Any, Optional, Tuple
import tushare as ts
import pandas as pd
import akshare as ak
import efinance as ef
from datetime import datetime, timedelta
import requests
import json

logger = logging.getLogger(__name__)

class DataLoader:
    """数据加载器"""
    
    def __init__(self, config):
        self.config = config
        self.ts_pro = None
        self._init_tushare()
        
    def _init_tushare(self):
        """初始化Tushare"""
        if self.config.data_source.tushare_token:
            try:
                ts.set_token(self.config.data_source.tushare_token)
                self.ts_pro = ts.pro_api()
                logger.info("✅ Tushare 初始化成功")
            except Exception as e:
                logger.error(f"❌ Tushare 初始化失败: {e}")
                self.ts_pro = None
        else:
            logger.warning("⚠️  Tushare Token 未配置，Tushare功能不可用")
    
    def get_realtime_data(self, symbol: str, retry: int = 3) -> Optional[Dict[str, Any]]:
        """从多个数据源获取实时数据"""
        sources = self.config.data_source.realtime_source_priority.copy()
        
        for attempt in range(retry):
            for source in sources:
                try:
                    if source == 'tencent':
                        data = self._get_from_tencent(symbol)
                    elif source == 'akshare_sina':
                        data = self._get_from_akshare_sina(symbol)
                    elif source == 'efinance':
                        data = self._get_from_efinance(symbol)
                    elif source == 'akshare_em':
                        data = self._get_from_akshare_em(symbol)
                    elif source == 'tushare' and self.ts_pro:
                        data = self._get_from_tushare(symbol)
                    else:
                        continue
                    
                    if data:
                        logger.info(f"✅ 从 {source} 获取到 {symbol} 的实时数据")
                        return data
                        
                except Exception as e:
                    logger.warning(f"⚠️  从 {source} 获取 {symbol} 数据失败: {e}")
                    continue
            
            if attempt < retry - 1:
                delay = 2 ** attempt + random.random()
                logger.info(f"⏳ 第 {attempt + 1} 次重试，等待 {delay:.1f} 秒...")
                time.sleep(delay)
        
        logger.error(f"❌ 所有数据源都无法获取 {symbol} 的实时数据")
        return None
    
    def _get_from_tencent(self, symbol: str) -> Optional[Dict[str, Any]]:
        """从腾讯获取实时数据"""
        try:
            # 腾讯财经接口
            if symbol.startswith('6'):
                market = 'sh'
            elif symbol.startswith('0') or symbol.startswith('3'):
                market = 'sz'
            else:
                market = 'bj'
            
            url = f"http://qt.gtimg.cn/q={market}{symbol}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                content = response.text
                parts = content.split('~')
                if len(parts) > 40:
                    return {
                        'code': symbol,
                        'name': parts[1] if len(parts) > 1 else symbol,
                        'price': float(parts[3]) if parts[3] else 0.0,
                        'change': float(parts[4]) if parts[4] else 0.0,
                        'pct_change': float(parts[32]) if len(parts) > 32 and parts[32] else 0.0,
                        'volume': int(parts[6]) if len(parts) > 6 and parts[6] else 0,
                        'amount': float(parts[37]) if len(parts) > 37 and parts[37] else 0.0,
                        'open': float(parts[5]) if parts[5] else 0.0,
                        'high': float(parts[33]) if len(parts) > 33 and parts[33] else 0.0,
                        'low': float(parts[34]) if len(parts) > 34 and parts[34] else 0.0,
                        'pre_close': float(parts[4]) + float(parts[3]) if parts[3] and parts[4] else 0.0,
                        'time': parts[30] if len(parts) > 30 else '',
                        'source': 'tencent'
                    }
        except Exception as e:
            logger.debug(f"腾讯接口异常: {e}")
        return None
    
    def _get_from_akshare_sina(self, symbol: str) -> Optional[Dict[str, Any]]:
        """从新浪获取实时数据"""
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
                        'pre_close': float(row.get('昨收', 0)),
                        'time': datetime.now().strftime('%H:%M:%S'),
                        'source': 'akshare_sina'
                    }
        except Exception as e:
            logger.debug(f"Akshare新浪接口异常: {e}")
        return None
    
    def _get_from_efinance(self, symbol: str) -> Optional[Dict[str, Any]]:
        """从efinance获取实时数据"""
        try:
            stock_code = f"{symbol}.SH" if symbol.startswith('6') else f"{symbol}.SZ"
            df = ef.stock.get_quote_history(stock_code)
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                return {
                    'code': symbol,
                    'name': symbol,
                    'price': float(latest.get('收盘', 0)),
                    'change': float(latest.get('涨跌幅', 0)),
                    'pct_change': float(latest.get('涨跌幅', 0)),
                    'volume': int(latest.get('成交量', 0)),
                    'amount': float(latest.get('成交额', 0)),
                    'open': float(latest.get('开盘', 0)),
                    'high': float(latest.get('最高', 0)),
                    'low': float(latest.get('最低', 0)),
                    'pre_close': float(latest.get('昨收', 0)) if '昨收' in latest else float(latest.get('收盘', 0)) / (1 + float(latest.get('涨跌幅', 0)) / 100),
                    'time': str(latest.get('日期', '')),
                    'source': 'efinance'
                }
        except Exception as e:
            logger.debug(f"Efinance接口异常: {e}")
        return None
    
    def _get_from_akshare_em(self, symbol: str) -> Optional[Dict[str, Any]]:
        """从东方财富获取实时数据"""
        try:
            # Akshare的东方财富接口
            df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                stock_data = df[df['代码'] == symbol]
                if not stock_data.empty:
                    row = stock_data.iloc[0]
                    return {
                        'code': symbol,
                        'name': row.get('名称', symbol),
                        'price': float(row.get('最新价', 0)),
                        'change': float(row.get('涨跌额', 0)),
                        'pct_change': float(row.get('涨跌幅', 0)),
                        'volume': int(row.get('成交量', 0)),
                        'amount': float(row.get('成交额', 0)),
                        'open': float(row.get('今开', 0)),
                        'high': float(row.get('最高', 0)),
                        'low': float(row.get('最低', 0)),
                        'pre_close': float(row.get('昨收', 0)),
                        'time': datetime.now().strftime('%H:%M:%S'),
                        'source': 'akshare_em'
                    }
        except Exception as e:
            logger.debug(f"Akshare东方财富接口异常: {e}")
        return None
    
    def _get_from_tushare(self, symbol: str) -> Optional[Dict[str, Any]]:
        """从Tushare获取实时数据"""
        try:
            if not self.ts_pro:
                return None
                
            # 获取日线数据
            today = datetime.now().strftime('%Y%m%d')
            df = self.ts_pro.daily(ts_code=f"{symbol}.SH" if symbol.startswith('6') else f"{symbol}.SZ", 
                                  trade_date=today)
            
            if df is not None and not df.empty:
                row = df.iloc[0]
                return {
                    'code': symbol,
                    'name': symbol,
                    'price': float(row.get('close', 0)),
                    'change': float(row.get('change', 0)),
                    'pct_change': float(row.get('pct_chg', 0)),
                    'volume': int(row.get('vol', 0)),
                    'amount': float(row.get('amount', 0)),
                    'open': float(row.get('open', 0)),
                    'high': float(row.get('high', 0)),
                    'low': float(row.get('low', 0)),
                    'pre_close': float(row.get('pre_close', 0)),
                    'time': today,
                    'source': 'tushare'
                }
        except Exception as e:
            logger.debug(f"Tushare接口异常: {e}")
        return None
    
    def get_kline_data(self, symbol: str, days: int = 30) -> Optional[pd.DataFrame]:
        """获取K线数据"""
        try:
            if self.ts_pro:
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=days*2)).strftime('%Y%m%d')
                
                ts_code = f"{symbol}.SH" if symbol.startswith('6') else f"{symbol}.SZ"
                df = self.ts_pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
                
                if df is not None and not df.empty:
                    df = df.sort_values('trade_date')
                    df['date'] = pd.to_datetime(df['trade_date'])
                    df.set_index('date', inplace=True)
                    return df
        except Exception as e:
            logger.warning(f"获取K线数据失败: {e}")
        
        return None
    
    def get_market_index(self) -> Dict[str, Any]:
        """获取大盘指数"""
        indices = {
            'sh000001': '上证指数',
            'sz399001': '深证成指',
            'sz399006': '创业板指',
            'sh000688': '科创50'
        }
        
        result = {}
        for code, name in indices.items():
            try:
                symbol = code[2:]  # 去除市场前缀
                data = self.get_realtime_data(symbol)
                if data:
                    result[code] = {
                        'name': name,
                        'price': data.get('price', 0),
                        'change': data.get('change', 0),
                        'pct_change': data.get('pct_change', 0)
                    }
            except Exception as e:
                logger.warning(f"获取指数 {code} 失败: {e}")
        
        return result
    
    def get_stock_basic_info(self, symbol: str) -> Dict[str, Any]:
        """获取股票基本信息"""
        try:
            if self.ts_pro:
                ts_code = f"{symbol}.SH" if symbol.startswith('6') else f"{symbol}.SZ"
                df = self.ts_pro.stock_basic(ts_code=ts_code)
                if df is not None and not df.empty:
                    return df.iloc[0].to_dict()
        except Exception as e:
            logger.debug(f"获取股票基本信息失败: {e}")
        
        return {}
    
    def get_news(self, symbol: str, limit: int = 5) -> List[Dict[str, Any]]:
        """获取相关新闻（简化版）"""
        # 这里可以集成新闻API
        return []
