# Sieve Bot - User Guide

## Quick Start

### For Group Admins (Adding the Bot)

1. **Add @sieve7_bot to your group**
   - Open your Telegram group
   - Click group name → Add Members
   - Search for `@sieve7_bot`
   - Add the bot

2. **You're automatically subscribed!**
   - The bot will send a welcome message in the group
   - You'll start receiving reminders for tasks mentioned in the group

3. **Invite others to subscribe**
   - Share the welcome message with group members
   - They can click "🔔 Enable My Reminders" button
   - They'll be subscribed instantly!

---

## For Group Members (Subscribing)

### ✅ Recommended Method: Click Group Button

1. Look for the bot's welcome message in your group
2. Click the "🔔 Enable My Reminders" button
3. Done! You'll now receive reminders

**This is the easiest and most reliable method.**

---

### Alternative Method: Private Chat

1. Open private chat with @sieve7_bot
2. Send `/start`
3. Click "➕ Add to Group"
4. Select your group from the list

**Note:** If the bot is already in your group, you won't see it in the list. Use the group button method instead!

---

## How It Works

### 1. Natural Language Task Detection

Just chat naturally in your group. The bot detects tasks automatically:

**Examples:**
- "Remind me to submit assignment tomorrow at 5pm"
- "Don't forget the meeting on Friday at 3pm"
- "Need to finish the project by next Monday"
- "Call John before 6pm today"

### 2. Smart Extraction

The bot uses AI to extract:
- **Task title**: What needs to be done
- **Action required**: Specific action
- **Deadline**: When it's due (in IST timezone)

### 3. Clarification (If Needed)

If the bot needs more details, it will DM you privately:
- "When is the deadline?"
- "What time on Friday?"
- "Which project are you referring to?"

Just reply naturally, and the bot will understand!

### 4. Reminders

You'll receive private DM reminders at:
- **24 hours before** deadline
- **1 hour before** deadline
- **At deadline** time

---

## Commands

### `/start`
Shows welcome message and "Add to Group" button

**When to use:** First time using the bot

---

### `/unsubscribe`
Manage your subscriptions

**How it works:**
1. Send `/unsubscribe` to bot privately
2. Bot shows list of groups you're subscribed to
3. Click a group to unsubscribe
4. Confirmation sent

**When to use:** Want to stop receiving reminders from a group

---

### `/help`
Shows help message with usage instructions

---

## Multi-Subscriber System

### How It Works

When someone mentions a task in a group:
1. **All subscribers** get the task saved
2. If clarification needed, **all subscribers** get the DM
3. **First person to reply** completes the task for themselves
4. **Others can reply separately** with different details

### Example Scenario

**Group:** CS101 Study Group (3 subscribers: Alice, Bob, Charlie)

**Message in group:** "Submit assignment tomorrow"

**What happens:**
1. Bot extracts: "Submit assignment" (needs time clarification)
2. Bot DMs Alice, Bob, and Charlie: "What time tomorrow?"
3. Alice replies: "5pm"
4. Bob replies: "6pm"
5. Charlie replies: "7pm"

**Result:**
- Alice gets reminder for 5pm
- Bob gets reminder for 6pm
- Charlie gets reminder for 7pm

**Each person can have different deadlines for the same task!**

---

## Tips & Best Practices

### ✅ Do's

- **Be specific with times**: "5pm" instead of "evening"
- **Mention dates clearly**: "May 15" instead of "next week"
- **Use natural language**: The bot understands conversational text
- **Reply to clarifications**: The bot learns from your responses

### ❌ Don'ts

- **Don't spam**: The bot ignores messages without task keywords
- **Don't edit messages**: The bot only processes new messages
- **Don't expect instant replies**: Processing takes 2-3 seconds

---

## Keyword Detection

The bot only processes messages containing task-related keywords:

**Time keywords:**
- due, deadline, by, before, until
- tomorrow, today, tonight
- monday, tuesday, etc.
- next week, this week

**Action keywords:**
- remind, reminder, remember
- need to, have to, must, should
- submit, complete, finish
- attend, join, participate

**Task keywords:**
- assignment, homework, test, exam
- meeting, call, event
- project, report, presentation

**Example:**
- ✅ "Submit assignment tomorrow" → Processed
- ❌ "How are you?" → Ignored (no keywords)

---

## Privacy & Data

### What We Store

- User ID (Telegram ID)
- Group ID (Telegram group ID)
- Task title, action, deadline
- Subscription status

### What We DON'T Store

- Message history
- Personal information
- Chat content (except task-related messages)

### GDPR Compliance

- Use `/unsubscribe` to stop receiving reminders
- Your data is deleted when you unsubscribe
- No data sharing with third parties

---

## Troubleshooting

### "Bot not responding to my messages"

**Possible reasons:**
1. Message doesn't contain task keywords
2. Bot is processing (wait 2-3 seconds)
3. Bot is down (check with admin)

**Solution:** Use task keywords like "remind", "deadline", "tomorrow"

---

### "I didn't receive a reminder"

**Possible reasons:**
1. You're not subscribed to the group
2. Task deadline hasn't arrived yet
3. You blocked the bot

**Solution:** 
- Check subscription: Send `/unsubscribe` to see your groups
- Unblock the bot if needed
- Re-subscribe using group button

---

### "Bot asked for clarification but I replied and nothing happened"

**Possible reasons:**
1. You replied in the group (should reply in private chat)
2. You took too long to reply (lock expired)
3. Someone else already replied

**Solution:** Reply to the bot's DM within 10 minutes

---

### "I want to change a task deadline"

**Current limitation:** No edit feature yet

**Workaround:** 
1. Send `/unsubscribe` and unsubscribe from group
2. Re-subscribe using group button
3. Mention the task again with new deadline

**Future feature:** `/edit` command (coming soon)

---

## Advanced Features

### Multiple Groups

You can subscribe to multiple groups:
- Each group has separate tasks
- Reminders show which group the task is from
- Use `/unsubscribe` to manage all subscriptions

### Recurring Tasks

**Current limitation:** Not supported yet

**Workaround:** Mention the task each time

**Future feature:** "Every Monday at 9am" (coming soon)

---

## Support

### Need Help?

1. Send `/help` to the bot
2. Check this guide
3. Contact group admin
4. Report issues: [GitHub Issues](https://github.com/yourusername/sieve)

### Feature Requests

We're always improving! Suggest features:
- Open a GitHub issue
- Message the developer
- Vote on existing requests

---

## Changelog

### v1.0 (Current)
- ✅ Natural language task extraction
- ✅ Multi-subscriber support
- ✅ HITL clarification system
- ✅ 3-level reminders (24h, 1h, at deadline)
- ✅ Unsubscribe mechanism
- ✅ Timezone support (IST)

### Coming Soon
- ⏳ Task editing/deletion
- ⏳ Snooze feature
- ⏳ Recurring tasks
- ⏳ Task priority levels
- ⏳ Analytics dashboard

---

Last Updated: 2026-05-11
Bot Version: 1.0
