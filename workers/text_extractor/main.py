import asyncio
import aio_pika
import json
import logging
import time
from prometheus_client import start_http_server
from workers.text_extractor.core.config import settings
from shared.metrics import workflow_duration
from workers.text_extractor.graph.workflow import app
from workers.text_extractor.graph.state import AgentState
from shared.redis_client import (
    check_hitl_lock, clear_hitl_lock,
    check_group_hitl_lock, clear_group_hitl_lock,
    is_message_processed, mark_message_processed
)
from shared.database import (
    init_pool, close_pool, save_task,
    update_task_by_id
)
from workers.text_extractor.services.telegram_client import send_telegram_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def process_message(message: aio_pika.IncomingMessage):
    async with message.process(requeue=False):
        workflow_start_time = time.time()

        try:
            data = json.loads(message.body)
            user_id = data.get("user_id", 0)
            group_id = data.get("group_id")
            message_id = data.get("message_id")

            if message_id and group_id:
                if await is_message_processed(message_id, group_id):
                    logger.info(f"[!] Message {message_id} already processed. Skipping.")
                    return
                await mark_message_processed(message_id, group_id)

            if data.get("is_group_hitl"):
                saved_state = data.get("saved_state", {})
                await handle_hitl_resolution(user_id, group_id, data, saved_state, is_group_hitl=True)

            elif data.get("is_hitl_response"):
                saved_state = await check_hitl_lock(user_id)
                if saved_state:
                    await handle_hitl_resolution(user_id, group_id, data, saved_state, is_group_hitl=False)

            else:
                await handle_new_message(user_id, group_id, data)

            workflow_duration.observe(time.time() - workflow_start_time)

        except Exception as e:
            logger.error(f"[x] Error processing message: {e}", exc_info=True)
            raise


async def handle_new_message(user_id: int, group_id: int, data: dict):
    is_personal = data.get("is_personal", False)

    state: AgentState = {
        "user_id": user_id,
        "group_id": group_id,
        "message_text": data.get("message_text", ""),
        "original_message": data.get("message_text", ""),
        "is_personal": is_personal,
        "triage_signal": data.get("triage_signal"),
        "intent": None,
        "message_buffer": None,
        "db_context": None,
        "context_retrieval_reasoning": None,
        "extracted_data": None,
        "validation_error": None,
        "needs_human": False,
        "hitl_prompt": None,
        "hitl_reason": None,
        "hitl_round": 0,
        "is_update": None,
        "update_candidates": None,
        "selected_task_id": None,
        "updating_task_title": None,
        "excluded_task_ids": [],
        "venue_info": None,
        "schedule_change_info": None,
        "announcement_text": None
    }

    result = await app.ainvoke(state)
    await handle_result(result, saved_state=None, is_group_hitl=False)


async def handle_hitl_resolution(user_id: int, group_id: int, data: dict, saved_state: dict, is_group_hitl: bool):
    hitl_reason = saved_state.get("hitl_reason")
    user_reply = data.get("message_text", "").strip()
    saved_group_id = saved_state.get("group_id")

    if hitl_reason == "update_candidates":
        candidates = saved_state.get("update_candidates", [])

        if user_reply.isdigit():
            # User picked a number from the list — direct DB update, no LLM needed
            idx = int(user_reply) - 1
            if 0 <= idx < len(candidates):
                picked = candidates[idx]
                new_value = saved_state.get("proposed_new_value")
                await update_task_by_id(picked["id"], new_deadline=new_value)
                await _clear_hitl(user_id, saved_group_id, is_group_hitl)
                await send_telegram_message(
                    saved_group_id,
                    f"✅ Updated: {picked['title']}"
                )
            else:
                await send_telegram_message(saved_group_id, "Invalid number. Please reply with a valid option.")
        else:
            # User described a task not in the list — run hitl_reretrieval_node
            hitl_round = saved_state.get("hitl_round", 1)
            if hitl_round >= 2:
                # Max rounds exceeded
                await _clear_hitl(user_id, saved_group_id, is_group_hitl)
                await send_telegram_message(
                    saved_group_id,
                    "I couldn't find the right task. Please try again with a clearer description."
                )
                return
            
            from workers.text_extractor.nodes.hitl_reretrieval_node import hitl_update_confirmation
            state = _build_state_from_saved(user_id, data, saved_state)
            state["hitl_round"] = hitl_round + 1
            state = await hitl_update_confirmation(state)
            await handle_result(state, saved_state=saved_state, is_group_hitl=is_group_hitl)

    else:
        # missing field resolution — merge node
        from workers.text_extractor.nodes.hitl_merge_node import merge_hitl_clarification
        state = _build_state_from_saved(user_id, data, saved_state)
        state = await merge_hitl_clarification(state)
        await handle_result(state, saved_state=saved_state, is_group_hitl=is_group_hitl)
        await _clear_hitl(user_id, saved_group_id, is_group_hitl)


async def _save_hitl_lock(user_id: int, group_id: int, hitl_state: dict, is_group_hitl: bool):
    from shared.redis_client import set_hitl_lock, set_group_hitl_lock
    if is_group_hitl and group_id:
        await set_group_hitl_lock(group_id, hitl_state)
    else:
        await set_hitl_lock(user_id, hitl_state)


async def _clear_hitl(user_id: int, group_id: int, is_group_hitl: bool):
    if is_group_hitl and group_id:
        await clear_group_hitl_lock(group_id)
    else:
        await clear_hitl_lock(user_id)


def _build_state_from_saved(user_id: int, data: dict, saved_state: dict) -> AgentState:
    return {
        "user_id": user_id,
        "group_id": saved_state.get("group_id"),
        "message_text": data.get("message_text", ""),
        "original_message": saved_state.get("original_message", ""),
        "is_personal": saved_state.get("is_personal", False),
        "triage_signal": None,
        "intent": saved_state.get("intent", "UPDATE"),
        "message_buffer": saved_state.get("message_buffer"),
        "db_context": saved_state.get("db_context"),
        "context_retrieval_reasoning": saved_state.get("context_retrieval_reasoning"),
        "extracted_data": saved_state.get("extracted_data"),
        "validation_error": None,
        "needs_human": False,
        "hitl_prompt": None,
        "hitl_reason": saved_state.get("hitl_reason"),
        "hitl_round": saved_state.get("hitl_round", 1),
        "is_update": None,
        "update_candidates": saved_state.get("update_candidates", []),
        "selected_task_id": saved_state.get("proposed_task_id"),
        "updating_task_title": None,
        "excluded_task_ids": saved_state.get("excluded_task_ids", []),
        "venue_info": None,
        "schedule_change_info": None,
        "announcement_text": None
    }


async def handle_result(result: dict, saved_state: dict, is_group_hitl: bool):
    if result.get("needs_human"):
        logger.info(f"[HITL] Triggered for user {result.get('user_id')}, reason: {result.get('hitl_reason')}")
        return

    intent = result.get("intent")
    extracted = result.get("extracted_data")
    group_id = result.get("group_id")
    user_id = result.get("user_id")
    is_personal = result.get("is_personal", False)

    if intent == "UPDATE" and result.get("selected_task_id"):
        task_id = result.get("selected_task_id")
        if extracted and extracted.deadline:
            await update_task_by_id(task_id, new_deadline=extracted.deadline)
            await _clear_hitl(user_id, group_id, is_group_hitl)
            await send_telegram_message(group_id, "Task updated successfully.")

    elif intent in ["NEW", "ANNOUNCEMENT", "FORM_DEADLINE"] and extracted:
        if is_personal:
            await save_task({
                "user_id": user_id,
                "group_id": None,
                "message_sender_id": user_id,
                "title": extracted.title,
                "action_required": extracted.action_required,
                "deadline": extracted.deadline,
                "source_message_text": result.get("original_message"),
                "message_type": extracted.message_type,
                "applies_at": extracted.applies_at,
                "location": extracted.location,
                "form_url": extracted.form_url,
                "reminder_strategy": extracted.reminder_strategy,
            })
            if saved_state:
                await _clear_hitl(user_id, group_id, is_group_hitl)
            deadline_str = str(extracted.deadline) if extracted.deadline else "no deadline set"
            await send_telegram_message(user_id, f"Reminder set: *{extracted.title}*\n{deadline_str}")
            logger.info(f"[OK] Personal task saved for user {user_id}")
        else:
            await save_task({
                "user_id": None,
                "group_id": group_id,
                "message_sender_id": user_id,
                "title": extracted.title,
                "action_required": extracted.action_required,
                "deadline": extracted.deadline,
                "source_message_text": result.get("original_message"),
                "message_type": extracted.message_type,
                "applies_at": extracted.applies_at,
                "location": extracted.location,
                "form_url": extracted.form_url,
                "reminder_strategy": extracted.reminder_strategy,
            })
            if saved_state:
                await _clear_hitl(user_id, group_id, is_group_hitl)
            logger.info(f"[OK] Group task saved for group {group_id}")


async def main():
    start_http_server(getattr(settings, 'PROMETHEUS_PORT', 8001))
    logger.info("[OK] Prometheus metrics exposed")

    await init_pool()
    logger.info("[OK] DB connection pool initialized")

    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)
    queue = await channel.declare_queue('fast_text_queue', durable=True)
    await queue.consume(process_message)

    logger.info("[OK] Consuming from fast_text_queue. Press CTRL+C to exit.")
    await asyncio.Future()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("[!] Shutting down...")
