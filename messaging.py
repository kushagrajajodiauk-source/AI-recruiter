"""
Shared messaging system for Jack and Jill agents.
Handles message exchange via messages.json and conversation logging.
"""

import json
import os
from datetime import datetime
import uuid


def init_messages_file():
    """Initialize messages.json if it doesn't exist."""
    if not os.path.exists("messages.json"):
        with open("messages.json", "w") as f:
            json.dump([], f, indent=2)


def send_message(sender, recipient, msg_type, content, metadata=None):
    """
    Send a message to the queue.
    
    Args:
        sender: "Jack" or "Jill"
        recipient: "Jack" or "Jill"
        msg_type: "candidate_profile" | "job_spec" | "match_suggestion" | "general"
        content: Message text
        metadata: Optional dict with additional data
    """
    init_messages_file()
    
    message = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "sender": sender,
        "recipient": recipient,
        "type": msg_type,
        "content": content,
        "metadata": metadata or {},
        "read": False
    }
    
    # Load existing messages
    with open("messages.json", "r") as f:
        messages = json.load(f)
    
    # Append new message
    messages.append(message)
    
    # Save back
    with open("messages.json", "w") as f:
        json.dump(messages, f, indent=2)
    
    # Log to conversation trail
    log_conversation(sender, recipient, msg_type, content)
    
    return message["id"]


def read_messages(for_recipient, mark_as_read=True):
    """
    Read unread messages for a specific recipient.
    
    Args:
        for_recipient: "Jack" or "Jill"
        mark_as_read: If True, mark messages as read
    
    Returns:
        List of message dicts
    """
    init_messages_file()
    
    with open("messages.json", "r") as f:
        messages = json.load(f)
    
    # Filter unread messages for this recipient
    unread_messages = [m for m in messages if m["recipient"] == for_recipient and not m.get("read", False)]
    
    if mark_as_read and unread_messages:
        # Mark as read
        for msg in messages:
            if msg["recipient"] == for_recipient and not msg.get("read", False):
                msg["read"] = True
        
        with open("messages.json", "w") as f:
            json.dump(messages, f, indent=2)
    
    return unread_messages


def log_conversation(sender, recipient, msg_type, content):
    """Append message to the conversation log."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Create log file if it doesn't exist
    if not os.path.exists("conversation_log.md"):
        with open("conversation_log.md", "w") as f:
            f.write("# Agent Conversation Log\n\n")
            f.write("This is a record of all messages exchanged between Jack and Jill.\n\n")
            f.write("---\n\n")
    
    # Append message
    with open("conversation_log.md", "a", encoding="utf-8") as f:
        f.write(f"## [{timestamp}] {sender} → {recipient}: {msg_type.replace('_', ' ').title()}\n\n")
        f.write(f"{content}\n\n")
        f.write("---\n\n")


def get_all_candidate_profiles():
    """Get list of all candidate profile files from candidates/ directory."""
    profiles = set()  # Use set for automatic deduplication
    
    # Scan candidates directory
    if os.path.exists("candidates"):
        for filename in os.listdir("candidates"):
            if filename.endswith(".md"):
                filepath = os.path.normpath(os.path.join("candidates", filename))
                profiles.add(filepath)
    
    # Also check messages for any files not in directory
    init_messages_file()
    with open("messages.json", "r") as f:
        messages = json.load(f)
    
    for msg in messages:
        if msg["type"] == "candidate_profile" and msg.get("metadata", {}).get("candidate_file"):
            profile_file = os.path.normpath(msg["metadata"]["candidate_file"])
            if os.path.exists(profile_file):
                profiles.add(profile_file)
    
    return sorted(list(profiles))  # Convert back to sorted list


def get_all_job_specs():
    """Get list of all job spec files from jobs/ directory."""
    jobs = set()  # Use set for automatic deduplication
    
    # Scan jobs directory
    if os.path.exists("jobs"):
        for filename in os.listdir("jobs"):
            if filename.endswith(".md"):
                filepath = os.path.normpath(os.path.join("jobs", filename))
                jobs.add(filepath)
    
    # Also check messages for any files not in directory
    init_messages_file()
    with open("messages.json", "r") as f:
        messages = json.load(f)
    
    for msg in messages:
        if msg["type"] == "job_spec" and msg.get("metadata", {}).get("job_file"):
            job_file = os.path.normpath(msg["metadata"]["job_file"])
            if os.path.exists(job_file):
                jobs.add(job_file)
    
    return sorted(list(jobs))  # Convert back to sorted list
