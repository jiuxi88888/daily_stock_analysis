"""
配置管理模块
"""
import os
import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

class ReportType(str, Enum):
    SIMPLE = "simple"
    DETAIL = "detail"
    CONCISE = "concise"

@dataclass
class AIConfig:
    """AI 配置"""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3-flash-preview"
    gemini_model_fallback: str = "gemini-2.5-flash"
    gemini_request_delay: float = 3.0
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = ""

@dataclass
class DataSourceConfig:
    """数据源配置"""
    tushare_token: str = ""
    realtime_source_priority: List[str] = field(default_factory=lambda: [
        "tencent", "akshare_sina", "efinance", "akshare_em"
    ])
    enable_chip_distribution: bool = False

@dataclass
class SearchConfig:
    """搜索配置"""
    bocha_api_keys: List[str] = field(default_factory=list)
    tavily_api_keys: List[str] = field(default_factory=list)
    serpapi_api_keys: List[str] = field(default_factory=list)

@dataclass
class NotificationConfig:
    """通知配置"""
    wechat_webhook_url: str = ""
    wechat_msg_type: str = "markdown"
    feishu_webhook_url: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_message_thread_id: str = ""
    email_sender: str = ""
    email_password: str = ""
    email_receivers: List[str] = field(default_factory=list)
    email_sender_name: str = "股票分析助手"
    pushover_user_key: str = ""
    pushover_api_token: str = ""
    pushplus_token: str = ""
    custom_webhook_urls: List[str] = field(default_factory=list)
    custom_webhook_bearer_token: str = ""
    discord_webhook_url: str = ""
    discord_bot_token: str = ""
    discord_main_channel_id: str = ""
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_folder_token: str = ""
    astrbot_url: str = ""
    astrbot_token: str = ""
    serverchan3_sendkey: str = ""

@dataclass
class RuntimeConfig:
    """运行配置"""
    stock_list: List[str] = field(default_factory=lambda: ["600519"])
    report_type: ReportType = ReportType.SIMPLE
    single_stock_notify: bool = False
    market_review_enabled: bool = True
    analysis_delay: float = 0
    max_workers: int = 1
    log_level: str = "INFO"

@dataclass
class Config:
    """主配置类"""
    ai: AIConfig = field(default_factory=AIConfig)
    data_source: DataSourceConfig = field(default_factory=DataSourceConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    notification: NotificationConfig = field(default_factory=NotificationConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    
    @classmethod
    def load(cls) -> 'Config':
        """从环境变量加载配置"""
        config = cls()
        
        # AI 配置
        config.ai.gemini_api_key = os.getenv('GEMINI_API_KEY', '')
        config.ai.gemini_model = os.getenv('GEMINI_MODEL', 'gemini-3-flash-preview')
        config.ai.gemini_model_fallback = os.getenv('GEMINI_MODEL_FALLBACK', 'gemini-2.5-flash')
        config.ai.gemini_request_delay = float(os.getenv('GEMINI_REQUEST_DELAY', '3.0'))
        config.ai.openai_api_key = os.getenv('OPENAI_API_KEY', '')
        config.ai.openai_base_url = os.getenv('OPENAI_BASE_URL', '')
        config.ai.openai_model = os.getenv('OPENAI_MODEL', '')
        
        # 数据源配置
        config.data_source.tushare_token = os.getenv('TUSHARE_TOKEN', '')
        priority_str = os.getenv('REALTIME_SOURCE_PRIORITY', 'tencent,akshare_sina,efinance,akshare_em')
        config.data_source.realtime_source_priority = [s.strip() for s in priority_str.split(',') if s.strip()]
        config.data_source.enable_chip_distribution = os.getenv('ENABLE_CHIP_DISTRIBUTION', 'false').lower() == 'true'
        
        # 搜索配置
        if bocha_keys := os.getenv('BOCHA_API_KEYS', ''):
            config.search.bocha_api_keys = [k.strip() for k in bocha_keys.split(',') if k.strip()]
        if tavily_keys := os.getenv('TAVILY_API_KEYS', ''):
            config.search.tavily_api_keys = [k.strip() for k in tavily_keys.split(',') if k.strip()]
        if serpapi_keys := os.getenv('SERPAPI_API_KEYS', ''):
            config.search.serpapi_api_keys = [k.strip() for k in serpapi_keys.split(',') if k.strip()]
        
        # 通知配置
        config.notification.wechat_webhook_url = os.getenv('WECHAT_WEBHOOK_URL', '')
        config.notification.wechat_msg_type = os.getenv('WECHAT_MSG_TYPE', 'markdown')
        config.notification.feishu_webhook_url = os.getenv('FEISHU_WEBHOOK_URL', '')
        config.notification.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        config.notification.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        config.notification.telegram_message_thread_id = os.getenv('TELEGRAM_MESSAGE_THREAD_ID', '')
        config.notification.email_sender = os.getenv('EMAIL_SENDER', '')
        config.notification.email_password = os.getenv('EMAIL_PASSWORD', '')
        if email_receivers := os.getenv('EMAIL_RECEIVERS', ''):
            config.notification.email_receivers = [e.strip() for e in email_receivers.split(',') if e.strip()]
        config.notification.email_sender_name = os.getenv('EMAIL_SENDER_NAME', '股票分析助手')
        config.notification.pushover_user_key = os.getenv('PUSHOVER_USER_KEY', '')
        config.notification.pushover_api_token = os.getenv('PUSHOVER_API_TOKEN', '')
        config.notification.pushplus_token = os.getenv('PUSHPLUS_TOKEN', '')
        if custom_urls := os.getenv('CUSTOM_WEBHOOK_URLS', ''):
            config.notification.custom_webhook_urls = [u.strip() for u in custom_urls.split(',') if u.strip()]
        config.notification.custom_webhook_bearer_token = os.getenv('CUSTOM_WEBHOOK_BEARER_TOKEN', '')
        config.notification.discord_webhook_url = os.getenv('DISCORD_WEBHOOK_URL', '')
        config.notification.discord_bot_token = os.getenv('DISCORD_BOT_TOKEN', '')
        config.notification.discord_main_channel_id = os.getenv('DISCORD_MAIN_CHANNEL_ID', '')
        config.notification.feishu_app_id = os.getenv('FEISHU_APP_ID', '')
        config.notification.feishu_app_secret = os.getenv('FEISHU_APP_SECRET', '')
        config.notification.feishu_folder_token = os.getenv('FEISHU_FOLDER_TOKEN', '')
        config.notification.astrbot_url = os.getenv('ASTRBOT_URL', '')
        config.notification.astrbot_token = os.getenv('ASTRBOT_TOKEN', '')
        config.notification.serverchan3_sendkey = os.getenv('SERVERCHAN3_SENDKEY', '')
        
        # 运行配置
        stock_str = os.getenv('STOCK_LIST', '600519')
        config.runtime.stock_list = [s.strip() for s in stock_str.split(',') if s.strip()]
        config.runtime.report_type = ReportType(os.getenv('REPORT_TYPE', 'simple'))
        config.runtime.single_stock_notify = os.getenv('SINGLE_STOCK_NOTIFY', 'false').lower() == 'true'
        config.runtime.market_review_enabled = os.getenv('MARKET_REVIEW_ENABLED', 'true').lower() == 'true'
        config.runtime.analysis_delay = float(os.getenv('ANALYSIS_DELAY', '0'))
        config.runtime.max_workers = int(os.getenv('MAX_WORKERS', '1'))
        config.runtime.log_level = os.getenv('LOG_LEVEL', 'INFO')
        
        return config
    
    def validate(self) -> List[str]:
        """验证配置，返回错误列表"""
        errors = []
        
        # 检查必需配置
        if not self.data_source.tushare_token:
            errors.append("TUSHARE_TOKEN 未配置")
            
        # 检查AI配置
        if not self.ai.gemini_api_key and not self.ai.openai_api_key:
            errors.append("GEMINI_API_KEY 或 OPENAI_API_KEY 至少需要配置一个")
            
        # 检查通知配置
        notification_methods = [
            bool(self.notification.wechat_webhook_url),
            bool(self.notification.feishu_webhook_url),
            bool(self.notification.telegram_bot_token and self.notification.telegram_chat_id),
            bool(self.notification.email_sender and self.notification.email_password and self.notification.email_receivers),
            bool(self.notification.pushover_user_key and self.notification.pushover_api_token),
            bool(self.notification.pushplus_token),
            bool(self.notification.discord_webhook_url),
            bool(self.notification.astrbot_url and self.notification.astrbot_token),
            bool(self.notification.serverchan3_sendkey),
        ]
        
        if not any(notification_methods):
            errors.append("至少需要配置一个通知渠道")
            
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于日志）"""
        config_dict = {
            "ai": {
                "gemini_api_key": "***" if self.ai.gemini_api_key else "",
                "gemini_model": self.ai.gemini_model,
                "openai_api_key": "***" if self.ai.openai_api_key else "",
            },
            "data_source": {
                "tushare_token": "***" if self.data_source.tushare_token else "",
                "realtime_sources": self.data_source.realtime_source_priority,
            },
            "runtime": {
                "stock_list": self.runtime.stock_list,
                "report_type": self.runtime.report_type.value,
                "market_review_enabled": self.runtime.market_review_enabled,
            }
        }
        return config_dict
