"""
工具函数模块
"""
import logging
import json
import yaml
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
import time
import random
import re

logger = logging.getLogger(__name__)

def setup_logging(log_level: str = "INFO", log_file: str = None) -> logging.Logger:
    """设置日志配置"""
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 创建根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # 清除现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 添加文件处理器
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    return root_logger

def format_number(num: Union[int, float]) -> str:
    """格式化数字"""
    if isinstance(num, (int, np.integer)):
        if abs(num) >= 1_0000_0000:  # 亿
            return f"{num/1_0000_0000:.2f}亿"
        elif abs(num) >= 1_0000:  # 万
            return f"{num/1_0000:.2f}万"
        else:
            return f"{num:,}"
    elif isinstance(num, float):
        return f"{num:.2f}"
    else:
        return str(num)

def format_percentage(value: float) -> str:
    """格式化百分比"""
    return f"{value:+.2f}%"

def format_price(price: float) -> str:
    """格式化价格"""
    return f"¥{price:.2f}"

def format_time(timestamp: Union[str, datetime]) -> str:
    """格式化时间"""
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except:
            return timestamp
    
    if isinstance(timestamp, datetime):
        return timestamp.strftime('%Y-%m-%d %H:%M:%S')
    
    return str(timestamp)

def calculate_change(current: float, previous: float) -> Dict[str, Any]:
    """计算涨跌幅"""
    if previous == 0:
        return {"change": 0, "pct_change": 0}
    
    change = current - previous
    pct_change = (change / previous) * 100
    
    return {
        "change": change,
        "pct_change": pct_change
    }

def is_trading_time() -> bool:
    """判断是否为交易时间"""
    now = datetime.now()
    
    # 检查是否为交易日（周一至周五）
    if now.weekday() >= 5:  # 5=周六, 6=周日
        return False
    
    # 检查时间（假设交易时间为 9:30-15:00）
    current_time = now.time()
    morning_start = datetime.strptime("09:30", "%H:%M").time()
    morning_end = datetime.strptime("11:30", "%H:%M").time()
    afternoon_start = datetime.strptime("13:00", "%H:%M").time()
    afternoon_end = datetime.strptime("15:00", "%H:%M").time()
    
    return (morning_start <= current_time <= morning_end) or \
           (afternoon_start <= current_time <= afternoon_end)

def get_trading_date(offset: int = 0) -> str:
    """获取交易日（支持偏移）"""
    today = datetime.now()
    
    # 简单实现，实际应该考虑节假日
    target_date = today + timedelta(days=offset)
    
    # 如果不是交易日，调整到前一个交易日
    while target_date.weekday() >= 5:  # 周六或周日
        target_date -= timedelta(days=1)
    
    return target_date.strftime("%Y%m%d")

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """安全除法"""
    if denominator == 0:
        return default
    return numerator / denominator

def validate_stock_code(code: str) -> bool:
    """验证股票代码格式"""
    pattern = r'^(600|601|603|605|688|900|000|002|300|200|730|700|080|031)\d{3}$'
    return bool(re.match(pattern, code))

def retry_on_error(max_retries: int = 3, delay: float = 1.0, 
                   exceptions: tuple = (Exception,)):
    """重试装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        sleep_time = delay * (2 ** attempt) + random.random() * 0.5
                        logger.warning(f"⚠️  {func.__name__} 执行失败，{sleep_time:.1f}秒后重试 ({attempt + 1}/{max_retries}): {e}")
                        time.sleep(sleep_time)
                    else:
                        logger.error(f"❌ {func.__name__} 重试{max_retries}次后失败: {e}")
            raise last_exception
        return wrapper
    return decorator

def export_to_json(data: Any, filename: str) -> bool:
    """导出数据到JSON文件"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            # 处理datetime对象
            def json_serializer(obj):
                if isinstance(obj, (datetime, pd.Timestamp)):
                    return obj.isoformat()
                elif isinstance(obj, pd.DataFrame):
                    return obj.to_dict(orient='records')
                elif isinstance(obj, pd.Series):
                    return obj.to_dict()
                elif isinstance(obj, np.integer):
                    return int(obj)
                elif isinstance(obj, np.floating):
                    return float(obj)
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                raise TypeError(f"Type {type(obj)} not serializable")
            
            json.dump(data, f, ensure_ascii=False, indent=2, default=json_serializer)
        logger.info(f"✅ 数据已导出到: {filename}")
        return True
    except Exception as e:
        logger.error(f"❌ 导出数据失败: {e}")
        return False

def export_to_csv(data: pd.DataFrame, filename: str) -> bool:
    """导出数据到CSV文件"""
    try:
        data.to_csv(filename, index=False, encoding='utf-8-sig')
        logger.info(f"✅ 数据已导出到: {filename}")
        return True
    except Exception as e:
        logger.error(f"❌ 导出CSV失败: {e}")
        return False

def load_config_file(filename: str) -> Dict[str, Any]:
    """加载配置文件"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            if filename.endswith('.json'):
                return json.load(f)
            elif filename.endswith(('.yaml', '.yml')):
                return yaml.safe_load(f)
            else:
                logger.error(f"❌ 不支持的配置文件格式: {filename}")
                return {}
    except Exception as e:
        logger.error(f"❌ 加载配置文件失败: {e}")
        return {}

def save_config_file(data: Dict[str, Any], filename: str) -> bool:
    """保存配置文件"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            if filename.endswith('.json'):
                json.dump(data, f, ensure_ascii=False, indent=2)
            elif filename.endswith(('.yaml', '.yml')):
                yaml.dump(data, f, allow_unicode=True, indent=2)
            else:
                logger.error(f"❌ 不支持的配置文件格式: {filename}")
                return False
        logger.info(f"✅ 配置已保存到: {filename}")
        return True
    except Exception as e:
        logger.error(f"❌ 保存配置文件失败: {e}")
        return False

def format_market_data(market_data: Dict[str, Any]) -> str:
    """格式化市场数据"""
    lines = ["📊 **大盘指数概览**"]
    for code, data in market_data.items():
        pct_change = data.get('pct_change', 0)
        if pct_change > 0:
            emoji = "📈"
        elif pct_change < 0:
            emoji = "📉"
        else:
            emoji = "➡️"
        
        lines.append(f"{emoji} **{data.get('name', code)}**: {data.get('price', 0):.2f} ({pct_change:+.2f}%)")
    
    return "\n".join(lines)

def format_stock_analysis(stock_data: Dict[str, Any]) -> str:
    """格式化股票分析结果"""
    lines = []
    
    # 基本信息
    realtime = stock_data.get('realtime', {})
    lines.append(f"**{realtime.get('name', 'N/A')} ({realtime.get('code', 'N/A')})**")
    lines.append(f"当前价格: {format_price(realtime.get('price', 0))}")
    
    pct_change = realtime.get('pct_change', 0)
    if pct_change > 0:
        change_str = f"📈 +{pct_change:.2f}%"
    elif pct_change < 0:
        change_str = f"📉 {pct_change:.2f}%"
    else:
        change_str = "➡️ 0.00%"
    
    lines.append(f"涨跌幅: {change_str}")
    lines.append(f"成交量: {format_number(realtime.get('volume', 0))}手")
    lines.append(f"成交额: {format_number(realtime.get('amount', 0))}元")
    
    # 技术指标
    technical = stock_data.get('technical', {})
    if technical:
        lines.append("\n**技术指标**")
        
        if 'ma' in technical and technical['ma']:
            ma_str = " | ".join([f"MA{period}: {price:.2f}" for period, price in technical['ma'].items()])
            lines.append(f"移动平均线: {ma_str}")
            
        if 'macd' in technical and technical['macd']:
            macd_data = technical['macd']
            lines.append(f"MACD: DIF={macd_data.get('dif', 0):.3f}, DEA={macd_data.get('dea', 0):.3f} ({macd_data.get('signal', '')})")
            
        if 'rsi' in technical and technical['rsi'] is not None:
            rsi_value = technical['rsi']
            rsi_status = "超买" if rsi_value > 70 else "超卖" if rsi_value < 30 else "正常"
            lines.append(f"RSI: {rsi_value:.1f} ({rsi_status})")
            
        if 'boll' in technical and technical['boll']:
            boll_data = technical['boll']
            lines.append(f"布林带: 上轨={boll_data.get('upper', 0):.2f}, 中轨={boll_data.get('middle', 0):.2f}, 下轨={boll_data.get('lower', 0):.2f}")
            lines.append(f"位置: {boll_data.get('position', 0)*100:.1f}% ({boll_data.get('signal', '')})")
    
    # AI分析摘要
    if 'ai_analysis' in stock_data and stock_data['ai_analysis']:
        lines.append(f"\n**AI分析摘要**: {stock_data['ai_analysis'][:100]}...")
    
    return "\n".join(lines)
