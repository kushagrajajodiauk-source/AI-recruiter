"""
Unified Recruiting Loop - The "Boardroom"
Orchestrates the negotiation between Jack (Candidate Agent) and Jill (Hiring Agent),
with Scout (Sourcer) acting as a fallback.
"""

import os
import sys
import json
import time
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

# Import database and Scout logic
from database import init_database, get_all_candidates, get_all_jobs, add_match
from scout_agent import calculate_match_score, search_linkedin_candidates

load_dotenv()

# Setup Groq Client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL_NAME = "llama-3.3-70b-versatile"

TRANSCRIPT_FILE = "negotiation_log.md"

def log_to_transcript(speaker, text):
    """Logs conversation to file and prints to console."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted_text = f"**{speaker}**: {text}\n\n"
    
    print(f"\n[{timestamp}] {speaker}: {text}")
    
    with open(TRANSCRIPT_FILE, "a", encoding="utf-8") as f:
        f.write(formatted_text)

def generate_agent_response(system_prompt, user_input):
    """Generates an agent response using Groq."""
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"[Error: {e}]"

def main():
    print("\n" + "="*60)
    print("🤝 AI AGENT MATCHING 'BOARDROOM'")
    print("="*60)
    
    # Initialize Log
    with open(TRANSCRIPT_FILE, "w", encoding="utf-8") as f:
        f.write("# 🤝 Agent Negotiation Transcript\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n---\n\n")

    init_database()
    
    jobs = get_all_jobs()
    candidates = get_all_candidates()
    
    if not jobs:
        print("❌ No jobs found in database. Run 'python jill_agent.py' first.")
        return

    # Loop through each open job
    for job in jobs:
        job_title = job['title']
        job_reqs = job['requirements']
        
        log_to_transcript("SYSTEM", f"Opening discussion for Job: **{job_title}**")
        
        # 1. Jill Pitches the Role (New Step)
        jill_pitch_prompt = f"""
        You are Jill, the Hiring Manager's AI Agent.
        You are in a boardroom with Jack (Candidate Agent) and Scout (Sourcer).
        
        JOB DETAILS:
        Title: {job_title}
        Requirements: {job_reqs}
        
        Write a short, professional opening statement to the team. 
        Pitch the role and the company briefly. Explain what you are looking for and why it's urgent.
        Keep it to 2-3 sentences.
        """
        jill_pitch = generate_agent_response(jill_pitch_prompt, "Open the meeting.")
        log_to_transcript("Jill", jill_pitch)

        # 2. Jack Responds & Checks Roster
        log_to_transcript("Jack", "Understood, Jill. That sounds like a key role. Let me check my current candidate roster against those requirements...")
        
        internal_matches_found = False
        candidates_pitched = 0
        
        if candidates:
            # Sort candidates by rough match score to prioritize best ones
            scored_candidates = []
            for candidate in candidates:
                cand_skills = json.loads(candidate['skills']) if candidate['skills'] else []
                # Simple keyword heuristic for sorting (LLM will do real eval)
                scored_candidates.append(candidate)

            for candidate in scored_candidates:
                # Jack evaluates if he should pitch this person
                jack_eval_prompt = f"""
                You are Jack. Jill just pitched this role: "{jill_pitch}"
                
                CANDIDATE PROFILE:
                Name: {candidate['name']}
                Skills: {candidate.get('skills', 'No specific skills listed')}
                Profile Summary: {candidate.get('headline', 'No headline')}
                
                Step 1: Assign a score from 0-10 based on POTENTIAL and ADAPTABILITY.
                - 10 = Perfect fit or high potential.
                - 0 = Completely irrelevant.
                
                Step 2: Decide if you should pitch them.
                - If Score >= 4, you MUST pitch them. (Be flexible!)
                
                Respond in this EXACT format:
                SCORE: [Number]
                PITCH: [Your 2 sentence pitch explaining why they are a good bet]
                
                If Score < 4, just respond: SKIP
                """
                jack_response = generate_agent_response(jack_eval_prompt, "Evaluate candidate.")
                
                if "SKIP" not in jack_response:
                    # Extract Jack's score
                    try:
                        jack_score_line = [l for l in jack_response.split('\n') if "SCORE:" in l][0]
                        jack_score = float(jack_score_line.split("SCORE:")[1].strip().split('/')[0])
                        jack_pitch_text = jack_response.split("PITCH:")[1].strip() if "PITCH:" in jack_response else jack_response
                    except:
                        jack_score = 5.0 # Default if parsing fails
                        jack_pitch_text = jack_response

                    candidates_pitched += 1
                    log_to_transcript("Jack", f"**Candidate: {candidate['name']}** (Score: {jack_score}/10)\n{jack_pitch_text}")
                    
                    # 3. Jill Evaluates the Candidate
                    jill_eval_prompt = f"""
                    You are Jill. Jack just pitched {candidate['name']} for the {job_title} role.
                    Jack's Pitch: "{jack_pitch_text}"
                    Jack's Score: {jack_score}/10
                    
                    Real Job Requirements: {job_reqs}
                    
                    Step 1: Assign your own INDEPENDENT score (0-10) based on requirements fit.
                    - Be critical but fair.
                    
                    Step 2: Provide your reasoning.
                    
                    Respond in this EXACT format:
                    SCORE: [Number]
                    REASON: [Your strict reasoning]
                    """
                    jill_decision = generate_agent_response(jill_eval_prompt, "Evaluate the pitch.")
                    
                    # Extract Jill's score
                    try:
                        jill_score_line = [l for l in jill_decision.split('\n') if "SCORE:" in l][0]
                        jill_score = float(jill_score_line.split("SCORE:")[1].strip().split('/')[0])
                        jill_reason = jill_decision.split("REASON:")[1].strip() if "REASON:" in jill_decision else jill_decision
                    except:
                        jill_score = 0.0
                        jill_reason = jill_decision
                        
                    log_to_transcript("Jill", f"(Score: {jill_score}/10)\n{jill_reason}")
                    
                    # Calculate Average
                    avg_score = (jack_score + jill_score) / 2
                    log_to_transcript("SYSTEM", f"📊 Average Score: {avg_score}/10")
                    
                    if avg_score > 8:
                        internal_matches_found = True
                        add_match(candidate['id'], job['id'], avg_score/10, source="negotiation_win")
                        log_to_transcript("SYSTEM", f"✅ INTERVIEW SCHEDULED! {candidate['name']} -> {job_title} (Avg > 8)")
                    else:
                         log_to_transcript("SYSTEM", f"❌ Candidate did not meet the bar (>8).")

        if candidates_pitched == 0:
            log_to_transcript("Jack", "I've reviewed my entire roster, but honestly, I don't have anyone who meets that specific bar right now.")

        # Phase 3: Scout's Fallback (External Search)
        if not internal_matches_found:
            log_to_transcript("Jill", "We didn't find any strong matches (>8/10). Scout, please look externally.")
            log_to_transcript("Scout", f"On it! Scouring LinkedIn for {job_title}...")
            
            # Using basic search terms from job title
            found_candidates = search_linkedin_candidates(job_title, [], "London", limit=3)
            
            if found_candidates:
                log_to_transcript("Scout", f"I found {len(found_candidates)} potential profiles on LinkedIn.")
                for cand in found_candidates:
                    log_to_transcript("Scout", f"Found: {cand['name']} - {cand.get('headline', 'No headline')}")
            else:
                log_to_transcript("Scout", "I couldn't find any external matches right now either.")
        else:
            log_to_transcript("Scout", "Looks like you two found a great match internally. I'll stay put.")

    print(f"\n✅ Negotiation Complete! Read the full transcript in: {TRANSCRIPT_FILE}")

if __name__ == "__main__":
    main()
