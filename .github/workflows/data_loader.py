"""
数据加载模块 - 适配便携AI版本
"""
import logging
import time
import random
from typing import Dict, Any, Optional
import tushare as ts
import pandas as pd
import akshare as ak
import efinance as ef
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
        if self.config.data_source.tushare_token:
            try:
                ts.set_token(self.config.data_source.tushare_token)
                self.ts_pro = ts.pro_api()
                logger.info("✅ Tushare 初始化成功")
            except Exception as e:
                logger.error(f"❌ Tushare 初始化失败: {e}")
    
    def get_realtime_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取股票实时数据"""
        sources = self.config.data_source.realtime_source_priority.copy()
        
        for source in sources:
            try:
                if source == 'tencent':
                    data = self._get_from_tencent(symbol)
                elif source == 'akshare_sina':
                    data = self._get_from_akshare_sina(symbol)
                elif source == 'efinance':
                    data = self._get_from_efinance(symbol)
                
                if data:
                    logger.info(f"✅ 从 {source} 获取到 {symbol} 数据")
                    return data
            except Exception as e:
                logger.warning(f"⚠️  {source} 获取失败: {e}")
                continue
        
        logger.error(f"❌ 无法获取 {symbol} 实时数据")
        return None
    
    def _get_from_tencent(self, symbol: str) -> Optional[Dict[str, Any]]:
        """从腾讯获取数据"""
        try:
            if symbol.startswith('6'):
                market = 'sh'
            elif symbol.startswith('0') or symbol.startswith('3'):
                market = 'sz'
            else:
                market = 'bj'
            
            url = f"http://qt.gtimg.cn/q={market}{symbol}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                content = response.text
                parts = content.split('~')
                if len(parts) > 30:
                    return {
                        'code': symbol,
                        'name': parts[1] if len(parts) > 1 else symbol,
                        'price': float(parts[3]) if parts[3] else 0.0,
                        'change': float(parts[4]) if parts[4] else 0.0,
                        'pct_change': float(parts[32]) if len(parts) > 32 and parts[32] else 0.0,
                        'volume': int(parts[6]) if len(parts) > 6 and parts[6] else 0,
                        'amount': float(parts[37]) if len(parts) > 37 and parts[37] else 0.0,
                        'time': parts[30] if len(parts) > 30 else '',
                        'source': 'tencent'
                    }
        except:
            pass
        return None
    
    def _get_from_akshare_sina(self, symbol: str) -> Optional[Dict[str, Any]]:
        """从新浪获取数据"""
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
                        'time': datetime.now().strftime('%H:%M:%S'),
                        'source': 'akshare_sina'
                    }
        except:
            pass
        return None
    
    def _get_from_efinance(self, symbol: str) -> Optional[Dict[str, Any]]:
        """从efinance获取数据"""
        try:
            stock_code = f"{symbol}.SH" if symbol.startswith('6') else f"{symbol}.SZ"
            df = ef.stock.get_quote_history(stock_code, klt=1)
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                return {
                    'code': symbol,
                    'name': symbol,
                    'price': float(latest.get('收盘', 0)),
                    'pct_change': float(latest.get('涨跌幅', 0)),
                    'volume': int(latest.get('成交量', 0)),
                    'amount': float(latest.get('成交额', 0)),
                    'time': str(latest.get('日期', '')),
                    'source': 'efinance'
                }
        except:
            pass
        return None
    
    def get_market_index(self) -> Dict[str, Any]:
        """获取大盘指数"""
        indices = {
            '000001': '上证指数',
            '399001': '深证成指',
            '399006': '创业板指'
        }
        
        result = {}
        for code, name in indices.items():
            try:
                data = self.get_realtime_data(code)
                if data:
                    result[code] = {
                        'name': name,
                        'price': data.get('price', 0),
                        'pct_change': data.get('pct_change', 0)
                    }
            except:
                continue
        
        return result
