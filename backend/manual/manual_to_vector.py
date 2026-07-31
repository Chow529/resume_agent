#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户操作手册导入到向量库的脚本
将 user_manual.md 中的每个 Q&A 对作为独立的 Document 存储到 Chroma 向量库
"""

import sys
import os

# 将项目根目录添加到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from pathlib import Path
from langchain_core.documents import Document
from rag.ChromaServer import ChromaServer
import re

def parse_qa_from_manual(file_path):
    """
    从 user_manual.md 文件中解析出所有 Q&A 对
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    documents = []
    current_section = "前言"
    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # 检测章节标题
        if line.startswith('## '):
            current_section = line[3:].strip()
            i += 1
            continue

        # 检测 Q 行：**Q编号: 问题？**
        q_match = re.match(r'\*\*Q(\d+): (.*?)\*\*$', line)
        if q_match:
            q_id = q_match.group(1)
            q_text = line.strip()
            i += 1

            # 跳过空行寻找 A 行
            while i < len(lines) and lines[i].strip() == "":
                i += 1

            a_text = ""
            if i < len(lines):
                a_line = lines[i].strip()
                # 匹配 A1: 答案内容
                a_match = re.match(r'A(\d+): (.+)', a_line)
                if a_match:
                    a_text = f"A{a_match.group(1)}: {a_match.group(2)}"

            if q_text and a_text:
                qa_content = q_text + "\n" + a_text
                doc = Document(
                    page_content=qa_content,
                    metadata={
                        "section": current_section,
                        "q_id": f"Q{q_id}",
                        "type": "Q&A",
                        "source": "user_manual"
                    }
                )
                documents.append(doc)
                print(f"[OK] 已解析: Q{q_id} - {current_section}")
            i += 1
        else:
            i += 1

    return documents


def save_qa_to_vector_db():
    """
    主函数：解析手册并存储到向量库
    """
    # 获取手册路径（与脚本同目录）
    manual_path = os.path.join(os.path.dirname(__file__), "user_manual.md")

    if not os.path.exists(manual_path):
        print(f"错误: 找不到手册文件 {manual_path}")
        return

    print(f"正在解析手册: {manual_path}")

    # 解析所有 Q&A 对
    documents = parse_qa_from_manual(manual_path)
    print(f"\n共解析出 {len(documents)} 个 Q&A 单元")

    if not documents:
        print("警告: 未解析到任何 Q&A 内容，请检查手册格式")
        return

    # 初始化向量库
    chroma = ChromaServer(chromaType="user_manual")

    # 准备 texts 和 ids
    texts = [doc.page_content for doc in documents]
    ids = [doc.metadata["q_id"] for doc in documents]

    # 批量添加到 Chroma
    try:
        chroma.chroma.add_texts(texts=texts, ids=ids)
        print(f"\n成功存储 {len(texts)} 个 Q&A 单元到向量库")
        print(f"向量库名称: user_manual")
    except Exception as e:
        print(f"\n存储到向量库时出错: {e}")


if __name__ == "__main__":
    save_qa_to_vector_db()
