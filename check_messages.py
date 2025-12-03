"""
Quick Message Checker - View messages without running full agent conversations
"""
import json
import os
from datetime import datetime

def check_messages(agent_name):
    """Check messages for a specific agent (Jack or Jill)"""
    
    if not os.path.exists("messages.json"):
        print(f"\n📭 No messages yet - {agent_name} hasn't received anything.\n")
        return
    
    with open("messages.json", "r", encoding="utf-8") as f:
        messages = json.load(f)
    
    # messages is a list directly
    if not isinstance(messages, list):
        messages = []
    
    # Filter messages for this agent
    agent_messages = [msg for msg in messages if msg["recipient"] == agent_name and not msg.get("read", False)]
    
    if not agent_messages:
        print(f"\n📭 No new messages for {agent_name}.\n")
        return
    
    print(f"\n{'='*60}")
    print(f"📬 NEW MESSAGES FOR {agent_name.upper()}")
    print(f"{'='*60}\n")
    
    for i, msg in enumerate(agent_messages, 1):
        timestamp = datetime.fromisoformat(msg["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
        msg_type = msg["type"].replace("_", " ").title()
        
        print(f"Message {i}/{len(agent_messages)}")
        print(f"From: {msg['sender']}")
        print(f"Type: {msg_type}")
        print(f"Time: {timestamp}")
        print(f"\n{msg['content']}\n")
        
        if msg.get("metadata"):
            print("Attachments:")
            for key, value in msg["metadata"].items():
                print(f"  - {key}: {value}")
        
        print("-" * 60 + "\n")

def show_conversation_log():
    """Show the full conversation log"""
    if not os.path.exists("conversation_log.md"):
        print("\n📭 No conversation log yet.\n")
        return
    
    print(f"\n{'='*60}")
    print("📜 FULL CONVERSATION LOG")
    print(f"{'='*60}\n")
    
    with open("conversation_log.md", "r", encoding="utf-8") as f:
        print(f.read())

def show_all_files():
    """Show all candidate profiles and job specs"""
    print(f"\n{'='*60}")
    print("📁 ALL PROFILES & JOB SPECS")
    print(f"{'='*60}\n")
    
    # Show jobs
    if os.path.exists("jobs"):
        jobs = [f for f in os.listdir("jobs") if f.endswith(".md")]
        print(f"📋 Job Specifications ({len(jobs)}):")
        for job in jobs:
            print(f"  - {job}")
    else:
        print("📋 Job Specifications: None")
    
    print()
    
    # Show candidates
    if os.path.exists("candidates"):
        candidates = [f for f in os.listdir("candidates") if f.endswith(".md")]
        print(f"👤 Candidate Profiles ({len(candidates)}):")
        for candidate in candidates:
            print(f"  - {candidate}")
    else:
        print("👤 Candidate Profiles: None")
    
    print()

def main():
    print("\n" + "="*60)
    print("MESSAGE CHECKER - Jack & Jill Communication System")
    print("="*60)
    
    while True:
        print("\nWhat would you like to check?")
        print("1. Jack's messages")
        print("2. Jill's messages")
        print("3. Full conversation log")
        print("4. All profiles & job specs")
        print("5. Exit")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == "1":
            check_messages("Jack")
        elif choice == "2":
            check_messages("Jill")
        elif choice == "3":
            show_conversation_log()
        elif choice == "4":
            show_all_files()
        elif choice == "5":
            print("\n👋 Goodbye!\n")
            break
        else:
            print("\n❌ Invalid choice. Please enter 1-5.\n")

if __name__ == "__main__":
    main()
