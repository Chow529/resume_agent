#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据中心路由

提供岗位 JD 采集相关接口：
- GET    /api/data-center/modules             采集模块列表（前端据此渲染模块与参数表单）
- POST   /api/data-center/scrape/stream       流式爬取（SSE 进度推送），结果按 user_id 入库
- GET    /api/data-center/jds                 查询个人/公用 JD
- GET    /api/data-center/jds/choices         面试可选 JD（个人+公用）
- GET    /api/data-center/jds/{jd_id}         JD 详情
- PUT    /api/data-center/jds/{jd_id}/visibility  个人数据 <-> 公用数据
- DELETE /api/data-center/jds/{jd_id}         删除本人 JD
"""
from __future__ import annotations

import asyncio
import json
import threading

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from collectors import get_collector, list_modules_metadata
from sqlClass.job_jd_model import JobJdModel
from utils.logging_tool import logger

router = APIRouter(prefix="/api/data-center", tags=["data-center"])


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


@router.get("/modules")
async def list_modules():
    """获取可用采集模块及参数定义"""
    return {"success": True, "modules": list_modules_metadata()}


@router.post("/scrape/stream")
async def scrape_stream(request: Request):
    """触发采集模块爬取，SSE 推送进度，完成后把结果按用户入库"""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return StreamingResponse(
            iter([_sse("error", {"message": "请求数据格式错误"})]),
            media_type="text/event-stream",
        )

    user_id = body.get("user_id")
    module_key = body.get("module")
    params = body.get("params") or {}
    if not user_id:
        return StreamingResponse(
            iter([_sse("error", {"message": "缺少 user_id，请先登录"})]),
            media_type="text/event-stream",
        )
    collector = get_collector(module_key) if module_key else None
    if collector is None:
        return StreamingResponse(
            iter([_sse("error", {"message": f"未知采集模块：{module_key}"})]),
            media_type="text/event-stream",
        )

    async def event_stream():
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def run_scrape():
            """后台线程：仅执行爬取（数据库写入回到事件循环线程，避免跨线程共用连接）"""
            try:
                def on_progress(keyword, page, collected, total_pages):
                    loop.call_soon_threadsafe(queue.put_nowait, {
                        "type": "progress",
                        "keyword": keyword,
                        "page": page,
                        "collected": collected,
                        "total_pages": total_pages,
                    })

                result = collector.scrape(params, on_progress=on_progress)
                loop.call_soon_threadsafe(queue.put_nowait, {
                    "type": "scraped",
                    "rows": result.rows,
                    "stats": result.stats,
                })
            except Exception as e:
                logger.error(f"采集模块 {module_key} 执行失败: {e}", exc_info=True)
                loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "message": str(e)})

        thread = threading.Thread(target=run_scrape, daemon=True)
        thread.start()

        try:
            while True:
                item = await queue.get()
                t = item.get("type")
                if t == "progress":
                    yield _sse("progress", {
                        "keyword": item["keyword"],
                        "page": item["page"],
                        "collected": item["collected"],
                        "total_pages": item["total_pages"],
                    })
                elif t == "scraped":
                    rows = item["rows"]
                    # 归属当前用户，默认私有
                    for r in rows:
                        r["user_id"] = int(user_id)
                        r["is_public"] = 0
                    # 在事件循环线程同步写入（量不大，且避免跨线程共用单例数据库连接）
                    try:
                        saved = JobJdModel().upsert_many(rows)
                    except Exception as e:
                        logger.error(f"JD 入库失败: {e}", exc_info=True)
                        yield _sse("error", {"message": f"爬取成功但入库失败: {str(e)[:200]}"})
                        return
                    yield _sse("done", {"saved": saved, "stats": item.get("stats", {})})
                    return
                elif t == "error":
                    yield _sse("error", {"message": item["message"]})
                    return
        finally:
            thread.join(timeout=2.0)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/jds")
async def list_jds(
    user_id: int = Query(...),
    scope: str = Query("personal"),  # personal | public
    keyword: str = Query(None),
):
    """查询 JD：scope=personal 个人库，scope=public 公用库"""
    model = JobJdModel()
    if scope == "public":
        items = model.list_public(keyword=keyword)
    else:
        items = model.list_personal(user_id, keyword=keyword)
    return {"success": True, "items": items, "scope": scope}


@router.get("/jds/choices")
async def jd_choices(user_id: int = Query(...)):
    """面试开始时选择目标岗位：个人数据 + 公用数据（同岗位去重）"""
    items = JobJdModel().list_choices(user_id)
    return {"success": True, "items": items}


@router.get("/jds/ranking")
async def jd_ranking(
    scope: str = Query("personal"),  # personal | public
    user_id: int = Query(None),
):
    """岗位使用排名：scope=personal 个人排名（本人JD按使用次数），scope=public 公用排名（所有用户使用汇总）"""
    model = JobJdModel()
    if scope == "public":
        items = model.list_public_ranking()
    else:
        if not user_id:
            return {"success": False, "message": "缺少 user_id"}
        items = model.list_personal_ranking(user_id)
    return {"success": True, "items": items, "scope": scope}


@router.get("/jds/{jd_id}")
async def jd_detail(jd_id: int):
    item = JobJdModel().get_by_id(jd_id)
    if not item:
        return {"success": False, "message": "JD 不存在"}
    return {"success": True, "item": item}


@router.put("/jds/{jd_id}/visibility")
async def set_visibility(jd_id: int, request: Request):
    """个人数据 -> 公用数据（仅所有者可操作；公用后不可改回个人数据）"""
    data = await request.json()
    user_id = data.get("user_id")
    is_public = 1 if data.get("is_public") else 0
    if not user_id:
        return {"success": False, "message": "缺少 user_id"}
    try:
        affected = JobJdModel().set_public(jd_id, int(user_id), is_public)
    except ValueError as e:
        return {"success": False, "message": str(e)}
    if not affected:
        return {"success": False, "message": "操作失败：数据不存在、你不是所有者或该数据已公开"}
    return {"success": True, "is_public": is_public}


@router.delete("/jds/{jd_id}")
async def delete_jd(jd_id: int, user_id: int = Query(...)):
    """删除本人 JD（仅所有者可操作）"""
    affected = JobJdModel().delete_for_user(jd_id, user_id)
    if not affected:
        return {"success": False, "message": "删除失败：数据不存在或你不是所有者"}
    return {"success": True}
