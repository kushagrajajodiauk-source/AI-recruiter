"""
Scout Agent - Sourcing & Matching Engine
Searches LinkedIn for candidates and jobs, ranks matches, feeds recommendations to Jack and Jill.
"""

import os
import sys
import json
import time
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from groq import Groq
from dotenv import load_dotenv
from duckduckgo_search import DDGS

from database import (
    init_database, get_all_candidates, get_all_jobs,
    add_match, send_agent_message, get_candidate, get_job
)

load_dotenv()
# Global Groq client
client = None

def init_groq():
    """Initialize Groq client"""
    global client
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ GROQ_API_KEY not found")
        sys.exit(1)
    client = Groq(api_key=api_key)
    return client


# ============================================================
# LINKEDIN X-RAY SEARCH
# ============================================================

def search_linkedin_candidates(job_title, skills, location, limit=10):
    """
    Search LinkedIn for candidate profiles using DuckDuckGo X-Ray search.
    This is a safe, API-free approach to finding LinkedIn profiles.
    """
    print(f"\n🔎 Searching LinkedIn for: {job_title} in {location}...")
    
    # Build X-Ray search query
    skill_query = " OR ".join([f'"{s}"' for s in skills[:3]])
    query = f'site:linkedin.com/in/ "{job_title}" ({skill_query}) "{location}"'
    
    print(f"   Query: {query[:80]}...")
    
    results = []
    try:
        with DDGS() as ddgs:
            search_results = list(ddgs.text(query, max_results=limit))
            
            for r in search_results:
                # Parse LinkedIn result
                title = r.get('title', '')
                url = r.get('href', '')
                snippet = r.get('body', '')
                
                # Extract name and headline from title
                # Format: "Name - Headline | LinkedIn"
                name = "Unknown"
                headline = ""
                
                if " - " in title:
                    parts = title.split(" - ", 1)
                    name = parts[0].strip()
                    if len(parts) > 1:
                        headline = parts[1].split("|")[0].strip()
                elif "|" in title:
                    name = title.split("|")[0].strip()
                
                if "linkedin.com/in/" in url:
                    results.append({
                        "name": name,
                        "headline": headline,
                        "linkedin_url": url,
                        "snippet": snippet,
                        "source": "linkedin_search"
                    })
                    print(f"   ✓ Found: {name}")
                
                time.sleep(0.3)  # Be polite
                
    except Exception as e:
        print(f"   ❌ Search error: {e}")
    
    return results

def search_linkedin_jobs(candidate_skills, preferred_industries, location, limit=10):
    """
    Search LinkedIn for job postings matching a candidate's profile.
    """
    print(f"\n🔎 Searching LinkedIn for jobs matching: {', '.join(candidate_skills[:3])}...")
    
    skill_query = " OR ".join([f'"{s}"' for s in candidate_skills[:3]])
    industry_query = " OR ".join([f'"{i}"' for i in preferred_industries[:2]]) if preferred_industries else ""
    
    query = f'site:linkedin.com/jobs/ ({skill_query})'
    if industry_query:
        query += f' ({industry_query})'
    if location:
        query += f' "{location}"'
    
    print(f"   Query: {query[:80]}...")
    
    results = []
    try:
        with DDGS() as ddgs:
            search_results = list(ddgs.text(query, max_results=limit))
            
            for r in search_results:
                title = r.get('title', '')
                url = r.get('href', '')
                snippet = r.get('body', '')
                
                # Extract job title and company
                job_title = title.split("|")[0].strip() if "|" in title else title
                company = ""
                if " at " in title.lower():
                    company = title.split(" at ")[-1].split("|")[0].strip()
                
                if "linkedin.com/jobs/" in url:
                    results.append({
                        "title": job_title,
                        "company": company,
                        "linkedin_url": url,
                        "snippet": snippet,
                        "source": "linkedin_search"
                    })
                    print(f"   ✓ Found: {job_title[:50]}...")
                
                time.sleep(0.3)
                
    except Exception as e:
        print(f"   ❌ Search error: {e}")
    
    return results

# ============================================================
# MATCHING ENGINE
# ============================================================

def calculate_match_score(candidate_data, job_data, model_name):
    """Use Gemini to calculate a match score between candidate and job."""
    prompt = f"""Analyze this candidate-job match and provide a score from 0.0 to 1.0.

CANDIDATE:
- Name: {candidate_data.get('name', 'Unknown')}
- Skills: {candidate_data.get('skills', [])}
- Headline: {candidate_data.get('headline', '')}

JOB:
- Title: {job_data.get('title', 'Unknown')}
- Company: {job_data.get('company', 'Unknown')}
- Requirements: {job_data.get('requirements', [])}

Respond with ONLY a JSON object:
{{"score": 0.XX, "reason": "brief explanation"}}
"""
    try:
        messages = [{"role": "user", "content": prompt}]
        response_text = client.chat.completions.create(model=model_name, messages=messages, temperature=0.7).choices[0].message.content
        result = json.loads(response_text.replace("```json", "").replace("```", "").strip())
        return result.get("score", 0.5), result.get("reason", "")
    except:
        return 0.5, "Unable to calculate"

# ============================================================
# MAIN SCOUT WORKFLOW
# ============================================================

def run_scout():
    """Main Scout workflow - search and match."""
    print("\n" + "="*60)
    print("🔍 SCOUT - Sourcing & Matching Agent")
    print("="*60)
    
    # Initialize
    init_database()
    
    init_groq()
    model_name = "llama-3.3-70b-versatile"
    
    # Get existing candidates and jobs from database
    candidates = get_all_candidates()
    jobs = get_all_jobs()
    
    print(f"\n📊 Database Status:")
    print(f"   Candidates: {len(candidates)}")
    print(f"   Jobs: {len(jobs)}")
    
    # MODE 1: Find candidates for existing jobs
    if jobs:
        print("\n" + "-"*40)
        print("🎯 MODE 1: Finding candidates for jobs")
        print("-"*40)
        
        for job in jobs:
            job_id = job['id']
            title = job['title']
            requirements = json.loads(job['requirements']) if job['requirements'] else []
            
            print(f"\n📋 Job: {title}")
            
            # 1. First, check INTERNAL candidates from Jack
            internal_matches = []
            if candidates:
                print("   🔍 Checking internal database first...")
                for candidate in candidates:
                    # Simple fuzzy match for now (ideally use semantics)
                    cand_skills = json.loads(candidate['skills']) if candidate['skills'] else []
                    cand_name = candidate['name']
                    
                    # Quick score check
                    score, reason = calculate_match_score(
                        {"name": cand_name, "skills": cand_skills, "headline": "Internal Candidate"}, 
                        {"title": title, "requirements": requirements, "company": job['company']},
                        model_name
                    )
                    
                    if score >= 0.7:
                        internal_matches.append({"name": cand_name, "id": candidate['id'], "score": score})
                        # Add match to DB
                        add_match(candidate['id'], job_id, score, source="internal_db")
            
            if internal_matches:
                print(f"   ✅ Found {len(internal_matches)} INTERNAL matches in database!")
                print(f"   ⏩ Skipping external LinkedIn search for this job.")
                
                # Notify Jill about her matches
                send_agent_message(
                    from_agent="Scout",
                    to_agent="Jill",
                    message_type="internal_match_found",
                    content=f"Found {len(internal_matches)} great candidates already in our system for {title}!",
                    metadata={"job_id": job_id, "matches": internal_matches}
                )
                continue  # SKIP LinkedIn search
            
            # 2. If NO internal matches, search LinkedIn
            print("   ⚠️ No internal matches found. Searching LinkedIn...")
            found_candidates = search_linkedin_candidates(
                job_title=title,
                skills=requirements[:5] if requirements else [title],
                location="",  # Could be extracted from job spec
                limit=5
            )
            
            if found_candidates:
                print(f"\n   📤 Sending {len(found_candidates)} external candidates to Jack...")
                
                # Send recommendation to Jack
                send_agent_message(
                    from_agent="Scout",
                    to_agent="Jack",
                    message_type="candidate_recommendation",
                    content=f"Found {len(found_candidates)} potential candidates for {title}",
                    metadata={
                        "job_id": job_id,
                        "job_title": title,
                        "candidates": found_candidates
                    }
                )
                print("   ✅ Sent to Jack!")
    
    # MODE 2: Find jobs for existing candidates
    if candidates:
        print("\n" + "-"*40)
        print("🎯 MODE 2: Finding jobs for candidates")
        print("-"*40)
        
        for candidate in candidates:
            candidate_id = candidate['id']
            name = candidate['name']
            skills = json.loads(candidate['skills']) if candidate['skills'] else []
            prefs = json.loads(candidate['preferences']) if candidate['preferences'] else {}
            
            print(f"\n👤 Candidate: {name}")
            
            # Search LinkedIn for matching jobs
            found_jobs = search_linkedin_jobs(
                candidate_skills=skills[:5] if skills else ["software"],
                preferred_industries=prefs.get('industries', []),
                location=prefs.get('location', ''),
                limit=5
            )
            
            if found_jobs:
                print(f"\n   📤 Sending {len(found_jobs)} jobs to Jack for outreach...")
                
                # Send recommendation to Jack (Jack does candidate outreach)
                send_agent_message(
                    from_agent="Scout",
                    to_agent="Jack",
                    message_type="job_recommendation",
                    content=f"Found {len(found_jobs)} potential jobs for {name}",
                    metadata={
                        "candidate_id": candidate_id,
                        "candidate_name": name,
                        "jobs": found_jobs
                    }
                )
                
                # Also notify Jill for hiring manager outreach
                send_agent_message(
                    from_agent="Scout",
                    to_agent="Jill",
                    message_type="outreach_opportunity",
                    content=f"Found jobs for {name} - you may want to reach out to these hiring managers",
                    metadata={
                        "candidate_id": candidate_id,
                        "candidate_name": name,
                        "jobs": found_jobs
                    }
                )
                print("   ✅ Sent to Jack and Jill!")
    
    print("\n" + "="*60)
    print("✅ Scout run complete!")
    print("="*60)

if __name__ == "__main__":
    run_scout()
