"""
Core AI agent — handles conversation turns and tool execution.
Uses Claude with tool_use to decide when to search, read email, etc.
"""

import json
import os
from datetime import datetime
import anthropic
from src.tools import search, gmail, notes, outages

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = f"""You are a personal AI assistant accessible via Telegram.
You help with research, managing Gmail, saving notes, scheduling tasks, and answering questions.

Current date/time: {datetime.now().strftime("%Y-%m-%d %H:%M")}

Guidelines:
- Be concise — Telegram messages should be readable on a phone.
- For research, always search before answering if the topic may have changed recently.
- When the user asks to "remember" something, save a note.
- When reading emails, summarize clearly and flag anything that needs action.
- Format responses with clean markdown (Telegram supports bold, italic, code blocks).
- Never expose internal tool errors directly — explain what went wrong in plain English.
- ALWAYS use the check_power_outages tool when the user asks about power outages, power cuts, electricity outages or Elektrodistribucija — never answer from memory or make assumptions about availability.
- When the user says "send me X at Y time" or "remind me about X tomorrow at Z", use schedule_task.
- For schedule_task, the prompt should be a self-contained instruction like "Search for world cup results and send them to me".
- run_at must be an ISO datetime string like "2026-06-27T09:00:00".
"""

TOOLS = [
    {
        "name": "web_search",
        "description": "Search the web for current information on any topic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"},
                "max_results": {"type": "integer", "description": "Number of results (default 5)", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "read_url",
        "description": "Fetch and read the text content of a specific webpage or article URL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The full URL to read"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "list_emails",
        "description": "List recent emails from Gmail inbox or a custom query.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Gmail search query (default: in:inbox)", "default": "in:inbox"},
                "max_results": {"type": "integer", "description": "Number of emails to fetch", "default": 10},
            },
        },
    },
    {
        "name": "read_email",
        "description": "Read the full content of a specific email by its ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {"type": "string", "description": "The Gmail message ID"},
            },
            "required": ["message_id"],
        },
    },
    {
        "name": "send_email",
        "description": "Send an email via Gmail.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body (plain text)"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "search_emails",
        "description": "Search Gmail with a query string (supports Gmail search syntax like from:, subject:, after:, etc.)",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Gmail search query"},
                "max_results": {"type": "integer", "default": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "label_email",
        "description": "Add or remove labels on a Gmail message (e.g. archive it, star it, move to trash).",
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {"type": "string"},
                "add_labels": {"type": "array", "items": {"type": "string"}, "description": "Label IDs to add"},
                "remove_labels": {"type": "array", "items": {"type": "string"}, "description": "Label IDs to remove"},
            },
            "required": ["message_id"],
        },
    },
    {
        "name": "save_note",
        "description": "Save a note, research summary, or piece of information to remember later.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "content": {"type": "string"},
                "tags": {"type": "string", "description": "Comma-separated tags for organization"},
            },
            "required": ["title", "content"],
        },
    },
    {
        "name": "list_notes",
        "description": "List saved notes, optionally filtered by tag.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tag": {"type": "string", "description": "Filter notes by tag (optional)"},
            },
        },
    },
    {
        "name": "get_note",
        "description": "Retrieve the full content of a saved note by its ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "note_id": {"type": "integer"},
            },
            "required": ["note_id"],
        },
    },
    {
        "name": "delete_note",
        "description": "Delete a saved note by its ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "note_id": {"type": "integer"},
            },
            "required": ["note_id"],
        },
    },
    {
        "name": "check_power_outages",
        "description": "Check planned power outages in Macedonia from Elektrodistribucija. Can filter by region (e.g. Скопје, Тетово, Охрид) and/or date (YYYY-MM-DD). If no date given, returns all upcoming outages.",
        "input_schema": {
            "type": "object",
            "properties": {
                "region": {"type": "string", "description": "Region name in Macedonian e.g. Скопје, Тетово, Охрид, Битола (optional)"},
                "for_date": {"type": "string", "description": "Date filter in YYYY-MM-DD format (optional)"},
            },
        },
    },
    {
        "name": "schedule_task",
        "description": "Schedule a task to run at a specific future date and time. Use when the user says things like 'send me X at 9am', 'remind me about Y tomorrow', 'check Z every morning'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "The self-contained task to execute at the scheduled time, e.g. 'Search for world cup results and send them to me'"},
                "run_at": {"type": "string", "description": "ISO datetime string for when to run, e.g. '2026-06-27T09:00:00'"},
            },
            "required": ["prompt", "run_at"],
        },
    },
    {
        "name": "list_scheduled_tasks",
        "description": "List all pending scheduled tasks for the user.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "cancel_scheduled_task",
        "description": "Cancel a scheduled task by its ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer"},
            },
            "required": ["task_id"],
        },
    },
]

# Will be set by bot.py after scheduler is initialized
_current_user_id: int = None

def set_current_user(user_id: int):
    global _current_user_id
    _current_user_id = user_id


def _execute_tool(name: str, inputs: dict):
    """Dispatch a tool call and return its result as a string."""
    try:
        if name == "web_search":
            results = search.web_search(**inputs)
            return json.dumps(results, indent=2)
        elif name == "read_url":
            return search.read_url(**inputs)
        elif name == "list_emails":
            results = gmail.list_emails(**inputs)
            return json.dumps(results, indent=2)
        elif name == "read_email":
            result = gmail.read_email(**inputs)
            return json.dumps(result, indent=2)
        elif name == "send_email":
            return gmail.send_email(**inputs)
        elif name == "search_emails":
            results = gmail.search_emails(**inputs)
            return json.dumps(results, indent=2)
        elif name == "label_email":
            return gmail.label_email(**inputs)
        elif name == "save_note":
            return notes.save_note(**inputs)
        elif name == "list_notes":
            results = notes.list_notes(**inputs)
            return json.dumps(results, indent=2)
        elif name == "get_note":
            result = notes.get_note(**inputs)
            return json.dumps(result, indent=2)
        elif name == "delete_note":
            return notes.delete_note(**inputs)
        elif name == "check_power_outages":
            results = outages.get_outages(**inputs)
            return outages.format_outages(results)
        elif name == "schedule_task":
            from src import scheduler
            run_at = datetime.fromisoformat(inputs["run_at"])
            task_id = scheduler.schedule_task(_current_user_id, inputs["prompt"], run_at)
            return f"Task scheduled (ID: {task_id}) for {run_at.strftime('%Y-%m-%d %H:%M')}."
        elif name == "list_scheduled_tasks":
            from src import scheduler
            tasks = scheduler.list_tasks(_current_user_id)
            return json.dumps(tasks, indent=2)
        elif name == "cancel_scheduled_task":
            from src import scheduler
            scheduler.cancel_task(inputs["task_id"])
            return f"Task {inputs['task_id']} cancelled."
        else:
            return f"Unknown tool: {name}"
    except Exception as e:
        return f"Tool error: {e}"


def chat(history: list[dict], user_message: str, user_id: int = None) -> tuple[str, list[dict]]:
    """
    Send a user message, run the agentic tool loop, return (reply_text, updated_history).
    history: list of {"role": "user"|"assistant", "content": ...} dicts
    """
    if user_id:
        set_current_user(user_id)
    # Refresh current datetime in system prompt each turn
    global SYSTEM_PROMPT
    SYSTEM_PROMPT = SYSTEM_PROMPT.replace(
        SYSTEM_PROMPT[SYSTEM_PROMPT.find("Current date"):SYSTEM_PROMPT.find("\n", SYSTEM_PROMPT.find("Current date"))],
        f"Current date/time: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )

    history = history + [{"role": "user", "content": user_message}]
    safe_history = history  # last known clean state

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=history,
        )

        tool_uses = [b for b in response.content if b.type == "tool_use"]
        text_blocks = [b for b in response.content if b.type == "text"]

        history.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn" or not tool_uses:
            reply = "\n".join(b.text for b in text_blocks if b.text)
            safe_history = history  # full exchange completed cleanly
            return reply, safe_history

        # Execute all tool calls and feed results back
        tool_results = []
        for tu in tool_uses:
            result = _execute_tool(tu.name, tu.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": result,
            })

        history.append({"role": "user", "content": tool_results})
        safe_history = history  # tool results paired — safe to save up to here
