from fastapi import APIRouter, Request
from api_gateway.services.redis_client import get_hitl_lock, delete_hitl_lock
from api_gateway.services.database import save_completed_task
from api_gateway.services.rabbitmq import publish_to_queue
from api_gateway.services.telegram import send_telegram_dm

router = APIRouter()

# Zero-cost triage keywords - expanded to catch more reminder-like messages
TRIAGE_KEYWORDS = [
    # Deadlines & Time
    "due", "deadline", "by", "before", "until", "tomorrow", "today", "tonight",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "next week", "this week", "later", "soon",
    
    # Academic/Work
    "assignment", "homework", "test", "exam", "quiz", "midterm", "final",
    "hackathon", "submit", "submission", "paper", "project", "report",
    "presentation", "lecture", "class", "lab",
    
    # Events & Meetings
    "meeting", "meet", "call", "conference", "event", "appointment",
    "session", "interview", "discussion", "standup", "sync",
    
    # Actions
    "remind", "reminder", "remember", "don't forget", "dont forget",
    "need to", "have to", "must", "should", "gotta", "got to",
    "attend", "join", "participate", "complete", "finish", "do",
    
    # Tasks
    "task", "todo", "to-do", "to do", "work on", "follow up", "followup"
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
        # PRIVATE DM - ONBOARDING & HITL
        # ============================================
        if chat_type == "private":
            # Handle /start command
            if text and text.startswith("/start"):
                welcome_message = (
                    "👋 <b>Welcome to Sieve!</b>\n\n"
                    "I'm your smart reminder assistant. I can help you:\n"
                    "• Extract reminders from conversations\n"
                    "• Set deadlines automatically\n"
                    "• Send you notifications when tasks are due\n\n"
                    "🚀 <b>Get Started:</b>\n"
                    "1. Add me to your group\n"
                    "2. Just chat naturally and mention tasks\n"
                    "3. I'll extract and remind you automatically!\n\n"
                    "💡 <b>Example:</b>\n"
                    "\"Remind me to submit assignment tomorrow at 5pm\"\n\n"
                    "Ready to add me to a group? Click the button below!"
                )
                
                # Get bot username for the link
                bot_username = "sieve7_bot"  # Your bot username
                
                # Create inline keyboard with "Add to Group" button
                # Note: Using startgroup without admin parameter - bot works as regular member
                inline_keyboard = {
                    "inline_keyboard": [
                        [
                            {
                                "text": "➕ Add to Group",
                                "url": f"https://t.me/{bot_username}?startgroup=start"
                            }
                        ],
                        [
                            {
                                "text": "📖 Help",
                                "callback_data": "help"
                            }
                        ]
                    ]
                }
                
                await send_telegram_dm(user_id, welcome_message, reply_markup=inline_keyboard)
                return {"status": "ok"}
            
            # Handle /help command
            if text and text.startswith("/help"):
                help_message = (
                    "📖 <b>How to use Sieve:</b>\n\n"
                    "<b>In Groups:</b>\n"
                    "Just chat naturally! I'll detect reminders like:\n"
                    "• \"Remind me to call John at 3pm\"\n"
                    "• \"Don't forget the meeting tomorrow\"\n"
                    "• \"Submit assignment by Friday\"\n\n"
                    "<b>Commands:</b>\n"
                    "/start - Show welcome message\n"
                    "/help - Show this help message\n\n"
                    "Need more help? Contact @YourSupportUsername"
                )
                
                await send_telegram_dm(user_id, help_message)
                return {"status": "ok"}
            
            # Check for HITL lock
            hitl_lock = await get_hitl_lock(user_id)
            
            if hitl_lock:
                # User is responding to clarification request
                print(f"[HITL] User {user_id} responding to clarification")
                
                # Send the user's response back to text_extractor for processing
                # The worker will merge the clarification with saved state
                payload = {
                    "user_id": user_id,
                    "group_id": hitl_lock.get("group_id"),
                    "message_text": text,
                    "is_hitl_response": True  # Flag to indicate this is a HITL response
                }
                
                print(f"[HITL] Routing clarification to text_extractor")
                await publish_to_queue("fast_text_queue", payload)
                
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
