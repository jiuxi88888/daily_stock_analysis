# -*- coding: utf-8 -*-
"""
===================================
A股自选股智能分析系统 - 配置管理模块
==================================
"""

import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv, dotenv_values
from dataclasses import dataclass, field


def setup_env(override: bool = False):
    env_file = os.getenv("ENV_FILE")
    if env_file:
        env_path = Path(env_file)
    else:
        env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(dotenv_path=env_path, override=override)


# ================= 股票代码标准化 =================
def normalize_stock_code(code: str) -> str:
    code = str(code).strip()
    if code.endswith((".SH", ".SZ")):
        return code
    if code.startswith("6"):
        return f"{code}.SH"
    elif code.startswith(("0", "3")):
        return f"{code}.SZ"
    return code


def normalize_stock_list(raw_list: list) -> list:
    return [normalize_stock_code(c) for c in raw_list]


@dataclass
class Config:
    # === 自选股配置 ===
    stock_list: List[str] = field(default_factory=list)

    # === 数据源 ===
    tushare_token: Optional[str] = None

    # === AI 分析 ===
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.7

    # === 通知 ===
    pushplus_token: Optional[str] = None
    wechat_webhook_url: Optional[str] = None
    feishu_webhook_url: Optional[str] = None

    # === ✅ 精选功能（已开启） ===
    enable_selection: bool = True   # ✅ 打开精选
    selection_count: int = 3        # ✅ 只选 3 只

    # === 系统 ===
    max_workers: int = 3
    log_dir: str = "./logs"
    log_level: str = "INFO"

    # === 单例 ===
    _instance: Optional['Config'] = None

    @classmethod
    def get_instance(cls) -> 'Config':
        if cls._instance is None:
            cls._instance = cls._load_from_env()
        return cls._instance

    @classmethod
    def _load_from_env(cls) -> 'Config':
        setup_env()

        # === 自选股（自动补 .SH/.SZ）===
        stock_list_str = os.getenv('STOCK_LIST', '')
        raw_stock_list = [
            c.strip() for c in stock_list_str.split(',') if c.strip()
        ]
        if not raw_stock_list:
            raw_stock_list = ['600519', '000001', '300750']

        stock_list = normalize_stock_list(raw_stock_list)

        return cls(
            stock_list=stock_list,
            tushare_token=os.getenv('TUSHARE_TOKEN'),
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            openai_base_url=os.getenv('OPENAI_BASE_URL'),
            openai_model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
            openai_temperature=float(os.getenv('OPENAI_TEMPERATURE', '0.7')),
            pushplus_token=os.getenv('PUSHPLUS_TOKEN'),
            wechat_webhook_url=os.getenv('WECHAT_WEBHOOK_URL'),
            feishu_webhook_url=os.getenv('FEISHU_WEBHOOK_URL'),
            enable_selection=os.getenv('ENABLE_SELECTION', 'true').lower() == 'true',
            selection_count=int(os.getenv('SELECTION_COUNT', '3')),
            max_workers=int(os.getenv('MAX_WORKERS', '3')),
        )

    def validate(self) -> List[str]:
        warnings = []
        if not self.stock_list:
            warnings.append("⚠️ 未配置自选股")
        if not self.tushare_token:
            warnings.append("⚠️ 未配置 Tushare Token")
        if not self.openai_api_key:
            warnings.append("⚠️ 未配置 OpenAI API Key")
        return warnings


# === 快捷访问 ===
def get_config() -> Config:
    return Config.get_instance()


if __name__ == "__main__":
    cfg = get_config()
    print("✅ 自选股:", cfg.stock_list)
    print("✅ 精选功能:", cfg.enable_selection)
    print("✅ 精选数量:", cfg.selection_count)
