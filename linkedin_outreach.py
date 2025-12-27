"""
LinkedIn Outreach Module - Manual Assist Mode
Generates personalized outreach messages and manages the outreach queue.
Users copy-paste messages to LinkedIn manually (safe, no ban risk).
"""

import os
import re
from pathlib import Path
from datetime import datetime

from database import queue_outreach, get_pending_outreach, mark_outreach_sent

TEMPLATE_DIR = Path(__file__).parent / "templates"

# ============================================================
# TEMPLATE RENDERING
# ============================================================

def load_template(template_name):
    """Load a message template from the templates directory."""
    template_path = TEMPLATE_DIR / f"{template_name}.md"
    if template_path.exists():
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        print(f"⚠️ Template not found: {template_path}")
        return None

def render_template(template_content, variables):
    """
    Render a template by replacing {{variable}} placeholders.
    
    Args:
        template_content: The template string with {{placeholders}}
        variables: Dict of variable_name -> value
    
    Returns:
        Rendered string
    """
    result = template_content
    for key, value in variables.items():
        placeholder = "{{" + key + "}}"
        result = result.replace(placeholder, str(value) if value else "N/A")
    return result

def generate_candidate_message(candidate_name, candidate_skills, job_title, company_name, match_reason):
    """Generate a personalized message for a candidate about a job opportunity."""
    template = load_template("candidate_outreach")
    if not template:
        return None
    
    # Format skills nicely
    if isinstance(candidate_skills, list):
        skills_str = ", ".join(candidate_skills[:3])
    else:
        skills_str = str(candidate_skills)
    
    return render_template(template, {
        "candidate_name": candidate_name,
        "candidate_skills": skills_str,
        "job_title": job_title,
        "company_name": company_name,
        "match_reason": match_reason
    })

def generate_hiring_manager_message(hiring_manager_name, job_title, company_name, 
                                     candidate_name, candidate_experience, 
                                     candidate_skills, match_reason):
    """Generate a personalized message for a hiring manager about a candidate."""
    template = load_template("hiring_manager_outreach")
    if not template:
        return None
    
    if isinstance(candidate_skills, list):
        skills_str = ", ".join(candidate_skills[:5])
    else:
        skills_str = str(candidate_skills)
    
    return render_template(template, {
        "hiring_manager_name": hiring_manager_name,
        "job_title": job_title,
        "company_name": company_name,
        "candidate_name": candidate_name,
        "candidate_experience": candidate_experience,
        "candidate_skills": skills_str,
        "match_reason": match_reason
    })

# ============================================================
# OUTREACH QUEUE MANAGEMENT
# ============================================================

def add_candidate_outreach(candidate_name, linkedin_url, job_title, company_name, skills, match_reason):
    """Add a candidate outreach message to the queue."""
    message = generate_candidate_message(
        candidate_name=candidate_name,
        candidate_skills=skills,
        job_title=job_title,
        company_name=company_name,
        match_reason=match_reason
    )
    
    if message:
        outreach_id = queue_outreach(
            target_type="candidate",
            target_name=candidate_name,
            target_linkedin_url=linkedin_url,
            message=message
        )
        print(f"📝 Queued outreach to candidate: {candidate_name}")
        return outreach_id
    return None

def add_hiring_manager_outreach(manager_name, linkedin_url, job_title, company_name,
                                 candidate_name, candidate_experience, candidate_skills, match_reason):
    """Add a hiring manager outreach message to the queue."""
    message = generate_hiring_manager_message(
        hiring_manager_name=manager_name,
        job_title=job_title,
        company_name=company_name,
        candidate_name=candidate_name,
        candidate_experience=candidate_experience,
        candidate_skills=candidate_skills,
        match_reason=match_reason
    )
    
    if message:
        outreach_id = queue_outreach(
            target_type="hiring_manager",
            target_name=manager_name,
            target_linkedin_url=linkedin_url,
            message=message
        )
        print(f"📝 Queued outreach to hiring manager: {manager_name}")
        return outreach_id
    return None

def show_pending_outreach():
    """Display all pending outreach messages for manual sending."""
    pending = get_pending_outreach()
    
    if not pending:
        print("\n📭 No pending outreach messages.")
        return
    
    print("\n" + "="*70)
    print("📬 PENDING OUTREACH MESSAGES")
    print("="*70)
    print("Copy these messages and send them via LinkedIn manually.\n")
    
    for i, item in enumerate(pending, 1):
        print(f"\n{'─'*70}")
        print(f"📧 MESSAGE {i} of {len(pending)}")
        print(f"{'─'*70}")
        print(f"To: {item['target_name']} ({item['target_type']})")
        print(f"LinkedIn: {item['target_linkedin_url']}")
        print(f"\n--- MESSAGE ---")
        print(item['message'])
        print(f"--- END ---\n")
        
        # Ask user if they sent it
        response = input(f"Did you send this message? (y/n/skip): ").strip().lower()
        if response == 'y':
            mark_outreach_sent(item['id'])
            print("✅ Marked as sent!")
        elif response == 'skip':
            print("⏭️ Skipped (will show again next time)")
        else:
            print("📌 Kept in queue")
    
    print("\n" + "="*70)
    print("✅ Outreach review complete!")
    print("="*70)

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("\n🔗 LinkedIn Outreach Manager - Manual Assist Mode")
    print("This tool helps you send personalized messages safely.\n")
    
    # Show pending messages
    show_pending_outreach()
