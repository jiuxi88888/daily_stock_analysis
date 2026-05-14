"""
工具函数模块
"""
import logging
import json
from datetime import datetime
from typing import Any, Dict, List

def setup_logging(log_level: str = "INFO"):
    """设置日志配置"""
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def format_number(num: int) -> str:
    """格式化数字"""
    if num >= 100000000:
        return f"{num/100000000:.2f}亿"
    elif num >= 10000:
        return f"{num/10000:.2f}万"
    else:
        return f"{num:,}"

def format_price(price: float) -> str:
    """格式化价格"""
    return f"¥{price:.2f}"

def create_report(stock_results: List[Dict[str, Any]], market_data: Dict[str, Any] = None) -> str:
    """创建分析报告"""
    report_date = datetime.now().strftime("%Y-%m-%d")
    
    content = f"# 📈 股票分析报告 {report_date}\n\n"
    content += f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    if market_data:
        content += "## 📊 大盘概览\n\n"
        for code, data in market_data.items():
            pct = data.get('pct_change', 0)
            emoji = "📈" if pct > 0 else "📉" if pct < 0 else "➡️"
            content += f"{emoji} **{data.get('name', code)}**: {data.get('price', 0):.2f} ({pct:+.2f}%)\n"
        content += "\n"
    
    content += "## 📈 个股分析\n\n"
    
    for result in stock_results:
        if 'error' in result:
            content += f"### ❌ {result.get('code')} - 分析失败\n"
            content += f"错误: {result.get('error')}\n\n"
        else:
            data = result.get('data', {})
            pct = data.get('pct_change', 0)
            emoji = "📈" if pct > 0 else "📉" if pct < 0 else "➡️"
            
            content += f"### {emoji} {result.get('name')} ({result.get('code')})\n\n"
            content += f"- **价格**: {format_price(data.get('price', 0))}\n"
            content += f"- **涨跌幅**: {pct:+.2f}%\n"
            content += f"- **成交量**: {format_number(data.get('volume', 0))}手\n"
            content += f"- **成交额**: ¥{data.get('amount', 0):,.2f}\n"
            content += f"- **更新时间**: {data.get('time', '')}\n\n"
            
            if result.get('ai_analysis'):
                content += f"**🤖 AI分析**:\n{result.get('ai_analysis')}\n\n"
            
            content += "---\n\n"
    
    return content
