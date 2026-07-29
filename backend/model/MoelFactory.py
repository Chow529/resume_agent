from typing  import Optional,cast
from abc import ABC,abstractmethod
from langchain.chat_models import BaseChatModel,init_chat_model
from langchain.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
import os

load_dotenv()

class ModelFactory (ABC): 
    @abstractmethod
    def InitModel(self) -> Optional[Embeddings | BaseChatModel] :
        pass


class ChatModelIni (ModelFactory) :
    def InitModel(self) -> BaseChatModel :      
        return cast(BaseChatModel,init_chat_model(model = os.getenv("DEEPSEEK_MODEL"),
                               base_url= os.getenv("DEEPSEEK_BASE_URL"),
                               api_key = os.getenv("DEEPSEEK_API_KEY"),
                               temperature = 0.7))

class EmbeddingModelIni (ModelFactory) :
    def InitModel(self) -> Embeddings :
        return OpenAIEmbeddings(model = cast(str,os.getenv("EMBEDDING_MODE")),
                               base_url= os.getenv("DEEPSEEK_BASE_URL"),
                               api_key = os.getenv("DEEPSEEK_API_KEY"), # type: ignore
                               check_embedding_ctx_length=False)



if __name__ == "__main__" :
    chat = EmbeddingModelIni().InitModel()
    res = chat.embed_query("你好")
    print(res[:3])