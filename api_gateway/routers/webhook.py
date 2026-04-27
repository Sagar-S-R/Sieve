from fastapi import APIRouter, Request
from api_gateway.services.redis_client import get_hitl_lock, delete_hitl_lock
from api_gateway.services.database import save_completed_task
from api_gateway.services.rabbitmq import publish_to_queue
from api_gateway.services.telegram import send_telegram_dm

router = APIRouter()

# Zero-cost triage keywords
TRIAGE_KEYWORDS = [
    "due", "deadline", "assignment", "homework", "test", "exam",
    "hackathon", "submit", "submission", "paper", "project",
    "meeting", "presentation", "reminder", "task"
]


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Main webhook endpoint for Telegram updates.
    
    Flow:
    1. Private DM → Check HITL lock → Save task if lock exists
    2. Group message with media → Route to heavy_media_queue
    3. Group message with text → Triage keywords → Route to fast_text_queue or drop
    """
    try:
        data = await request.json()
        
        # Extract message data
        message = data.get("message", {})
        if not message:
            return {"status": "ok"}
        
        user_id = message.get("from", {}).get("id")
        chat = message.get("chat", {})
        chat_type = chat.get("type")  # "private", "group", "supergroup"
        text = message.get("text", "")
        
        # Check for media
        photo = message.get("photo")
        document = message.get("document")
        
        # ============================================
        # PRIVATE DM - HITL INTERCEPT
        # ============================================
        if chat_type == "private":
            # Check for HITL lock
            hitl_lock = await get_hitl_lock(user_id)
            
            if hitl_lock:
                # User is responding to clarification request
                print(f"[HITL] User {user_id} responding to clarification")
                
                # Extract saved data from lock
                extracted_data = hitl_lock.get("extracted_data", {})
                
                # Merge user's answer with saved data
                # The user's text is the clarification (e.g., deadline)
                task_data = {
                    "user_id": hitl_lock.get("user_id", user_id),
                    "group_id": hitl_lock.get("group_id"),
                    "title": extracted_data.get("title", "Task"),
                    "action_required": extracted_data.get("action_required", ""),
                    "deadline": text  # User's reply is the missing deadline
                }
                
                # Save to database
                try:
                    task_id = await save_completed_task(task_data)
                    print(f"[HITL] Task {task_id} saved after clarification")
                    
                    # Delete HITL lock
                    await delete_hitl_lock(user_id)
                    
                    # Send confirmation DM
                    await send_telegram_dm(
                        user_id,
                        f"✅ <b>Task saved!</b>\n\n"
                        f"📌 {task_data['title']}\n"
                        f"⏰ Deadline: {text}"
                    )
                    
                except Exception as e:
                    print(f"[HITL] Error saving task: {e}")
                    await send_telegram_dm(
                        user_id,
                        "❌ Sorry, there was an error saving your task. Please try again."
                    )
                
                return {"status": "ok"}
            
            # No HITL lock - ignore private messages for now
            return {"status": "ok"}
        
        # ============================================
        # GROUP MESSAGE - ROUTING LOGIC
        # ============================================
        if chat_type in ["group", "supergroup"]:
            group_id = chat.get("id")
            
            # Prepare base payload
            payload = {
                "user_id": user_id,
                "group_id": group_id,
                "message_text": text
            }
            
            # Check for media (images or documents)
            if photo or document:
                # Route to heavy_media_queue
                if photo:
                    # Get highest resolution photo
                    file_id = photo[-1].get("file_id")
                    payload["file_id"] = file_id
                    payload["media_type"] = "image"
                elif document:
                    file_id = document.get("file_id")
                    payload["file_id"] = file_id
                    payload["media_type"] = "document"
                
                print(f"[ROUTE] Media message → heavy_media_queue")
                await publish_to_queue("heavy_media_queue", payload)
                return {"status": "ok"}
            
            # Pure text message - apply zero-cost triage
            if text:
                text_lower = text.lower()
                
                # Check for triage keywords
                has_keywords = any(keyword in text_lower for keyword in TRIAGE_KEYWORDS)
                
                if has_keywords:
                    # Route to fast_text_queue
                    print(f"[ROUTE] Text with keywords → fast_text_queue")
                    await publish_to_queue("fast_text_queue", payload)
                else:
                    # Drop message to save LLM costs
                    print(f"[DROP] Text without keywords - dropped")
                
                return {"status": "ok"}
        
        return {"status": "ok"}
        
    except Exception as e:
        print(f"[ERROR] Webhook error: {e}")
        return {"status": "error", "message": str(e)}
