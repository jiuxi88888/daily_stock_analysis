"""
配置管理模块 - 升级版
"""

import os
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any
from enum import Enum


class ReportType(str, Enum):
    """报告类型枚举"""
    SIMPLE = "simple"      # 简洁报告
    DETAIL = "detail"     # 详细报告
    CONCISE = "concise"    # 精简报告


@dataclass
class AIConfig:
    """AI 配置"""
    api_key: str = ""
    base_url: str = "https://api.bianxie.ai/v1"
    model: str = "gpt-4o"
    
    # AI参数配置
    temperature: float = 0.7
    max_tokens: int = 1000
    timeout: int = 30
    request_delay: float = 2.0


@dataclass
class DataSourceConfig:
    """数据源配置"""
    tushare_token: str = ""
    
    realtime_source_priority: List[str] = field(default_factory=lambda: [
        "tencent",
        "akshare_sina",
        "efinance"
    ])


@dataclass
class NotificationConfig:
    """通知配置"""
    pushplus_token: str = ""
    wechat_webhook_url: str = ""
    wechat_msg_type: str = "markdown"


@dataclass
class RuntimeConfig:
    """运行配置"""
    stock_list: List[str] = field(default_factory=lambda: ["600519", "000001"])
    report_type: ReportType = ReportType.SIMPLE
    
    market_review_enabled: bool = True
    single_stock_notify: bool = False
    analysis_delay: float = 1.0
    
    # 精选功能配置
    enable_selection: bool = True
    selection_count: int = 8
    
    log_level: str = "INFO"
    max_workers: int = 1


@dataclass
class Config:
    """主配置类"""
    ai: AIConfig = field(default_factory=AIConfig)
    data_source: DataSourceConfig = field(default_factory=DataSourceConfig)
    notification: NotificationConfig = field(default_factory=NotificationConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    
    @classmethod
    def load(cls) -> 'Config':
        """从环境变量加载配置"""
        config = cls()
        
        # AI 配置
        config.ai.api_key = os.getenv('OPENAI_API_KEY', '')
        config.ai.base_url = os.getenv('OPENAI_BASE_URL', 'https://api.bianxie.ai/v1')
        config.ai.model = os.getenv('AI_MODEL', 'gpt-4o')
        config.ai.temperature = float(os.getenv('AI_TEMPERATURE', '0.7'))
        config.ai.max_tokens = int(os.getenv('AI_MAX_TOKENS', '1000'))
        config.ai.timeout = int(os.getenv('AI_TIMEOUT', '30'))
        config.ai.request_delay = float(os.getenv('AI_REQUEST_DELAY', '2.0'))
        
        # 数据源配置
        config.data_source.tushare_token = os.getenv('TUSHARE_TOKEN', '')
        priority_str = os.getenv('REALTIME_SOURCE_PRIORITY', 'tencent,akshare_sina,efinance')
        config.data_source.realtime_source_priority = [
            s.strip() for s in priority_str.split(',') if s.strip()
        ]
        
        # 通知配置
        config.notification.pushplus_token = os.getenv('PUSHPLUS_TOKEN', '')
        config.notification.wechat_webhook_url = os.getenv('WECHAT_WEBHOOK_URL', '')
        config.notification.wechat_msg_type = os.getenv('WECHAT_MSG_TYPE', 'markdown')
        
        # 运行配置
        stock_str = os.getenv('STOCK_LIST', '600519,000001')
        config.runtime.stock_list = [
            s.strip() for s in stock_str.split(',') if s.strip()
        ]
        
        report_type_str = os.getenv('REPORT_TYPE', 'simple')
        try:
            config.runtime.report_type = ReportType(report_type_str)
        except ValueError:
            config.runtime.report_type = ReportType.SIMPLE
        
        config.runtime.market_review_enabled = (
            os.getenv('MARKET_REVIEW_ENABLED', 'true').lower() == 'true'
        )
        config.runtime.single_stock_notify = (
            os.getenv('SINGLE_STOCK_NOTIFY', 'false').lower() == 'true'
        )
        config.runtime.analysis_delay = float(os.getenv('ANALYSIS_DELAY', '1.0'))
        
        # 精选功能配置
        config.runtime.enable_selection = os.getenv('ENABLE_SELECTION', 'true').lower() == 'true'
        config.runtime.selection_count = int(os.getenv('SELECTION_COUNT', '8'))
        
        config.runtime.log_level = os.getenv('LOG_LEVEL', 'INFO')
        config.runtime.max_workers = int(os.getenv('MAX_WORKERS', '1'))
        
        return config
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        
        if not self.data_source.tushare_token:
            errors.append("❌ TUSHARE_TOKEN 未配置")
        
        if not self.ai.api_key:
            errors.append("❌ OPENAI_API_KEY 未配置")
        
        if not self.notification.pushplus_token and not self.notification.wechat_webhook_url:
            errors.append("⚠️ 至少配置一个通知渠道")
        
        return errors
