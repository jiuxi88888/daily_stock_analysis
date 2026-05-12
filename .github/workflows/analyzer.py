"""
分析模块 - 升级版
增强AI分析能力，提高预测准确度
"""
import logging
import time
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime
from openai import OpenAI

logger = logging.getLogger(__name__)


class AIEngine:
    """AI 分析引擎 - 升级版"""
    
    def __init__(self, config):
        self.config = config
        self.client = None
        self._init_ai()
    
    def _init_ai(self):
        """初始化AI客户端"""
        if self.config.ai.api_key:
            try:
                self.client = OpenAI(
                    api_key=self.config.ai.api_key,
                    base_url=self.config.ai.base_url,
                    timeout=self.config.ai.timeout
                )
                logger.info(f"✅ AI客户端初始化成功 (BaseURL: {self.config.ai.base_url})")
            except Exception as e:
                logger.error(f"❌ AI客户端初始化失败: {e}")
        else:
            logger.warning("⚠️  AI API Key 未配置")
    
    def analyze_stock(self, stock_data: Dict[str, Any], market_data: Dict[str, Any] = None) -> Optional[str]:
        """使用AI分析股票"""
        if not self.client:
            return "⚠️ AI分析不可用（未配置API密钥）"
        
        try:
            prompt = self._build_analysis_prompt(stock_data, market_data)
            
            response = self.client.chat.completions.create(
                model=self.config.ai.model,
                messages=[
                    {
                        "role": "system", 
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=self.config.ai.max_tokens,
                temperature=self.config.ai.temperature
            )
            
            analysis = response.choices[0].message.content
            logger.info(f"✅ AI分析完成 (模型: {self.config.ai.model})")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ AI分析失败: {e}")
            return None
    
    def _get_system_prompt(self) -> str:
        """
        升级版系统提示词
        让AI更专业地分析股票
        """
        return """你是一位具有10年经验的资深股票分析师，专注于A股市场短线和中线投资。

## 分析原则
1. **客观严谨**：基于数据说话，不主观臆断
2. **风险第一**：永远把风险控制放在首位
3. **顺势而为**：尊重市场趋势，不逆势操作

## 分析框架（请严格按此框架输出）

### 一、市场环境判断
- 当前大盘走势（上证、深证、创业板）
- 市场情绪（乐观/中性/悲观）
- 板块热点分析

### 二、基本面简析
- 当前价格位置分析
- 估值水平（PE、PB）
- 业绩情况（如有）

### 三、技术面分析
- 均线系统（多头/空头排列）
- MACD指标（方向、动能）
- KDJ指标（超买超卖）
- 布林带（当前位置）
- 成交量（放量/缩量）

### 四、资金流向
- 主力资金净流入/流出
- 资金动向判断

### 五、综合研判
基于以上分析，给出：
- **短期走势预测**（1-3天）：看涨/看跌/震荡
- **预测置信度**：高/中/低（给出理由）
- **关键支撑位**：元
- **关键压力位**：元

### 六、操作建议
| 操作 | 条件 |
|------|------|
| 买入 | 同时满足：缩量回调+技术支撑+资金流入 |
| 持有 | 趋势完好，持有为主 |
| 卖出 | 放量滞涨/跌破止损 |
| 观望 | 信号不明确 |

### 七、风险提示
- 明确说明可能的风险
- 建议止损位
- 仓位建议

## 输出要求
1. 用中文回答
2. 结构清晰，使用Markdown
3. 预测要有数据支撑
4. 置信度评估要诚实
5. 字数控制在400-600字

## 免责声明
以上分析仅供参考，不构成投资建议。股市有风险，投资需谨慎。"""
    
    def _build_analysis_prompt(self, stock_data: Dict[str, Any], market_data: Dict[str, Any] = None) -> str:
        """构建分析提示词"""
        
        # 基本行情
        prompt = f"""请分析以下股票：

## 股票基本信息
- 名称：{stock_data.get('name', '')}
- 代码：{stock_data.get('code', '')}
- 当前价格：{stock_data.get('price', 0):.2f} 元
- 涨跌幅：{stock_data.get('pct_change', 0):+.2f}%
- 涨跌额：{stock_data.get('change', 0):+.2f} 元
- 今日开盘：{stock_data.get('open', 0):.2f} 元
- 今日最高：{stock_data.get('high', 0):.2f} 元
- 今日最低：{stock_data.get('low', 0):.2f} 元
- 成交量：{stock_data.get('volume', 0):,} 手
- 成交额：{stock_data.get('amount', 0):,.2f} 万元
- 振幅：{stock_data.get('amplitude', 0):.2f}%

"""
        
        # 大盘指数
        if market_data:
            prompt += "## 大盘指数\n"
            for code, data in market_data.items():
                pct = data.get('pct_change', 0)
                emoji = "📈" if pct > 0 else "📉" if pct < 0 else "➡️"
                prompt += f"- {emoji} {data.get('name', code)}：{data.get('price', 0):.2f} ({pct:+.2f}%)\n"
            prompt += "\n"
        
        # 技术指标
        tech = stock_data.get('tech', {})
        if tech:
            prompt += "## 技术指标\n"
            prompt += f"- MA5：{tech.get('ma5', 0):.2f} 元\n"
            prompt += f"- MA10：{tech.get('ma10', 0):.2f} 元\n"
            prompt += f"- MA20：{tech.get('ma20', 0):.2f} 元\n"
            prompt += f"- MACD：{tech.get('macd', 0):.3f}，信号：{tech.get('macd_signal', '震荡')}\n"
            prompt += f"- KDJ：K={tech.get('kdj_k', 0):.2f} D={tech.get('kdj_d', 0):.2f} J={tech.get('kdj_j', 0):.2f}，信号：{tech.get('kdj_signal', '震荡')}\n"
            prompt += f"- RSI(14)：{tech.get('rsi', 0):.2f}，状态：{tech.get('rsi_signal', '正常')}\n"
            prompt += f"- 布林带：上轨{tech.get('boll_upper', 0):.2f}，中轨{tech.get('boll_middle', 0):.2f}，下轨{tech.get('boll_lower', 0):.2f}\n"
            prompt += f"- 成交量：较5日均量{tech.get('volume_ratio', 1):.2f}倍，状态：{tech.get('volume_signal', '正常')}\n"
            prompt += "\n"
        
        # 资金流向
        money_flow = stock_data.get('money_flow', {})
        if money_flow:
            prompt += "## 资金流向\n"
            main_inflow = money_flow.get('main_net_inflow', 0)
            main_pct = money_flow.get('main_net_inflow_pct', 0)
            if main_inflow > 0:
                prompt += f"- 主力净流入：+{main_inflow/1e8:.2f} 亿（占比{abs(main_pct):.1f}%）✅\n"
            else:
                prompt += f"- 主力净流出：{main_inflow/1e8:.2f} 亿（占比{abs(main_pct):.1f}%）⚠️\n"
            prompt += "\n"
        
        prompt += """请按照分析框架进行全面分析，给出专业、客观的研判。"""
        
        return prompt


class StockAnalyzer:
    """股票分析器 - 升级版"""
    
    def __init__(self, data_loader, ai_engine, config):
        self.data_loader = data_loader
        self.ai_engine = ai_engine
        self.config = config
    
    def analyze_single_stock(self, symbol: str) -> Dict[str, Any]:
        """分析单个股票"""
        logger.info(f"📈 分析股票: {symbol}")
        
        # 获取实时数据
        data = self.data_loader.get_realtime_data(symbol)
        if not data:
            return {"error": "获取数据失败", "code": symbol}
        
        # 获取K线数据和技术指标
        kline = self.data_loader.get_kline_data(symbol, count=60)
        tech = self.data_loader.calculate_technical_indicators(kline)
        data['tech'] = tech
        
        # 获取资金流向
        money_flow = self.data_loader.get_money_flow(symbol)
        data['money_flow'] = money_flow
        
        # 获取大盘数据
        market_data = self.data_loader.get_market_index()
        
        # AI分析
        ai_analysis = None
        if self.config.runtime.report_type != "simple":
            ai_analysis = self.ai_engine.analyze_stock(data, market_data)
        
        return {
            "code": symbol,
            "name": data.get("name", symbol),
            "data": data,
            "market": market_data,
            "tech": tech,
            "money_flow": money_flow,
            "ai_analysis": ai_analysis,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def analyze_stocks(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """批量分析股票"""
        results = []
        
        for i, symbol in enumerate(symbols):
            if i > 0 and self.config.runtime.analysis_delay > 0:
                time.sleep(self.config.runtime.analysis_delay)
            
            try:
                result = self.analyze_single_stock(symbol)
                results.append(result)
            except Exception as e:
                logger.error(f"❌ 分析 {symbol} 失败: {e}")
                results.append({"error": str(e), "code": symbol})
        
        return results
    
    def select_and_analyze(self, count: int = 8) -> List[Dict[str, Any]]:
        """
        精选股票并分析
        这是升级版的核心功能
        """
        logger.info(f"🎯 开始精选+分析 {count} 只股票...")
        
        # 精选股票
        top_stocks = self.data_loader.select_top_stocks(count=count)
        
        if not top_stocks:
            logger.error("❌ 精选失败")
            return []
        
        # 获取大盘数据
        market_data = self.data_loader.get_market_index()
        
        # AI分析每只股票
        results = []
        for i, stock in enumerate(top_stocks):
            logger.info(f"📈 分析精选股票 {i+1}/{len(top_stocks)}: {stock.get('name')}")
            
            try:
                # 获取资金流向
                money_flow = self.data_loader.get_money_flow(stock['code'])
                stock['money_flow'] = money_flow
                
                # AI分析
                ai_analysis = None
                if self.config.runtime.report_type != "simple":
                    ai_analysis = self.ai_engine.analyze_stock(stock, market_data)
                
                result = {
                    "code": stock['code'],
                    "name": stock['name'],
                    "data": stock,
                    "market": market_data,
                    "tech": stock.get('tech', {}),
                    "money_flow": money_flow,
                    "ai_analysis": ai_analysis,
                    "score": stock.get('score', 0),
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                results.append(result)
                
                time.sleep(1)  # 避免请求过快
                
            except Exception as e:
                logger.error(f"❌ 分析 {stock.get('code')} 失败: {e}")
                continue
        
        logger.info(f"✅ 精选分析完成，共 {len(results)} 只")
        return results
