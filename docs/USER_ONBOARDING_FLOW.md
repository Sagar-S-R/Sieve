# User Onboarding Flow - How Friends Can Subscribe

## The Problem

When a friend wants to subscribe to a group where the bot is already added:
- **Telegram Limitation:** You cannot "re-add" a bot to a group where it already exists
- **Old Flow:** Friend clicks `/start` → "Add to Group" → Tries to add to existing group → Fails ❌

## The Solution ✅

We've implemented a smart onboarding flow that detects if the user is already in groups with the bot.

---

## Flow 1: Friend Clicks "Enable My Reminders" Button (Recommended)

**Best UX - One Click Subscribe**

1. Bot is added to group
2. Bot sends welcome message IN THE GROUP with button: "🔔 Enable My Reminders"
3. Friend clicks button → Opens private chat with deep link
4. Bot auto-subscribes friend → Confirmation message sent
5. Done! ✅

**Deep Link Format:** `https://t.me/sieve7_bot?start=sub_{group_id}`

**Code Location:** `api_gateway/routers/webhook.py` (lines 90-140)

---

## Flow 2: Friend Uses /start First (Alternative)

**When friend starts private chat before clicking group button**

### Scenario A: Friend is in groups with the bot

1. Friend sends `/start` to bot privately
2. Bot checks: `get_user_available_groups(user_id)`
3. Bot finds groups where:
   - Bot is present (exists in `group_subscriptions`)
   - Shows subscription status for each
4. Bot shows buttons:
   - **If unsubscribed:** "🔔 Subscribe to Group {id}" (deep link)
   - **If already subscribed:** Shows status + "➕ Add to New Group"
5. Friend clicks subscribe button → Opens deep link → Auto-subscribes
6. Done! ✅

**Code Location:** `api_gateway/routers/webhook.py` (lines 200-260)

### Scenario B: Friend not in any groups with bot yet

1. Friend sends `/start` to bot privately
2. Bot checks: `get_user_available_groups(user_id)` → Empty list
3. Bot shows welcome message with "➕ Add to Group" button
4. Friend clicks → Adds bot to NEW group
5. Bot auto-subscribes friend
6. Done! ✅

---

## Technical Implementation

### Database Query: `get_user_available_groups()`

**Location:** `api_gateway/services/database.py`

```python
async def get_user_available_groups(user_id: int) -> list:
    """
    Get all groups where the bot is present.
    Shows subscription status for each group.
    
    Returns:
        List of dicts with group_id, is_subscribed
    """
    query = """
        SELECT DISTINCT 
            gs.group_id,
            CASE WHEN user_sub.subscriber_id IS NOT NULL 
                THEN true ELSE false 
            END as is_subscribed
        FROM group_subscriptions gs
        LEFT JOIN group_subscriptions user_sub 
            ON user_sub.group_id = gs.group_id 
            AND user_sub.subscriber_id = $1
        ORDER BY gs.group_id
    """
```

**How it works:**
1. Finds all groups where bot exists (has at least one subscriber)
2. Checks if THIS user is subscribed to each group
3. Returns list with subscription status

**Limitation:** We don't verify if user is actually a member of the group (Telegram API limitation). We assume if they're trying to subscribe, they have access.

---

## Deep Link Types

### 1. Subscription Deep Link
**Format:** `https://t.me/sieve7_bot?start=sub_{group_id}`

**Triggers:** `/start sub_{group_id}` command

**Action:** Auto-subscribe user to specified group

**Example:** `https://t.me/sieve7_bot?start=sub_-1001234567890`

### 2. Add to Group Deep Link
**Format:** `https://t.me/sieve7_bot?startgroup=start`

**Action:** Opens group selection dialog to add bot

**Used when:** User not in any groups with bot yet

---

## Inline Keyboard Examples

### Welcome Message in Group (After Bot Added)

```json
{
  "inline_keyboard": [[
    {
      "text": "🔔 Enable My Reminders",
      "url": "https://t.me/sieve7_bot?start=sub_{group_id}"
    }
  ]]
}
```

### /start Response (User in Groups, Not Subscribed)

```json
{
  "inline_keyboard": [
    [
      {
        "text": "🔔 Subscribe to Group -1001234567890",
        "url": "https://t.me/sieve7_bot?start=sub_-1001234567890"
      }
    ],
    [
      {
        "text": "➕ Add to New Group",
        "url": "https://t.me/sieve7_bot?startgroup=start"
      }
    ]
  ]
}
```

### /start Response (User Not in Any Groups)

```json
{
  "inline_keyboard": [[
    {
      "text": "➕ Add to Group",
      "url": "https://t.me/sieve7_bot?startgroup=start"
    }
  ]]
}
```

---

## Why This Solves the Problem

### Before (Broken Flow)
1. Friend uses `/start` first
2. Bot shows "Add to Group" button
3. Friend tries to add to existing group
4. **Telegram rejects** (bot already there) ❌
5. Friend confused, gives up

### After (Fixed Flow)
1. Friend uses `/start` first
2. Bot detects friend is in groups with bot
3. Bot shows "Subscribe to Group X" buttons (deep links)
4. Friend clicks → Auto-subscribes ✅
5. No need to "re-add" bot!

---

## User Instructions

### For Group Admin (Person who added bot)
1. Add bot to group
2. Share the "🔔 Enable My Reminders" button message with friends
3. Tell friends to click the button

### For Friends (New subscribers)
**Option 1 (Recommended):**
1. Click "🔔 Enable My Reminders" button in group
2. Done!

**Option 2 (If you started private chat first):**
1. Send `/start` to bot privately
2. Click "🔔 Subscribe to Group X" button
3. Done!

**Option 3 (Adding to new group):**
1. Send `/start` to bot privately
2. Click "➕ Add to New Group"
3. Select a NEW group (not one where bot already exists)

---

## Testing Checklist

- [x] Bot added to group → Welcome message sent with button
- [x] Friend clicks button → Private chat opens with deep link
- [x] Deep link auto-subscribes → Confirmation sent
- [x] Friend uses `/start` first → Shows subscribe buttons
- [x] Friend already subscribed → Shows "Add to New Group" only
- [x] Friend not in any groups → Shows "Add to Group" button
- [x] Multiple groups → Shows all unsubscribed groups as buttons

---

## Future Improvements

### 1. Store Group Names
**Current:** Shows "Group -1001234567890"
**Better:** Shows "CS101 Study Group"

**Implementation:**
- Store group title when bot is added
- Update `group_subscriptions` table with `group_name` column

### 2. Verify Group Membership
**Current:** Assumes user has access if they try to subscribe
**Better:** Use Telegram API to verify user is actually in the group

**Implementation:**
```python
async def is_user_in_group(user_id: int, group_id: int) -> bool:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
    response = await client.post(url, json={
        "chat_id": group_id,
        "user_id": user_id
    })
    member = response.json().get("result", {})
    return member.get("status") in ["member", "administrator", "creator"]
```

### 3. Show Group Activity
**Feature:** Show how many tasks have been created in each group
**Example:** "🔔 Subscribe to CS101 Study Group (12 tasks this week)"

---

## Related Files

- `api_gateway/routers/webhook.py` - Main webhook handler with `/start` logic
- `api_gateway/services/database.py` - `get_user_available_groups()` function
- `api_gateway/services/telegram.py` - `send_telegram_dm()` with inline keyboards
- `database/init.sql` - `group_subscriptions` table schema

---

Last Updated: 2026-05-11
