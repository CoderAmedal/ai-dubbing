"""Provider 注册表 — 按 stage + name 查找实现。

provider 通过 @register 装饰器注册，配置从 settings（用户数据目录）读取。
"""

from __future__ import annotations

import logging
from typing import TypeVar

from .base import ProviderInfo

log = logging.getLogger("providers.registry")

P = TypeVar("P")

_REGISTRY: dict[str, type] = {}


def register(cls: type) -> type:
    """装饰器：按 cls.info.name 注册 provider。"""
    _REGISTRY[cls.info.name] = cls
    return cls


def list_providers(stage: str | None = None) -> list[ProviderInfo]:
    """列出全部（或指定环节的）provider 元信息。"""
    infos = []
    for cls in _REGISTRY.values():
        if stage is None or cls.info.stage == stage:
            infos.append(cls.info)
    return sorted(infos, key=lambda i: (i.stage, i.name))


def get_provider(name: str, cls: type | None = None):
    """实例化 provider。cls 用于限定环节（校验 name 属于该环节）。"""
    if name not in _REGISTRY:
        raise KeyError(f"未知 provider: {name}（可用: {sorted(_REGISTRY)}）")
    provider_cls = _REGISTRY[name]
    if cls is not None and not issubclass(provider_cls, cls):
        raise TypeError(f"provider {name} 不属于 {cls.__name__} 环节")
    return provider_cls()


def resolve_provider_config(settings: dict, stage: str) -> dict:
    """从 settings 中提取指定环节的 provider 配置。

    settings 结构: {"asr": {...}, "translate": {...}, "tts": {...}}
    """
    section = settings.get(stage, {})
    if not isinstance(section, dict):
        return {}
    return dict(section)
