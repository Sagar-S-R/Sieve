import asyncio
import aio_pika
import json
import logging
import time
from prometheus_client import start_http_server
from workers.text_extractor.core.config import settings
from workers.text_extractor.core.metrics import workflow_duration
from workers.text_extractor.graph.workflow import app
from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.services.redis_client import (
    check_hitl_lock, clear_hitl_lock,
    check_group_hitl_lock, clear_group_hitl_lock,
    is_message_processed, mark_message_processed
)
from workers.text_extractor.services.database import (
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

            # Idempotency check
            if message_id and group_id:
                if is_message_processed(message_id, group_id):
                    logger.info(f"[!] Message {message_id} already processed. Skipping.")
                    return
                mark_message_processed(message_id, group_id)

            # Group HITL response — saved_state already in payload from webhook
            if data.get("is_group_hitl"):
                saved_state = data.get("saved_state", {})
                await handle_hitl_resolution(user_id, group_id, data, saved_state, is_group_hitl=True)

            # Private DM HITL response
            elif data.get("is_hitl_response"):
                saved_state = check_hitl_lock(user_id)
                if saved_state:
                    await handle_hitl_resolution(user_id, group_id, data, saved_state, is_group_hitl=False)

            else:
                await handle_new_message(user_id, group_id, data)

            workflow_duration.observe(time.time() - workflow_start_time)

        except Exception as e:
            logger.error(f"[x] Error processing message: {e}", exc_info=True)
            raise  # aio_pika will nack


async def handle_new_message(user_id: int, group_id: int, data: dict):
    state: AgentState = {
        "user_id": user_id,
        "group_id": group_id,
        "message_text": data.get("message_text", ""),
        "original_message": data.get("message_text", ""),
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
    user_reply = data.get("message_text", "").lower().strip()
    saved_group_id = saved_state.get("group_id")

    if hitl_reason == "update_confirmation":
        if any(w in user_reply for w in ["yes", "confirm", "correct", "yeah", "yep", "y"]):
            task_id = saved_state.get("proposed_task_id")
            new_deadline = saved_state.get("proposed_new_value")
            if task_id and new_deadline:
                await update_task_by_id(task_id, new_deadline=new_deadline)
                _clear_hitl(user_id, saved_group_id, is_group_hitl)
                await send_telegram_message(saved_group_id, "Task updated successfully.")
                logger.info(f"[UPDATE] Task {task_id} updated by user {user_id}")

        elif any(w in user_reply for w in ["no", "wrong", "nope", "n"]):
            excluded = saved_state.get("excluded_task_ids", [])
            proposed = saved_state.get("proposed_task_id")
            if proposed and proposed not in excluded:
                excluded.append(proposed)
            saved_state["excluded_task_ids"] = excluded
            saved_state["hitl_reason"] = "low_match_confidence"
            saved_state["hitl_round"] = saved_state.get("hitl_round", 1)

            state = _build_state_from_saved(user_id, data, saved_state)
            result = await app.ainvoke(state)
            await handle_result(result, saved_state=saved_state, is_group_hitl=is_group_hitl)

    elif hitl_reason == "low_match_confidence":
        candidates = saved_state.get("update_candidates", [])

        if user_reply.isdigit():
            idx = int(user_reply) - 1
            if 0 <= idx < len(candidates):
                picked = candidates[idx]
                saved_state["proposed_task_id"] = picked["id"]
                saved_state["hitl_reason"] = "update_confirmation"
                state = _build_state_from_saved(user_id, data, saved_state)
                result = await app.ainvoke(state)
                await handle_result(result, saved_state=saved_state, is_group_hitl=is_group_hitl)
            else:
                from workers.text_extractor.services.telegram_client import send_dm
                await send_dm(user_id, "Invalid number. Please reply with a valid option number.")
        else:
            saved_state["hitl_round"] = saved_state.get("hitl_round", 1) + 1
            if saved_state["hitl_round"] > 2:
                _clear_hitl(user_id, saved_group_id, is_group_hitl)
                from workers.text_extractor.services.telegram_client import send_dm
                await send_dm(user_id,
                    "I couldn't find the right task. Want me to create this as a new task instead? Reply 'yes' or 'no'.")
                return
            state = _build_state_from_saved(user_id, data, saved_state)
            result = await app.ainvoke(state)
            await handle_result(result, saved_state=saved_state, is_group_hitl=is_group_hitl)

    else:
        # Missing field resolution — merge clarification
        from workers.text_extractor.nodes.hitl_merge_node import merge_hitl_clarification
        state = _build_state_from_saved(user_id, data, saved_state)
        state = await merge_hitl_clarification(state)
        await handle_result(state, saved_state=saved_state, is_group_hitl=is_group_hitl)


def _clear_hitl(user_id: int, group_id: int, is_group_hitl: bool):
    """Clear the correct HITL lock depending on flow type."""
    if is_group_hitl and group_id:
        clear_group_hitl_lock(group_id)
    else:
        clear_hitl_lock(user_id)


def _build_state_from_saved(user_id: int, data: dict, saved_state: dict) -> AgentState:
    return {
        "user_id": user_id,
        "group_id": saved_state.get("group_id"),
        "message_text": data.get("message_text", ""),
        "original_message": saved_state.get("original_message", ""),
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

    if intent == "UPDATE" and result.get("selected_task_id"):
        task_id = result.get("selected_task_id")
        if extracted and extracted.deadline:
            await update_task_by_id(task_id, new_deadline=extracted.deadline)
            _clear_hitl(user_id, group_id, is_group_hitl)
            await send_telegram_message(group_id, "Task updated successfully.")

    elif intent in ["NEW", "ANNOUNCEMENT", "RESOURCE_CALLOUT"] and extracted:
        await save_task({
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
            _clear_hitl(user_id, group_id, is_group_hitl)
        logger.info(f"[OK] Task saved for group {group_id}")


async def main():
    # Start Prometheus
    start_http_server(getattr(settings, 'PROMETHEUS_PORT', 8001))
    logger.info("[OK] Prometheus metrics exposed")

    # Init DB pool
    await init_pool()
    logger.info("[OK] DB connection pool initialized")

    # Connect RabbitMQ
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)
    queue = await channel.declare_queue('fast_text_queue', durable=True)
    await queue.consume(process_message)

    logger.info("[OK] Consuming from fast_text_queue. Press CTRL+C to exit.")
    await asyncio.Future()  # run forever


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("[!] Shutting down...")
