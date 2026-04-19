"""
配置管理模块 - 适配便携AI版本
"""
import os
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any
from enum import Enum

class ReportType(str, Enum):
    """报告类型枚举"""
    SIMPLE = "simple"    # 简洁报告
    DETAIL = "detail"    # 详细报告
    CONCISE = "concise"  # 精简报告

@dataclass
class AIConfig:
    """AI 配置 - 适配便携AI"""
    # 便携AI使用OpenAI兼容接口
    api_key: str = ""  # 便携AI的sk-xxx密钥
    base_url: str = "https://api.bianxie.ai/v1"  # 便携AI接口地址
    model: str = "gpt-4"  # 便携AI支持的模型
    
    # AI参数配置
    temperature: float = 0.7
    max_tokens: int = 1000
    timeout: int = 30
    request_delay: float = 2.0  # 请求延迟

@dataclass
class DataSourceConfig:
    """数据源配置"""
    tushare_token: str = ""  # Tushare Pro令牌
    
    # 实时数据源优先级
    realtime_source_priority: List[str] = field(default_factory=lambda: [
        "tencent",      # 腾讯财经
        "akshare_sina", # 新浪财经
        "efinance"      # 东方财富
    ])

@dataclass
class NotificationConfig:
    """通知配置"""
    pushplus_token: str = ""  # PushPlus令牌
    wechat_webhook_url: str = ""  # 企业微信Webhook
    wechat_msg_type: str = "markdown"  # 消息类型

@dataclass
class RuntimeConfig:
    """运行配置"""
    # 自选股列表
    stock_list: List[str] = field(default_factory=lambda: ["600519", "000001"])
    
    # 报告类型
    report_type: ReportType = ReportType.SIMPLE
    
    # 功能开关
    market_review_enabled: bool = True  # 是否分析大盘
    single_stock_notify: bool = False   # 单只股票通知
    analysis_delay: float = 1.0         # 分析延迟（秒）
    
    # 系统配置
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
        
        # ========== AI 配置 ==========
        config.ai.api_key = os.getenv('OPENAI_API_KEY', '')
        config.ai.base_url = os.getenv('OPENAI_BASE_URL', 'https://api.bianxie.ai/v1')
        config.ai.model = os.getenv('AI_MODEL', 'gpt-4')
        config.ai.temperature = float(os.getenv('AI_TEMPERATURE', '0.7'))
        config.ai.max_tokens = int(os.getenv('AI_MAX_TOKENS', '1000'))
        config.ai.timeout = int(os.getenv('AI_TIMEOUT', '30'))
        config.ai.request_delay = float(os.getenv('AI_REQUEST_DELAY', '2.0'))
        
        # ========== 数据源配置 ==========
        config.data_source.tushare_token = os.getenv('TUSHARE_TOKEN', '')
        
        priority_str = os.getenv('REALTIME_SOURCE_PRIORITY', 'tencent,akshare_sina,efinance')
        config.data_source.realtime_source_priority = [
            s.strip() for s in priority_str.split(',') if s.strip()
        ]
        
        # ========== 通知配置 ==========
        config.notification.pushplus_token = os.getenv('PUSHPLUS_TOKEN', '')
        config.notification.wechat_webhook_url = os.getenv('WECHAT_WEBHOOK_URL', '')
        config.notification.wechat_msg_type = os.getenv('WECHAT_MSG_TYPE', 'markdown')
        
        # ========== 运行配置 ==========
        # 股票列表
        stock_str = os.getenv('STOCK_LIST', '600519,000001')
        config.runtime.stock_list = [
            s.strip() for s in stock_str.split(',') if s.strip()
        ]
        
        # 报告类型
        report_type_str = os.getenv('REPORT_TYPE', 'simple')
        try:
            config.runtime.report_type = ReportType(report_type_str)
        except ValueError:
            config.runtime.report_type = ReportType.SIMPLE
        
        # 功能开关
        config.runtime.market_review_enabled = (
            os.getenv('MARKET_REVIEW_ENABLED', 'true').lower() == 'true'
        )
        config.runtime.single_stock_notify = (
            os.getenv('SINGLE_STOCK_NOTIFY', 'false').lower() == 'true'
        )
        config.runtime.analysis_delay = float(os.getenv('ANALYSIS_DELAY', '1.0'))
        
        # 系统配置
        config.runtime.log_level = os.getenv('LOG_LEVEL', 'INFO')
        config.runtime.max_workers = int(os.getenv('MAX_WORKERS', '1'))
        
        return config
    
    def validate(self) -> List[str]:
        """验证配置，返回错误列表"""
        errors = []
        
        # 检查必需配置
        if not self.data_source.tushare_token:
            errors.append("❌ TUSHARE_TOKEN 未配置")
            
        if not self.ai.api_key:
            errors.append("❌ OPENAI_API_KEY 未配置（便携AI密钥）")
            
        # 检查通知配置
        if not self.notification.pushplus_token and not self.notification.wechat_webhook_url:
            errors.append("⚠️  至少配置一个通知渠道 (PUSHPLUS_TOKEN 或 WECHAT_WEBHOOK_URL)")
            
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于日志）"""
        return {
            "ai": {
                "model": self.ai.model,
                "base_url": self.ai.base_url,
                "api_key": "***" if self.ai.api_key else ""
            },
            "data_source": {
                "tushare_token": "***" if self.data_source.tushare_token else "",
                "sources": self.data_source.realtime_source_priority
            },
            "runtime": {
                "stock_list": self.runtime.stock_list,
                "report_type": self.runtime.report_type.value,
                "market_review": self.runtime.market_review_enabled
            }
        }
    
    def log_config(self, logger: logging.Logger):
        """记录配置信息"""
        config_dict = self.to_dict()
        
        logger.info("📋 当前配置:")
        logger.info(f"  📈 分析股票: {', '.join(self.runtime.stock_list)}")
        logger.info(f"  🤖 AI模型: {self.ai.model}")
        logger.info(f"  🔗 AI接口: {self.ai.base_url}")
        logger.info(f"  📊 数据源: {', '.join(self.data_source.realtime_source_priority)}")
        logger.info(f"  📝 报告类型: {self.runtime.report_type.value}")
        
        # 检查通知配置
        if self.notification.pushplus_token:
            logger.info("  📱 通知: PushPlus ✓")
        if self.notification.wechat_webhook_url:
            logger.info("  💬 通知: 企业微信 ✓")
