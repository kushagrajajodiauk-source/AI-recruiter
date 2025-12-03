"""
Job-Focused Match Discussion - Jack shortlists candidates per role, Jill reviews
"""
import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import datetime
from messaging import send_message, get_all_job_specs, get_all_candidate_profiles

load_dotenv()

def log_detailed_discussion(job_file, job_discussion):
    """Log the detailed discussion to conversation_log.md"""
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    job_name = os.path.basename(job_file).replace('.md', '').replace('job_', '').replace('_', ' ').title()
    
    with open("conversation_log.md", "a", encoding="utf-8") as f:
        f.write(f"\n## 💬 [{timestamp}] Jack & Jill Discussion: {job_name}\n\n")
        f.write(f"**Job:** {os.path.basename(job_file)}\n")
        f.write(f"**Candidates Screened:** {job_discussion['total_candidates_screened']}\n")
        f.write(f"**Shortlisted:** {job_discussion['shortlist_count']}\n\n")
        
        f.write("---\n\n")
        
        # Write each candidate discussion
        sorted_candidates = sorted(job_discussion['candidates'], key=lambda x: x['avg_score'], reverse=True)
        
        for rank, candidate in enumerate(sorted_candidates, 1):
            cand_name = os.path.basename(candidate['file']).replace('.md', '').replace('candidate_', '').replace('_', ' ').title()
            
            f.write(f"### Candidate #{rank}: {cand_name}\n\n")
            f.write(f"**File:** {os.path.basename(candidate['file'])}\n")
            f.write(f"**Jack's Score:** {candidate['jack_score']:.2f}/1.0\n")
            f.write(f"**Jill's Score:** {candidate['jill_score']:.2f}/1.0\n")
            f.write(f"**Average:** {candidate['avg_score']:.2f}/1.0\n")
            f.write(f"**Decision:** {candidate['decision']}\n\n")
            
            f.write(f"#### 🤖 Jack's Analysis:\n\n")
            f.write(f"{candidate['jack_analysis']}\n\n")
            
            f.write(f"#### 🤖 Jill's Review:\n\n")
            f.write(f"{candidate['jill_analysis']}\n\n")
            
            f.write("---\n\n")
        
        f.write("\n")


def analyze_candidate_for_job(job_content, candidate_file, model):
    """Have Jack quickly score a candidate for a job"""
    try:
        with open(candidate_file, "r", encoding="utf-8") as f:
            candidate_content = f.read()
        
        prompt = f"""You are Jack, a Talent Advocate. Quickly score this candidate for this job.

CANDIDATE PROFILE:
---
{candidate_content}
---

JOB REQUIREMENTS:
---
{job_content}
---

Provide ONLY:
1. Match Score (0.0-1.0)
2. One sentence why this score

Format: Start with "MATCH_SCORE: X.XX" then one brief sentence."""

        response = model.generate_content(prompt)
        analysis = response.text
        
        # Extract score
        score = 0.0
        for line in analysis.split('\n'):
            if 'MATCH_SCORE' in line:
                try:
                    score = float(line.split(':')[1].strip())
                except:
                    pass
                break
        
        return score, analysis
    except Exception as e:
        print(f"Error analyzing {candidate_file}: {e}")
        return 0.0, ""

def discuss_job_matches(model):
    """For each job, have Jack shortlist candidates and Jill review"""
    
    job_files = get_all_job_specs()
    candidate_files = get_all_candidate_profiles()
    
    if not job_files:
        print("❌ No job specs found. Run Jill first to create job specs.")
        return
    
    if not candidate_files:
        print("❌ No candidate profiles found. Run Jack first to interview candidates.")
        return
    
    print(f"\n📊 Found:")
    print(f"   - {len(job_files)} job spec(s)")
    print(f"   - {len(candidate_files)} candidate profile(s)\n")
    
    # Create matches directory
    os.makedirs("matches", exist_ok=True)
    
    all_discussions = []
    
    # Process each job
    for job_idx, job_file in enumerate(job_files, 1):
        print(f"\n{'='*70}")
        print(f"📋 JOB {job_idx}/{len(job_files)}: {os.path.basename(job_file)}")
        print(f"{'='*70}\n")
        
        # Load job content
        with open(job_file, "r", encoding="utf-8") as f:
            job_content = f.read()
        
        # Step 1: Jack screens ALL candidates
        print(f"🤖 JACK: Screening {len(candidate_files)} candidate(s)...\n")
        
        candidate_scores = []
        for candidate_file in candidate_files:
            score, brief_reason = analyze_candidate_for_job(job_content, candidate_file, model)
            candidate_scores.append({
                "file": candidate_file,
                "score": score,
                "reason": brief_reason
            })
            print(f"   ✓ {os.path.basename(candidate_file)}: {score:.2f}")
        
        # Sort by score and take top candidates (minimum 0.5 score or top 5, whichever is less)
        candidate_scores.sort(key=lambda x: x['score'], reverse=True)
        shortlist = [c for c in candidate_scores if c['score'] >= 0.5][:5]
        
        if not shortlist:
            print(f"\n❌ No suitable candidates found (all scores < 0.5)")
            continue
        
        print(f"\n📋 Jack's Shortlist: {len(shortlist)} candidate(s)")
        for i, c in enumerate(shortlist, 1):
            print(f"   {i}. {os.path.basename(c['file'])}: {c['score']:.2f}")
        
        # Step 2: Jack creates detailed analysis for shortlisted candidates
        print(f"\n🤖 JACK: Creating detailed analysis for shortlist...\n")
        
        shortlist_details = []
        for candidate_info in shortlist:
            candidate_file = candidate_info['file']
            
            with open(candidate_file, "r", encoding="utf-8") as f:
                candidate_content = f.read()
            
            jack_prompt = f"""You are Jack, a Talent Advocate. You've shortlisted this candidate for a role. Provide your detailed analysis.

CANDIDATE PROFILE:
---
{candidate_content}
---

JOB REQUIREMENTS:
---
{job_content}
---

Provide:
1. Match Score (0.0-1.0)
2. Why you shortlisted them (2-3 sentences)
3. Top 3 strengths for this role
4. Potential concerns
5. Your recommendation to Jill

Start with "MATCH_SCORE: X.XX" then your analysis."""

            jack_response = model.generate_content(jack_prompt)
            jack_analysis = jack_response.text
            
            # Extract score
            jack_score = 0.0
            for line in jack_analysis.split('\n'):
                if 'MATCH_SCORE' in line:
                    try:
                        jack_score = float(line.split(':')[1].strip())
                    except:
                        pass
                    break
            
            shortlist_details.append({
                "file": candidate_file,
                "score": jack_score,
                "analysis": jack_analysis
            })
            
            print(f"   ✓ {os.path.basename(candidate_file)}: {jack_score:.2f}")
        
        # Step 3: Jill reviews Jack's shortlist
        print(f"\n🤖 JILL: Reviewing Jack's recommendations...\n")
        
        jill_reviews = []
        for candidate_info in shortlist_details:
            candidate_file = candidate_info['file']
            jack_analysis = candidate_info['analysis']
            
            with open(candidate_file, "r", encoding="utf-8") as f:
                candidate_content = f.read()
            
            jill_prompt = f"""You are Jill, a Talent Acquisition Partner. Jack recommended this candidate from his shortlist. Review their fit.

YOUR JOB OPENING:
---
{job_content}
---

CANDIDATE PROFILE:
---
{candidate_content}
---

JACK'S RECOMMENDATION:
---
{jack_analysis}
---

Provide:
1. Your Match Score (0.0-1.0)
2. Do you agree with Jack? Why or why not?
3. Role-specific concerns
4. Final decision: Interview or Pass?

Start with "MATCH_SCORE: X.XX" then your response."""

            jill_response = model.generate_content(jill_prompt)
            jill_analysis = jill_response.text
            
            # Extract score
            jill_score = 0.0
            for line in jill_analysis.split('\n'):
                if 'MATCH_SCORE' in line:
                    try:
                        jill_score = float(line.split(':')[1].strip())
                    except:
                        pass
                    break
            
            avg_score = (candidate_info['score'] + jill_score) / 2
            
            if avg_score >= 0.7:
                decision = "🎯 INTERVIEW"
            elif avg_score >= 0.5:
                decision = "⚠️ BACKUP"
            else:
                decision = "❌ PASS"
            
            jill_reviews.append({
                "file": candidate_file,
                "jack_score": candidate_info['score'],
                "jack_analysis": jack_analysis,
                "jill_score": jill_score,
                "jill_analysis": jill_analysis,
                "avg_score": avg_score,
                "decision": decision
            })
            
            print(f"   ✓ {os.path.basename(candidate_file)}: J:{candidate_info['score']:.2f} / Ji:{jill_score:.2f} → {decision}")
        
        # Save this job's discussion
        job_discussion = {
            "job_file": job_file,
            "timestamp": datetime.now().isoformat(),
            "total_candidates_screened": len(candidate_files),
            "shortlist_count": len(shortlist),
            "candidates": jill_reviews
        }
        all_discussions.append(job_discussion)
        
        # Send messages
        shortlist_summary = "\n".join([
            f"• {os.path.basename(c['file'])}: {c['jack_score']:.2f} - {c['decision']}"
            for c in jill_reviews
        ])
        
        send_message("Jack", "Jill", "job_shortlist",
                   f"🎯 SHORTLIST FOR {os.path.basename(job_file)}\n\nScreened {len(candidate_files)} candidates, recommending {len(shortlist)}:\n\n{shortlist_summary}",
                   {"job_file": job_file, "shortlist_count": len(shortlist)})
        
        # Also log detailed conversation to conversation_log.md
        log_detailed_discussion(job_file, job_discussion)
        
        print(f"\n✅ Completed discussion for {os.path.basename(job_file)}\n")
    
    # Save reports
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # JSON report
    json_file = f"matches/job_discussions_{timestamp_str}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(all_discussions, f, indent=2)
    
    # Markdown report
    markdown_file = f"matches/job_discussions_{timestamp_str}.md"
    with open(markdown_file, "w", encoding="utf-8") as f:
        f.write(f"# Jack & Jill Job-Focused Match Discussions\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}\n\n")
        f.write(f"**Jobs Reviewed:** {len(all_discussions)}\n\n")
        f.write("---\n\n")
        
        for job_idx, discussion in enumerate(all_discussions, 1):
            job_name = os.path.basename(discussion['job_file'])
            
            f.write(f"## Job #{job_idx}: {job_name}\n\n")
            f.write(f"**Job Spec:** [{job_name}](../{discussion['job_file']})\n\n")
            f.write(f"**Screening Results:**\n")
            f.write(f"- Total candidates screened: {discussion['total_candidates_screened']}\n")
            f.write(f"- Shortlisted by Jack: {discussion['shortlist_count']}\n")
            f.write(f"- Reviewed by Jill: {len(discussion['candidates'])}\n\n")
            
            f.write(f"### 📊 Final Rankings\n\n")
            f.write("| Rank | Candidate | Jack | Jill | Avg | Decision |\n")
            f.write("|------|-----------|------|------|-----|----------|\n")
            
            # Sort by average score
            sorted_candidates = sorted(discussion['candidates'], key=lambda x: x['avg_score'], reverse=True)
            for rank, candidate in enumerate(sorted_candidates, 1):
                cand_name = os.path.basename(candidate['file']).replace('candidate_', '').replace('.md', '')
                f.write(f"| {rank} | {cand_name} | {candidate['jack_score']:.2f} | {candidate['jill_score']:.2f} | {candidate['avg_score']:.2f} | {candidate['decision']} |\n")
            
            f.write("\n")
            
            # Detailed discussions
            f.write(f"### 💬 Detailed Discussions\n\n")
            
            for cand_idx, candidate in enumerate(sorted_candidates, 1):
                cand_name = os.path.basename(candidate['file'])
                
                f.write(f"#### {cand_idx}. {cand_name}\n\n")
                f.write(f"**Decision:** {candidate['decision']} (Avg: {candidate['avg_score']:.2f})\n\n")
                
                f.write(f"**🤖 Jack's Analysis** (Score: {candidate['jack_score']:.2f})\n\n")
                f.write(f"{candidate['jack_analysis']}\n\n")
                
                f.write(f"**🤖 Jill's Review** (Score: {candidate['jill_score']:.2f})\n\n")
                f.write(f"{candidate['jill_analysis']}\n\n")
                
                f.write("---\n\n")
            
            f.write("\n\n")
    
    print(f"\n{'='*70}")
    print(f"✅ All jobs processed!")
    print(f"\n📄 Reports saved to:")
    print(f"   - {json_file}")
    print(f"   - {markdown_file}")
    print(f"\n💡 Open the .md file to see full discussions per job!")
    print(f"{'='*70}\n")

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment variables.")
        return
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    
    print("\n" + "="*70)
    print("🎯 JACK & JILL - JOB-FOCUSED MATCH DISCUSSIONS")
    print("="*70)
    print("\nHow it works:")
    print("1. For each job, Jack screens ALL candidates")
    print("2. Jack shortlists top 3-5 matches (score >= 0.5)")
    print("3. Jack sends detailed analysis to Jill")
    print("4. Jill reviews only the shortlist")
    print("5. Final rankings and decisions per job")
    print("\nResult: One focused discussion per job, not per candidate!")
    print("\nReady? Press Enter to start...")
    input()
    
    discuss_job_matches(model)

if __name__ == "__main__":
    main()
