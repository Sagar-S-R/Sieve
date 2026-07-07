# Sieve User Guide

Welcome to the Sieve task assistant! This guide explains how to interact with the bot in Telegram.

## How it Works

Sieve is a "silent observer" bot. You add it to your Telegram groups, and it listens in the background for keywords like "due", "deadline", "assignment", etc. When it detects a task, it extracts the details and saves it to its database. 

It will **never** reply in the group chat. When a deadline approaches, it will send a **private Direct Message (DM)** to the person who sent the message.

## Triggering Task Extraction

To ensure the bot picks up your task, use standard keywords in your message.

### Text Messages
Just send a normal message with a clear deadline:
- *"Reminder: Submit the math assignment by tomorrow 5pm"*
- *"The hackathon project is due Friday at 11:59pm"*

### Images and Documents
You can send screenshots, photos of whiteboards, or PDF documents. Include a caption with a keyword:
- Send an image of a syllabus and add the caption: *"Syllabus for the semester, assignments due as listed."*
- Sieve will download the file, use AI Vision/OCR to read the text, and extract all the deadlines.

## The Human-in-the-Loop (HITL) Flow

Sometimes, you might mention a task but forget to include a specific deadline. For example:
- *"Reminder to buy groceries"*

Sieve's AI will realize it's missing a deadline and needs clarification. Here is what happens:
1. Sieve suspends processing the task.
2. It sends you a **private DM** asking for the missing information (e.g., "When should I remind you?").
3. You reply to the DM with the missing info (e.g., "Tomorrow at 6pm").
4. Sieve intercepts your reply, merges it with the original task, and saves it. It will confirm with a "Task saved!" message.

## Task Reminders

By default, the Sieve system checks for due tasks every 60 seconds. When your deadline arrives, the bot will send you a DM with the task details. 
Once a reminder is sent, the task is marked as completed in the database so you won't receive duplicate notifications.
