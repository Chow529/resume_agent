import sys
from pathlib import Path

# 获取当前文件所在目录的父目录（即项目根目录）
project_root = Path(__file__).parent.parent

# 将项目根目录添加到 sys.path 的最前面
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from langchain_chroma import Chroma
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from utils.path_tool import get_abs_path  
import os  
from model.MoelFactory import EmbeddingModelIni
from utils.readyml_tool import load_txt
from utils.logging_tool import logger
import hashlib
import textwrap

MD5PATH = get_abs_path("rag_knowladge/md5.txt")
RAGPATH = get_abs_path("rag_knowladge")

"""
向量库存储,获取,读取
"""
class ChromaServer:
    def __init__(self,chromaType :str = "job_jd") -> None:
        path = RAGPATH
        # 确保目录存在
        if not os.path.exists(path):
            os.makedirs(path)

        self.chroma = Chroma(
            collection_name=chromaType,
            embedding_function=EmbeddingModelIni().InitModel(),
            persist_directory=path
        )

        self.spliter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", ""],
            chunk_size=300,
            chunk_overlap=200,
            length_function=len
        )

        self.retriever = self.chroma.as_retriever(
            # search_type="similarity_score_threshold", "score_threshold": 0.75
            search_kwargs={'k': 5,}
        )

    def get_retriever(self) -> VectorStoreRetriever:
        return self.retriever

    def ChangeToMd5(self, content: str, chunk_size: int = 4096) -> str:
        """
        将长文本内容转化为固定的md5值
        
        :param content: 原文本内容
        :type content: str
        :param chunk_size : 针对于长文本的进行切分整合成md5值
        :return: 转换的md5值
        :rtype: str
        """
        md5_obj = hashlib.md5()
        for i in range(0, len(content), chunk_size):
            md5_obj.update(content[i:i+chunk_size].encode('utf-8'))
        return md5_obj.hexdigest()

    def _ensure_md5_file(self):
        """确保 MD5 文件存在"""
        try:
            # 获取文件所在目录
            dir_path = os.path.dirname(MD5PATH)
            # 创建目录（如果不存在）
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
            # 创建文件（如果不存在）
            if not os.path.exists(MD5PATH):
                with open(MD5PATH, 'w', encoding='utf-8') as f:
                    f.write('')
                logger.info(f"已创建 MD5 文件: {MD5PATH}")
        except Exception as e:
            logger.error(f"创建 MD5 文件失败: {e}")

    def StorageVector(self, content: str):
        """
        将文本存储到向量库内
        
        :param content: 文本信息
        :type content: str
        """
        # 确保 MD5 文件存在
        self._ensure_md5_file()
        
        listStr = self.spliter.split_text(content)
        
        idsList = []
        for text_chunk in listStr:
            md5 = self.ChangeToMd5(text_chunk)
            if self.CheckMd5(md5):
                idsList.append(md5)
                self.__storageMd5(md5)
            else:
                # 如果某个块已存在，跳过（但继续处理其他块）
                logger.info(f"MD5 已存在，跳过: {md5[:8]}...")
                # 注意：这里原来有 return，会导致停止处理后续块
                # 如果希望跳过重复块继续处理，应该用 continue 而不是 return
        
        # 如果有新的块，才添加到向量库
        if idsList:
            self.chroma.add_texts(texts=listStr, ids=idsList)

    def batch_storage(self, contents: list[str]):
        """
        批量存储文本到向量库（优化版本，减少 IO 和 Embedding 调用次数）
        
        :param contents: 文本信息列表
        :type contents: list[str]
        """
        # 确保 MD5 文件存在
        self._ensure_md5_file()
        
        # 一次性加载所有已存在的 MD5 到 set 中（O(1) 查找）
        existing_md5s = set()
        try:
            with open(MD5PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        existing_md5s.add(line.strip())
        except Exception as e:
            logger.error(f"加载 MD5 文件失败: {e}")
        
        all_texts = []
        all_ids = []
        new_md5s = []
        
        # 处理所有文本
        for content in contents:
            chunks = self.spliter.split_text(content)
            for chunk in chunks:
                md5 = self.ChangeToMd5(chunk)
                if md5 not in existing_md5s:
                    all_texts.append(chunk)
                    all_ids.append(md5)
                    new_md5s.append(md5)
                    existing_md5s.add(md5)  # 避免同一批次内重复
        
        # 批量写入向量库（按 Embedding API 上限分批，每次最多 20 条）
        if all_texts:
            BATCH_SIZE = 20  # 向量模型 API 单次请求的 batch 上限
            for i in range(0, len(all_texts), BATCH_SIZE):
                batch_texts = all_texts[i:i + BATCH_SIZE]
                batch_ids = all_ids[i:i + BATCH_SIZE]
                self.chroma.add_texts(texts=batch_texts, ids=batch_ids)
            logger.info(f"批量写入向量库：{len(all_texts)} 个文本块")
            
            # 批量写入 MD5 文件（一次写入）
            try:
                with open(MD5PATH, 'a', encoding='utf-8') as f:
                    for md5 in new_md5s:
                        f.write(md5 + "\n")
            except Exception as e:
                logger.error(f"批量写入 MD5 失败: {e}")

    def __storageMd5(self, md5: str):
        """
        存储md5值,将文本转化成md5值进行存储(去重使用)

        :param md5: 文本信息(转化成md5值)
        :type md5: str
        """
        try:
            # 确保文件存在
            self._ensure_md5_file()
            
            # 追加写入
            with open(MD5PATH, 'a', encoding='utf-8') as f:
                f.write(md5 + "\n")
        except Exception as e:
            logger.error(f"存储 MD5 失败: {e}")

    def CheckMd5(self, md5: str) -> bool:
        """
        检查文本转化成md5值是否存在,true不存在 false存在
        
        :param md5: md5值
        :type md5: str
        """
        try:
            # 确保文件存在
            self._ensure_md5_file()
            
            # 读取文件
            with open(MD5PATH, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 检查 MD5 是否存在（去除换行符比较）
            for line in lines:
                if line.strip() == md5:
                    return False  # 已存在，返回 False
            
            return True  # 不存在，返回 True
            
        except Exception as e:
            logger.error(f"检查 MD5 失败: {e}")
            return True  # 出错时默认认为不存在，可以继续

    def __delectMd5(self, md5: str):
        """
        删除文本内指定md5值
        
        :param md5: 说明
        :type md5: str
        """
        try:
            # 确保文件存在
            self._ensure_md5_file()
            
            # 1. 读取文件所有内容
            with open(MD5PATH, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 2. 删除指定的字符串
            new_lines = [
                line for line in lines 
                if line.strip() != md5 and line.strip() != ''
            ]
            
            # 3. 重新写入文件（覆盖）
            with open(MD5PATH, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
                
            logger.info(f"已删除 MD5: {md5}")
            
        except FileNotFoundError:
            logger.error(f"文件不存在")
        except Exception as e:
            logger.error(f"操作失败: {e}")

    def __delectVector(self, md5: str):
        """
        删除指定md5值的向量库内容
        
        :param md5: 说明
        :type md5: str
        """
        self.chroma.delete([md5])

    def DelectValue(self, md5: str):
        """
        包装内部的删除md5同时删除文本以及向量库内容
        """
        if not self.CheckMd5(md5):  # 注意：CheckMd5 返回 True 表示不存在
            self.__delectMd5(md5)
            self.__delectVector(md5)

    def list_all_documents(self):
        """
        列出向量库中所有文档
        
        :return: 文档列表，每个文档包含 id、page_content 和 metadata
        :rtype: list
        """
        try:
            data = self.chroma.get()
            documents = []
            if data and data.get('ids'):
                ids = data['ids']
                docs = data.get('documents') or []
                metadatas = data.get('metadatas') or []
                for i, doc_id in enumerate(ids):
                    metadata = metadatas[i] if i < len(metadatas) and metadatas[i] else {}
                    doc = {
                        'id': doc_id,
                        'page_content': docs[i] if i < len(docs) else '',
                        'metadata': metadata if metadata else {}
                    }
                    documents.append(doc)
            return documents
        except Exception as e:
            logger.error(f"获取向量库文档列表失败: {e}")
            return []

    def add_qa_document(self, q_id: str, question: str, answer: str, section: str = "自定义"):
        """
        添加一个 QA 文档到向量库
        
        :param q_id: 问题ID（如 Q100）
        :param question: 问题内容
        :param answer: 答案内容
        :param section: 章节名称
        :return: 是否成功
        """
        try:
            qa_content = f"**{q_id}: {question}**\nA{q_id[1:]}: {answer}"
            doc = Document(
                page_content=qa_content,
                metadata={
                    "section": section,
                    "q_id": q_id,
                    "type": "Q&A",
                    "source": "user_manual"
                }
            )
            self.chroma.add_texts(
                texts=[doc.page_content],
                ids=[q_id],
                metadatas=[doc.metadata]
            )
            return True
        except Exception as e:
            logger.error(f"添加 QA 文档失败: {e}")
            return False

    def delete_document(self, doc_id: str):
        """
        删除指定文档
        
        :param doc_id: 文档ID
        :return: 是否成功
        """
        try:
            self.chroma.delete([doc_id])
            return True
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False