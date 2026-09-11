from typing import Optional, cast
from abc import ABC, abstractmethod
from langchain.chat_models import BaseChatModel, init_chat_model
from langchain.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
import json
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent.parent.parent / "config.json"

# 模型实例缓存，保存配置后调用 reload_models() 清除
_chat_model: Optional[BaseChatModel] = None
_embedding_model: Optional[Embeddings] = None


def _cfg() -> dict:
    """读取 config.json，不存在或解析失败返回空字典"""
    if _CONFIG_PATH.is_file():
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def config_ready() -> bool:
    """判断 config.json 是否包含必要字段"""
    cfg = _cfg()
    return bool(cfg.get("model_name") and cfg.get("api_key") and cfg.get("base_url"))


def reload_models():
    """清除模型缓存，下次访问时从 config.json 重新加载"""
    global _chat_model, _embedding_model
    _chat_model = None
    _embedding_model = None


class ModelFactory(ABC):
    @abstractmethod
    def InitModel(self) -> Optional[Embeddings | BaseChatModel]:
        pass


class ChatModelIni(ModelFactory):
    def InitModel(self) -> BaseChatModel:
        global _chat_model
        if _chat_model is not None:
            return _chat_model
        cfg = _cfg()
        if not (cfg.get("model_name") and cfg.get("api_key") and cfg.get("base_url")):
            raise RuntimeError("AI 模型未配置，请先完成模型配置")
        temperature = float(cfg.get("temperature", 0.7)) if cfg.get("temperature") else 0.7
        _chat_model = cast(BaseChatModel, init_chat_model(
            model=cfg["model_name"],
            model_provider="openai",
            base_url=cfg["base_url"],
            api_key=cfg["api_key"],
            temperature=temperature,
        ))
        return _chat_model


class EmbeddingModelIni(ModelFactory):
    def InitModel(self) -> Embeddings:
        global _embedding_model
        if _embedding_model is not None:
            return _embedding_model
        cfg = _cfg()
        if not cfg.get("embedding_model"):
            raise RuntimeError("Embedding 模型未配置，请先完成模型配置")
        # 如果开启了独立配置，使用 embedding_* 字段；否则回退到主模型字段
        if cfg.get("embedding_separate"):
            api_key = cfg.get("embedding_api_key") or cfg.get("api_key")
            base_url = cfg.get("embedding_base_url") or cfg.get("base_url")
        else:
            api_key = cfg.get("api_key")
            base_url = cfg.get("base_url")
        if not (api_key and base_url):
            raise RuntimeError("Embedding 模型配置不完整，请检查 API Key 和 Base URL")
        _embedding_model = OpenAIEmbeddings(
            model=cfg["embedding_model"],
            base_url=base_url,
            api_key=api_key,
            check_embedding_ctx_length=False,
            dimensions=1536
        )
        return _embedding_model


if __name__ == "__main__":
    chat = EmbeddingModelIni().InitModel()
    res = chat.embed_query("你好")
    print(res[:3])
