"""
面试模拟 Agent - 终端控制台版本
使用 langchain.agents.create_agent 实现交互式面试
完整集成 rag/ModelServer 和 rag/ChromaServer 模块
"""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from langchain_core.messages import HumanMessage, AIMessage
from langchain.agents import create_agent
from rag.ChromaServer import ChromaServer
from agent.tools import agent_tools
from model.MoelFactory import ChatModelIni
from utils.readyml_tool import load_yaml_config, load_pdf
from utils.logging_tool import logger


def build_agent():
    """构建 Agent"""
    prompt = load_yaml_config("prompt/prompt.yml")
    if prompt is None:
        raise FileNotFoundError("未找到 prompt/prompt.yml 配置文件")

    system_prompt = prompt.get("MAIN_PROMPT", "")
    chat_model = ChatModelIni().InitModel()

    agent = create_agent(
        chat_model,
        tools=[agent_tools.get_job_working, agent_tools.get_jd_content],
        system_prompt=system_prompt,
    )

    return agent


def print_help():
    """打印帮助信息"""
    print("\n" + "=" * 60)
    print("              可用命令帮助")
    print("=" * 60)
    print("  /start     - 开始面试流程 (读取简历,获取岗位,检索JD)")
    print("  /end       - 结束面试,回到终端")
    print("  /resume    - 查看当前简历内容")
    print("  /vector xx - 查看向量库中已存储的xx相关JD数量")
    print("  /history   - 查看对话历史")
    print("  /clear     - 清空对话历史")
    print("  /help      - 打印此帮助信息")
    print("  /quit      - 退出程序")
    print("  直接输入消息 - 与面试 Agent 对话 (需在面试中)")
    print("-" * 60)


def print_banner():
    """打印欢迎横幅"""
    print("\n" + "=" * 60)
    print("        面试模拟 Agent - 交互式终端版")
    print("=" * 60)
    print("  输入 /help 查看所有可用命令")
    print("-" * 60)


def main():
    """主交互循环"""
    try:
        agent = build_agent()
    except Exception as e:
        logger.error(f"Agent 初始化失败: {e}")
        print(f"错误: Agent 初始化失败 - {e}")
        print("请检查 prompt/prompt.yml 和 .env 配置是否正确")
        return

    chat_history: list = []
    chroma_server = ChromaServer()  # 复用同一个向量库实例
    print_banner()

    while True:
        try:
            user_input = input("\n[你] ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见!")
            break

        if not user_input:
            continue

        if user_input in ("/quit", "/exit"):
            print("再见!")
            break

        if user_input == "/clear":
            chat_history.clear()
            print("对话历史已清空。")
            continue

        if user_input == "/help":
            print_help()
            continue

        if user_input == "/end":
            """结束面试,回到终端"""
            print("\n面试已结束,回到终端模式。")
            print("输入 /start 重新开始面试,输入 /help 查看更多命令。")
            chat_history.clear()
            continue

        if user_input == "/history":
            if not chat_history:
                print("暂无对话历史。")
            else:
                print(f"\n--- 对话历史 ({len(chat_history)} 条) ---")
                for i, msg in enumerate(chat_history, 1):
                    role = "用户" if isinstance(msg, HumanMessage) else "Agent"
                    preview = (msg.content[:100] + "...") if isinstance(msg.content, str) else str(msg.content)[:100]
                    print(f"  {i}. [{role}] {preview}")
                print("-" * 30)
            continue

        if user_input == "/resume":
            """查看简历内容"""
            user_resum = load_pdf()
            if user_resum:
                content = "\n".join([doc.page_content for doc in user_resum])
                print(f"\n[简历内容]\n{content}")
            else:
                print("\n[提示] 未找到简历文件 job/jobhunter.pdf")
            continue

        if user_input.startswith("/vector"):
            """查看向量库信息"""
            retriever = chroma_server.get_retriever()
            # 通过查询一个通用词来估算库中数据量
            try:
                jdList = list(filter(lambda x: x.strip(), user_input.split(" ")))
                if len(jdList) > 2:
                    all_docs = retriever.invoke(jdList[-1])
                    print(f"\n[向量库] 当前存储了 {len(all_docs)} 条相关JD记录")
            except Exception as e:
                print(f"\n[向量库] 查询失败: {e}")
            continue

        if user_input == "/start":
            """启动面试流程: 清空历史,让Agent自主调用工具,打印调试信息"""
            print("\n" + "=" * 60)
            print("正在初始化面试流程...")
            print("=" * 60)

            # 0. 确认简历文件存在
            user_resum = load_pdf()
            if not user_resum:
                print("[错误] 未找到简历文件,请先将简历放入 job/jobhunter.pdf")
                continue
            print("[1/5] 简历文件确认成功")

            chat_history.clear()
            chat_history.append(HumanMessage(content="开始面试,请先获取我的简历信息"))

            print("[2/5] 等待Agent调用工具获取岗位信息...")
            try:
                response = agent.invoke({"messages": chat_history})
                messages = response.get("messages", [])
                ai_reply = messages[-1].content if messages else ""
                print(f"[3/5] Agent响应:\n{ai_reply}")
                print("[4/5] 等待Agent调用工具存入JD到向量库...")

                # 检查是否有工具调用,等待完成
                for msg in messages:
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        for tc in msg.tool_calls:
                            print(f"     -> 调用工具: {tc['name']}")

                chat_history.append(AIMessage(content=ai_reply))
                print("[5/5] 面试流程启动完成,请简单做一个自我介绍")
                print(f"\n[Agent] {ai_reply}")
            except Exception as e:
                print(f"\n[错误] Agent 执行失败: {e}")
            continue

        # 普通对话 - 交给 Agent 处理,Agent 内部会通过工具调用 ChromaServer 和 ModelServer
        chat_history.append(HumanMessage(content=user_input))

        try:
            response = agent.invoke({"messages": chat_history})
            messages = response.get("messages", [])
            ai_reply = messages[-1].content if messages else ""
            print(f"\n[Agent] {ai_reply}")
            chat_history.append(AIMessage(content=ai_reply))
        except Exception as e:
            print(f"\n[错误] Agent 执行失败: {e}")
            logger.error(f"Agent 执行错误: {e}", exc_info=True)


if __name__ == "__main__":
    main()
