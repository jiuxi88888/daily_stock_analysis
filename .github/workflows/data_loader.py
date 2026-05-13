"""
数据加载模块 - 升级版
增加全市场扫描、技术指标、资金流向
"""
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
    """数据加载器 - 升级版"""
    
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
                        'open': float(parts[5]) if parts[5] else 0.0,
                        'high': float(parts[33]) if parts[33] else 0.0,
                        'low': float(parts[34]) if parts[34] else 0.0,
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
                        'open': float(row.get('今开', 0)),
                        'high': float(row.get('最高', 0)),
                        'low': float(row.get('最低', 0)),
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
            df = ak.stock_zh_a_hist(
                symbol=stock_code.replace('.SH', '').replace('.SZ', ''),
                period="daily",
                start_date=(datetime.now() - timedelta(days=30)).strftime('%Y%m%d'),
                end_date=datetime.now().strftime('%Y%m%d'),
                adjust=""
            )
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
    
    # ========== 新增功能 ==========
    
    def scan_market(self, limit: int = 100) -> List[Dict[str, Any]]:
        """全市场扫描，筛选优质股票"""
        try:
            logger.info(f"🔍 开始全市场扫描...")
            
            df = ak.stock_zh_a_spot_em()
            
            if df is None or df.empty:
                logger.error("❌ 获取全市场数据失败")
                return []
            
            df = df[df['代码'].str.startswith(('0', '3', '6'))]
            df = df[~df['名称'].str.contains('ST|退市|N', na=False)]
            df = df[df['成交额'] > 1e8]
            df = df.sort_values('涨跌幅', ascending=False)
            
            top_stocks = df.head(limit)
            
            result = []
            for _, row in top_stocks.iterrows():
                try:
                    stock = {
                        'code': str(row['代码']),
                        'name': str(row['名称']),
                        'price': float(row['最新价']),
                        'pct_change': float(row['涨跌幅']),
                        'change': float(row['涨跌额']),
                        'volume': int(row['成交量']),
                        'amount': float(row['成交额']),
                        'open': float(row['今开']),
                        'high': float(row['最高']),
                        'low': float(row['最低']),
                        'amplitude': float(row.get('振幅', 0)) if '振幅' in row else 0,
                    }
                    result.append(stock)
                except:
                    continue
            
            logger.info(f"✅ 全市场扫描完成，筛选出 {len(result)} 只股票")
            return result
            
        except Exception as e:
            logger.error(f"❌ 全市场扫描失败: {e}")
            return []
    
    def get_kline_data(self, symbol: str, period: str = 'daily', count: int = 60) -> Optional[pd.DataFrame]:
        """获取K线数据"""
        try:
            stock_code = f"{symbol}.SH" if symbol.startswith('6') else f"{symbol}.SZ"
            
            df = ak.stock_zh_a_hist(
                symbol=stock_code.replace('.SH', '').replace('.SZ', ''),
                period="daily",
                start_date=(datetime.now() - timedelta(days=count * 2)).strftime('%Y%m%d'),
                end_date=datetime.now().strftime('%Y%m%d'),
                adjust=""
            )
            
            if df is not None and not df.empty:
                df = df.tail(count)
                return df
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 获取K线数据失败 {symbol}: {e}")
            return None
    
    def calculate_technical_indicators(self, kline_df: pd.DataFrame) -> Dict[str, Any]:
        """计算技术指标"""
        if kline_df is None or kline_df.empty:
            return {}
        
        try:
            close = kline_df['收盘'].astype(float)
            high = kline_df['最高'].astype(float)
            low = kline_df['最低'].astype(float)
            volume = kline_df['成交量'].astype(float)
            
            indicators = {}
            
            # MA均线
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
            
            if indicators['macd'] > 0 and indicators['macd'] > indicators['macd_signal']:
                indicators['macd_status'] = '金叉（看涨）'
            elif indicators['macd'] < 0 and indicators['macd'] < indicators['macd_signal']:
                indicators['macd_status'] = '死叉（看跌）'
            else:
                indicators['macd_status'] = '震荡'
            
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
            
            if indicators['kdj_k'] > indicators['kdj_d']:
                indicators['kdj_signal'] = '金叉'
            elif indicators['kdj_k'] < indicators['kdj_d']:
                indicators['kdj_signal'] = '死叉'
            else:
                indicators['kdj_signal'] = '震荡'
            
            # RSI
            rsi_period = 14
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(window=rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
            rs = gain / loss
            indicators['rsi'] = round(100 - (100 / (1 + rs)).iloc[-1], 2)
            
            if indicators['rsi'] > 70:
                indicators['rsi_signal'] = '超买'
            elif indicators['rsi'] < 30:
                indicators['rsi_signal'] = '超卖'
            else:
                indicators['rsi_signal'] = '正常'
            
            # 布林带
            bb_period = 20
            bb_std = close.rolling(window=bb_period).std()
            bb_ma = close.rolling(window=bb_period).mean()
            
            indicators['boll_upper'] = round(bb_ma.iloc[-1] + 2 * bb_std.iloc[-1], 2)
            indicators['boll_middle'] = round(bb_ma.iloc[-1], 2)
            indicators['boll_lower'] = round(bb_ma.iloc[-1] - 2 * bb_std.iloc[-1], 2)
            
            current_price = close.iloc[-1]
            if current_price > indicators['boll_upper']:
                indicators['boll_signal'] = '突破上轨（强势）'
            elif current_price < indicators['boll_lower']:
                indicators['boll_signal'] = '突破下轨（弱势）'
            else:
                indicators['boll_signal'] = '轨道内'
            
            # 成交量分析
            vol_ma5 = volume.tail(5).mean()
            indicators['volume_ratio'] = round(volume.iloc[-1] / vol_ma5, 2)
            
            if volume.iloc[-1] > vol_ma5 * 1.5:
                indicators['volume_signal'] = '放量'
            elif volume.iloc[-1] < vol_ma5 * 0.5:
                indicators['volume_signal'] = '缩量'
            else:
                indicators['volume_signal'] = '正常'
            
            return indicators
            
        except Exception as e:
            logger.error(f"❌ 计算技术指标失败: {e}")
            return {}
    
    def get_financial_data(self, symbol: str) -> Dict[str, Any]:
        """获取财务数据"""
        if not self.ts_pro:
            return {}
        
        try:
            df = self.ts_pro.fina_indicator(
                ts_code=f"{symbol}.SZ" if not symbol.startswith('6') else f"{symbol}.SH",
                start_date=(datetime.now() - timedelta(days=90)).strftime('%Y%m%d')
            )
            
            if df is not None and not df.empty:
                latest = df.iloc[0]
                return {
                    'pe': round(float(latest.get('pe', 0)), 2) if latest.get('pe') else 0,
                    'pb': round(float(latest.get('pb', 0)), 2) if latest.get('pb') else 0,
                    'roe': round(float(latest.get('roe', 0)), 2) if latest.get('roe') else 0,
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"❌ 获取财务数据失败 {symbol}: {e}")
            return {}
    
    def get_money_flow(self, symbol: str) -> Dict[str, Any]:
        """获取资金流向"""
        try:
            df = ak.stock_individual_fund_flow(stock=symbol, market="sh" if symbol.startswith('6') else "sz")
            
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                return {
                    'main_net_inflow': float(latest.get('主力净流入-净额', 0)) if '主力净流入-净额' in latest else 0,
                    'main_net_inflow_pct': float(latest.get('主力净流入-净占比', 0)) if '主力净流入-净占比' in latest else 0,
                }
            
            return {}
            
        except Exception as e:
            logger.debug(f"获取资金流向失败 {symbol}: {e}")
            return {}
    
    def select_top_stocks(self, count: int = 8) -> List[Dict[str, Any]]:
        """精选股票"""
        logger.info(f"🎯 开始精选股票（目标: {count}只）...")
        
        stocks = self.scan_market(limit=100)
        
        if not stocks:
            logger.error("❌ 无法获取市场数据")
            return []
        
        scored_stocks = []
        
        for stock in stocks:
            try:
                code = stock['code']
                
                kline = self.get_kline_data(code, count=60)
                tech = self.calculate_technical_indicators(kline)
                score = self._calculate_score(stock, tech)
                
                stock['tech'] = tech
                stock['score'] = score
                
                scored_stocks.append(stock)
                
                time.sleep(0.1)
                
            except Exception as e:
                logger.debug(f"处理 {stock.get('code')} 时出错: {e}")
                continue
        
        scored_stocks.sort(key=lambda x: x['score'], reverse=True)
        top_stocks = scored_stocks[:count]
        
        logger.info(f"✅ 精选完成，选出 {len(top_stocks)} 只股票")
        
        return top_stocks
    
    def _calculate_score(self, stock: Dict, tech: Dict) -> float:
        """计算股票评分"""
        score = 0.0
        
        pct = stock.get('pct_change', 0)
        if 2 <= pct <= 5:
            score += 15
        elif 0 <= pct < 2:
            score += 10
        elif 5 <= pct <= 9:
            score += 12
        elif -2 <= pct < 0:
            score += 5
        
        vol_ratio = tech.get('volume_ratio', 1)
        if vol_ratio > 2:
            score += 10
        elif vol_ratio > 1.5:
            score += 8
        elif vol_ratio > 1:
            score += 5
        
        macd_signal = tech.get('macd_status', '震荡')
        if '金叉' in macd_signal and tech.get('macd', 0) > 0:
            score += 10
        elif '金叉' in macd_signal:
            score += 7
        
        kdj_signal = tech.get('kdj_signal', '震荡')
        if '金叉' in kdj_signal:
            score += 8
        
        rsi_signal = tech.get('rsi_signal', '正常')
        if rsi_signal == '正常':
            score += 8
        elif rsi_signal == '超卖':
            score += 10
        
        boll_signal = tech.get('boll_signal', '')
        if '突破上轨' in boll_signal:
            score += 5
        
        return round(score, 2)
