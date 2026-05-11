# Multi-Subscriber System

## Overview

The Sieve bot now supports multiple subscribers per group. This means anyone in a group can opt-in to receive reminders and clarification requests, not just the person who sent the message.

## How It Works

### Subscription Model

**Before (Old System):**
- Bot sends DMs to whoever sent the message
- Problem: If your mom sends "be ready by 10PM", bot tries to DM your mom (403 Forbidden if she never started the bot)

**After (New System):**
- Bot tracks who wants notifications from each group
- When anyone sends a message with a task, ALL subscribers get:
  - Clarification requests (HITL DMs)
  - Reminder notifications (24h, 1h, deadline)

### Example Scenario

**Setup:**
1. You add `@sieve7_bot` to your family group
2. You're auto-subscribed
3. Your friend also wants reminders, so they send `/subscribe` in the group
4. Now both you and your friend are subscribed

**Usage:**
1. Your mom sends: "Be ready by 10PM"
2. Bot extracts task but needs clarification
3. Bot sends DM to YOU and YOUR FRIEND: "I found a task 'Be ready' but I'm missing some info: what are you getting ready for?"
4. Either you or your friend replies: "For family dinner"
5. Bot saves task for both subscribers
6. Both you and your friend get reminders at 24h, 1h, and deadline

## Database Schema

### group_subscriptions Table

```sql
CREATE TABLE group_subscriptions (
    id SERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL,
    subscriber_id BIGINT NOT NULL,
    subscribed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(group_id, subscriber_id)
);
```

### tasks Table (Updated)

```sql
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,  -- Subscriber who receives reminders
    group_id BIGINT NOT NULL,
    message_sender_id BIGINT,  -- Who sent the original message
    title VARCHAR(255) NOT NULL,
    action_required TEXT NOT NULL,
    deadline TIMESTAMP WITH TIME ZONE,
    reminder_level INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

## Commands

### /start (Private DM only)
Opens the subscription management interface.

**For new users:** Shows "Add to Group" button

**For existing users:** Shows all groups where the bot is present with subscribe/unsubscribe buttons

**Usage:** Send `/start` to `@sieve7_bot` in a private DM

**Response:** Interactive buttons to manage subscriptions

## User Flow

### Flow 1: You add the bot (Auto-subscribe)

1. You add `@sieve7_bot` to your family group
2. Bot auto-subscribes you
3. Bot sends you a DM:
   ```
   Thanks for adding me!
   You're now subscribed to reminders from this group.
   
   Want others to get reminders too?
   Share this link: https://t.me/sieve7_bot
   ```

### Flow 2: Your friend wants notifications

1. You share `https://t.me/sieve7_bot` with your friend
2. Friend clicks link → opens bot in Telegram
3. Friend clicks "START"
4. Bot shows: "🔔 Subscribe to Family Group" button
5. Friend clicks button → subscribed!
6. No commands in group chat needed

### Flow 3: Unsubscribe

1. User sends `/start` to bot in private DM
2. Bot shows: "✅ Family Group (Subscribed)" button
3. User clicks button → unsubscribed
4. Bot confirms: "👋 Unsubscribed"

## Auto-Subscription

When you add the bot to a group, you're automatically subscribed. The bot sends you a welcome DM:

```
Thanks for adding me!

You're now subscribed to reminders from this group.

How it works:
• Anyone can send messages with tasks/deadlines
• I'll DM you for clarifications if needed
• You'll get reminders before deadlines

Want others to get reminders too?
They can send /subscribe in this group!

Commands:
/subscribe - Subscribe to this group's reminders
/unsubscribe - Stop receiving reminders
/subscribers - See who's subscribed
```

## Task Creation Logic

When a task is extracted:

1. Get all subscribers for the group
2. Create ONE task per subscriber
3. Each subscriber gets their own:
   - Task record in database
   - Reminder notifications (independent reminder_level tracking)
   - HITL clarification requests

This means if 3 people are subscribed, 3 tasks are created (one for each).

## HITL (Human-in-the-Loop) Logic

When clarification is needed:

1. Get all subscribers for the group
2. Send DM to EACH subscriber
3. Create Redis lock for EACH subscriber
4. First subscriber to reply resolves the HITL
5. Task is saved for ALL subscribers

## Privacy & Permissions

- Bot works as a regular group member (no admin permissions required)
- Bot can only DM users who have:
  - Started a private chat with the bot, OR
  - Subscribed to a group where the bot is present
- Subscriptions are per-group (subscribing to Group A doesn't subscribe you to Group B)

## Edge Cases Handled

### Multiple people try to add the bot
- Telegram prevents adding the same bot twice
- Second person can send `/subscribe` instead

### Someone unsubscribes
- They stop receiving reminders
- Their existing tasks remain in database (but no new reminders sent)
- Other subscribers unaffected

### Last subscriber unsubscribes
- Group still monitored
- New messages won't create tasks (no subscribers)
- Anyone can re-subscribe with `/subscribe`

### Bot removed from group
- Subscriptions remain in database
- No new tasks created
- Existing reminders still sent (until they expire)

## Implementation Files

- `database/init.sql` - Schema with group_subscriptions table
- `api_gateway/routers/webhook.py` - Auto-subscribe on bot add, subscription commands
- `api_gateway/services/database.py` - Subscription management functions
- `workers/text_extractor/main.py` - Create tasks for all subscribers
- `workers/text_extractor/services/database.py` - Get subscribers, save tasks
- `workers/text_extractor/nodes/hitl_node.py` - Send HITL to all subscribers
- `workers/cron_notifier/` - Already works (sends to user_id in tasks)

## Testing

1. Add bot to a test group
2. Verify you get auto-subscribe DM
3. Have a friend send `/subscribe` in the group
4. Send `/subscribers` to verify both are subscribed
5. Send a message with a task
6. Verify both subscribers get HITL DMs (if needed)
7. Verify both subscribers get reminders
