import os
import sys
import time
import re
from groq import Groq
from dotenv import load_dotenv
import speech_recognition as sr
import pyttsx3

# Load environment variables
load_dotenv()
# Global Groq client
client = None

def init_groq():
    """Initialize Groq client"""
    global client
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY not found in environment variables.")
        print("Please create a .env file with GROQ_API_KEY=your_key")
        sys.exit(1)
    client = Groq(api_key=api_key)
    return client

def groq_call(messages, model="llama-3.3-70b-versatile", temperature=0.7):
    """Helper to call Groq API"""
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature
    )
    return response.choices[0].message.content


def load_system_prompt():
    try:
        with open("prompts/jill_persona.md", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print("Error: prompts/jill_persona.md not found.")
        sys.exit(1)

def init_engine():
    """Initializes the TTS engine with female voice and slower speed."""
    engine = pyttsx3.init()
    
    # Set Rate (Speed) - Slower for better clarity
    rate = engine.getProperty('rate')
    engine.setProperty('rate', rate)  # Standard speed (removed slowdown)
    
    # Set Voice (Female)
    voices = engine.getProperty('voices')
    target_voice = None
    
    # Look for "Zira" (common Windows female voice) or just "Female"
    for voice in voices:
        if "zira" in voice.name.lower() or "female" in voice.name.lower():
            target_voice = voice.id
            break
            
    if target_voice:
        engine.setProperty('voice', target_voice)
    else:
        print("Warning: No female voice found. Using default.")
            
    return engine

def speak(text):
    """Speaks the text using a fresh engine instance."""
    try:
        # Clean text for speech: remove ALL markdown and asterisks
        clean_text = re.sub(r'\*.*?\*', '', text)  # Remove *text*
        clean_text = clean_text.replace("*", "")  # Remove standalone asterisks
        clean_text = clean_text.replace("#", "").replace("- ", "")
        
        print(f"[Debug] Speaking: {clean_text[:50]}...")
        engine = init_engine()
        engine.say(clean_text)
        engine.runAndWait()
        print("[Debug] Speech finished.")
    except Exception as e:
        print(f"Error in TTS: {e}")

def listen():
    """Listens to the microphone and returns text."""
    r = sr.Recognizer()
    r.pause_threshold = 1.5  # Wait 1.5 seconds before processing
    
    with sr.Microphone() as source:
        print("\nListening... (Speak now)")
        # Adjust for ambient noise - reduced duration for faster response
        r.adjust_for_ambient_noise(source, duration=0.3)
        try:
            audio = r.listen(source, timeout=10, phrase_time_limit=None)
            print("Recognizing...")
            text = r.recognize_google(audio)
            print(f"You said: {text}")
            return text
        except sr.WaitTimeoutError:
            message = "I can't hear you. Could you please repeat that?"
            print(f"Jill: {message}")
            speak(message)
            return None
        except sr.UnknownValueError:
            message = "I didn't catch that. Could you say it again?"
            print(f"Jill: {message}")
            speak(message)
            return None
        except sr.RequestError as e:
            print(f"Could not request results; {e}")
            return None

def generate_job_spec(messages, jd_content=None):
    """Generates a job specification document based on the conversation and optional job description."""
    print("\n📝 Generating Job Requirement One-Pager...")
    try:
        # Add JD cross-reference if provided
        jd_context = ""
        if jd_content:
            jd_context = f"""

IMPORTANT: The hiring manager has also provided a written job description. Use this to:
1. Cross-reference factual details (requirements, qualifications, responsibilities)
2. Fill in any gaps from the conversation
3. Validate what was discussed
4. Add any additional relevant details not mentioned

JOB DESCRIPTION PROVIDED:
---
{jd_content}
---

If there are any discrepancies between the conversation and the job description, note them in the spec.
"""
        
        prompt = f"""Based on our comprehensive conversation, please generate a detailed Job Requirement One-Pager. 
        
        {jd_context}
        Include ALL of the following sections:
        - **Company Overview** (What they do, industry, mission. If startup: funding stage, runway, growth/traction)
        - **Team Context** (What the team does, team size, reporting structure)
        - **Role Expectations** (Day-to-day responsibilities, key deliverables in first 3/6 months, projects to own)
        - **Required Skills** (Technical/hard skills, years of experience, industry/company background, education/certifications)
        - **Nice-to-Have Skills** (Bonus skills that aren't dealbreakers)
        - **Cultural & Behavioral Fit** (Personality traits that succeed, working style, red flags to avoid)
        - **Compensation** (Salary range - base + bonus, equity/stock options, benefits)
        - **Location & Relocation** (Office location, remote/hybrid/on-site policy, open to relocation?, relocation support)
        
        CRITICAL: At the very beginning, include a line: "JOB_TITLE: [the job title]"
        
        Format it as a concise **ONE-PAGE SUMMARY**. Do not write a multi-page essay.
        Use bullet points and short paragraphs. Make it a clean, professional Markdown document.
        Be specific and cite examples from our conversation.
        """
        messages.append({"role": "user", "content": prompt})
        
        # Call Groq to generate
        model_name = "llama-3.3-70b-versatile"
        response_text = groq_call(messages, model_name)
        messages.append({"role": "assistant", "content": response_text})
        
        # Extract job title from response
        content = response_text
        job_title = "unknown"
        for line in content.split('\n'):
            if 'JOB_TITLE:' in line:
                job_title = line.split('JOB_TITLE:')[1].strip()
                content = content.replace(line, "").strip()
                break
        
        # Sanitize title for filename
        from datetime import datetime
        safe_title = re.sub(r'[^\w\s-]', '', job_title.lower())
        safe_title = re.sub(r'[-\s]+', '_', safe_title)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Ensure jobs directory exists
        os.makedirs("jobs", exist_ok=True)
        
        filename = f"jobs/job_{safe_title}_{timestamp}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
            
        print(f"✅ Job requirements saved to {filename}")
        
        # Persist to Database
        try:
            from database import add_job
            # Extract title/company from filename or use safe_title
            db_title = safe_title.replace("_", " ").title()
            
            add_job(
                title=db_title,
                company="Unknown", # TODO: Parse from content
                spec_file=filename,
                requirements=[] # TODO: extract requirements
            )
            print(f"✅ Job added to database: {db_title}")
        except Exception as db_e:
            print(f"❌ Error adding to database: {db_e}")
            
        return filename, content
    except Exception as e:
        print(f"❌ Error generating job spec: {e}")
        return None, None

def load_job_input():
    """Loads the initial job description from job_input.txt if it exists, then deletes it."""
    try:
        if os.path.exists("job_input.txt"):
            with open("job_input.txt", "r", encoding="utf-8") as f:
                content = f.read().strip()
            
            # Auto-delete to prevent reuse by next user
            try:
                os.remove("job_input.txt")
                print("✅ Found and loaded job_input.txt (File deleted for security)")
            except Exception as del_e:
                print(f"⚠️ Loaded job_input.txt but failed to delete it: {del_e}")
                
            return content
    except Exception as e:
        print(f"Warning: Could not read job_input.txt: {e}")
    return None

def load_candidate_profile():
    """Loads the candidate profile generated by Jack if it exists."""
    try:
        if os.path.exists("candidate_profile.md"):
            with open("candidate_profile.md", "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception as e:
        print(f"Warning: Could not read candidate_profile.md: {e}")
    return None

def check_for_candidate_matches(model, job_spec_content):
    """Check if job matches any available candidates and suggest to Jack."""
    from messaging import get_all_candidate_profiles, send_message
    
    candidate_files = get_all_candidate_profiles()
    
    if not candidate_files:
        print("\n📭 No candidate profiles available from Jack yet.")
        return
    
    print(f"\n🔍 Checking job against {len(candidate_files)} available candidate(s)...")
    
    for candidate_file in candidate_files:
        try:
            with open(candidate_file, "r", encoding="utf-8") as f:
                candidate_content = f.read()
            
            match_prompt = f"""Analyze this job requirement against the candidate profile.
            
JOB REQUIREMENTS:
---
{job_spec_content}
---

CANDIDATE PROFILE:
---
{candidate_content}
---

Provide:
1. Match Score (0.0-1.0, where 1.0 is perfect match)
2. Brief explanation of fit
3. Key strengths from candidate
4. Potential gaps or development areas

Format: Start with "MATCH_SCORE: X.XX" then your analysis."""

            match_messages = [{"role": "user", "content": match_prompt}]
            analysis = groq_call(match_messages)
            
            score_line = [line for line in analysis.split('\n') if 'MATCH_SCORE' in line]
            match_score = 0.0
            if score_line:
                try:
                    match_score = float(score_line[0].split(':')[1].strip())
                except:
                    match_score = 0.5
            
            if match_score >= 0.6:
                message = f"""🎯 JOB MATCH SUGGESTION

I think the candidate from {candidate_file} could be a great fit for this role!

Match Score: {match_score:.2f}/1.0

{analysis}

Would you like me to reach out to see if they're interested?"""

                send_message("Jill", "Jack", "match_suggestion", message, {
                    "candidate_file": candidate_file,
                    "job_file": "job_requirements.md",
                    "match_score": match_score
                })
                
                print(f"✅ Sent match suggestion to Jack (Score: {match_score:.2f})")
            else:
                print(f"⚠️  Low match for {candidate_file} (Score: {match_score:.2f}) - not suggesting")
                
        except Exception as e:
            print(f"Error analyzing match for {candidate_file}: {e}")


def main():
    init_groq()

    system_prompt = load_system_prompt()
    
    # Initialize database
    from database import init_database, get_agent_messages, mark_message_read, add_job
    init_database()
    
    # Read messages from Jack (legacy system) - REMOVED
    # from messaging import read_messages
    # print("\n📬 Checking messages from Jack...")
    # messages = read_messages("Jill")
    
    # if messages:
    #     print(f"\n💬 You have {len(messages)} new message(s) from Jack:\n")
    #     for msg in messages:
    #         print(f"[{msg['timestamp']}] {msg['type'].replace('_', ' ').title()}:")
    #         print(f"{msg['content']}\n")
    #         print("---\n")
    # else:
    #     print("No new messages from Jack.\n")
    
    # Check for Scout recommendations (new system)
    print("🔍 Checking Scout recommendations...")
    scout_messages = get_agent_messages("Jill", unread_only=True)
    
    if scout_messages:
        print(f"\n🎯 Scout found {len(scout_messages)} recommendation(s):\n")
        for msg in scout_messages:
            import json
            metadata = json.loads(msg['metadata']) if msg['metadata'] else {}
            print(f"   [{msg['message_type']}] {msg['content']}")
            
            # If it's an outreach opportunity (jobs found for a candidate)
            if msg['message_type'] == 'outreach_opportunity':
                jobs = metadata.get('jobs', [])
                candidate_name = metadata.get('candidate_name', 'Unknown')
                print(f"   Candidate: {candidate_name}")
                print(f"   Found {len(jobs)} companies to reach out to:")
                for j in jobs[:3]:
                    company = j.get('company', 'Unknown')
                    title = j.get('title', 'Unknown')
                    print(f"      • {company} - {title[:30]}...")
                print()
            
            mark_message_read(msg['id'])
        
        print("   💡 Run `python linkedin_outreach.py` to generate hiring manager messages.\n")
    else:
        print("No new Scout recommendations.\n")
    
    job_input = load_job_input()
    candidate_profile = load_candidate_profile()
    
    model_name = "llama-3.3-70b-versatile"
    
    try:
        messages = [{"role": "system", "content": system_prompt}]

        # Using messages array for Groq
        
        context_parts = []
        if job_input:
            context_parts.append(f"The user has provided an initial job description:\n---\n{job_input}\n---")
        if candidate_profile:
            context_parts.append(f"Jack has provided a candidate profile from a previous interview:\n---\n{candidate_profile}\n---")
            
        if context_parts:
            context_prompt = "\n".join(context_parts) + "\n\nPlease acknowledge these details. If a Candidate Profile is provided, mention if they might be a fit for this new role or if we need a different profile. Start the conversation naturally."
            print(f"\n📄 Loading Context (Job Input: {'Yes' if job_input else 'No'}, Candidate Profile: {'Yes' if candidate_profile else 'No'})...")
            messages.append({"role": "user", "content": context_prompt})
            intro_text = groq_call(messages, model_name)
            messages.append({"role": "assistant", "content": intro_text})
        else:
            intro_text = "Hello! I'm Jill, your Talent Acquisition Partner. It's a pleasure to meet you. How can I help you build your team today? What role are we looking to fill?"

        print(f"Jill (Talent Acquisition) [{model_name}]: {intro_text}")
        speak(intro_text)

        while True:
            try:
                user_input = listen()
                
                if not user_input:
                    continue

                # Check for exit keywords BEFORE sending to AI
                if user_input.lower() in ['quit', 'exit', 'stop', 'goodbye']:
                    # DON'T send "goodbye" to the AI, handle it directly
                    jd_content = job_input
                    
                    if not jd_content:
                        # Ask for job description file upload ONLY if not provided at start
                        jd_request = "Before we finish - do you have a written job spec to share? If yes, paste it into 'job_description.txt' and say 'ready'. Otherwise, say 'no'."
                        print(f"\nJill: {jd_request}")
                        speak(jd_request)
                        
                        # Wait for response
                        jd_response = listen()
                        
                        if jd_response and jd_response.lower() in ['ready', 'yes', 'done', 'uploaded']:
                            # Try to read job description
                            if os.path.exists("job_description.txt"):
                                try:
                                    with open("job_description.txt", "r", encoding="utf-8") as f:
                                        jd_content = f.read()
                                    confirm_msg = "Thanks! I've got the job description. I'll use this to cross-reference our conversation."
                                    print(f"\nJill: {confirm_msg}")
                                    speak(confirm_msg)
                                    
                                    # Delete file immediately to prevent reuse
                                    os.remove("job_description.txt")
                                    print("✅ Job description processed and file deleted")
                                except Exception as e:
                                    print(f"⚠️ Couldn't read job description file: {e}")
                            else:
                                wait_msg = "I don't see the job_description.txt file yet. Let me know when it's ready by saying 'ready'."
                                print(f"\nJill: {wait_msg}")
                                speak(wait_msg)
                                
                                # Give one more chance
                                second_response = listen()
                                if second_response and os.path.exists("job_description.txt"):
                                    try:
                                        with open("job_description.txt", "r", encoding="utf-8") as f:
                                            jd_content = f.read()
                                        os.remove("job_description.txt")
                                        print("✅ Job description processed and file deleted")
                                    except:
                                        pass
                    
                        if not jd_content:
                            no_jd_msg = "No problem! I'll create the job spec based on our conversation."
                            print(f"\nJill: {no_jd_msg}")
                            speak(no_jd_msg)
                    
                    # Generate job spec with optional JD cross-reference
                    result = generate_job_spec(messages, jd_content=jd_content)
                    
                    if result and result[0]:
                        filename, job_spec_content = result
                        
                        # Approval loop - allow iterative refinement
                        while True:
                            # Show the document to user (don't read it aloud)
                            print("\n" + "="*60)
                            print("📄 JOB SPECIFICATION GENERATED")
                            print("="*60)
                            print(job_spec_content)
                            print("="*60)
                            
                            # Ask for approval - REMOVED (Auto-save now)
                            # approval_message = "I've generated the job specification above..."
                            # print(f"\nJill: {approval_message}")
                            # speak(approval_message)
                            
                            # Wait for approval - REMOVED (Auto-save now)
                            approval = "yes"  # Auto-approve
                            
                            if approval and approval.lower() in ['yes', 'yeah', 'yep', 'sure', 'approve', 'good', 'looks good', 'perfect']:
                                # Save and share
                                # from messaging import send_message - REMOVED
                                
                                # Overwrite file with latest content
                                with open(filename, "w", encoding="utf-8") as f:
                                    f.write(job_spec_content)
                                
                                # send_message("Jill", "Jack", "job_spec", ...) - REMOVED
                                
                                print(f"📤 Saved job spec (Jack will see it in the DB)")
                                # check_for_candidate_matches(model, job_spec_content) - Moved to run_recruiting_loop.py
                                
                                success_msg = "Perfect! I've saved it and shared it with Jack. He'll start looking for matching candidates right away. Goodbye!"
                                print(f"\nJill: {success_msg}")
                                speak(success_msg)
                                break  # Exit approval loop
                            else:
                                # Ask for changes
                                changes_msg = "No problem! What would you like me to change or add?"
                                print(f"\nJill: {changes_msg}")
                                speak(changes_msg)
                                
                                # Get user feedback
                                feedback = listen()
                                
                                if not feedback:
                                    continue
                                
                                # Generate updated version
                                update_prompt = f"""The user wants changes to the job specification. Here's the current version:

---
{job_spec_content}
---

User feedback: {feedback}

Please generate an UPDATED version incorporating their feedback. Keep the same format and structure, but make the requested changes. Include the "JOB_TITLE: [title]" line at the beginning."""

                                print("\n🔄 Updating job specification...")
                                update_messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": update_prompt}]
                                updated_content = groq_call(update_messages)
                                
                                # Extract updated content
                                for line in updated_content.split('\n'):
                                    if 'JOB_TITLE:' in line:
                                        updated_content = updated_content.replace(line, "").strip()
                                        break
                                
                                job_spec_content = updated_content
                                print("✅ Updated!")
                                # Loop back to show updated version
                    else:
                        error_msg = "I had trouble generating the job spec. Let me know if you'd like to try again. Goodbye!"
                        print(f"Jill: {error_msg}")
                        speak(error_msg)
                    break  # Exit main conversation loop

                messages.append({"role": "user", "content": user_input})
                response_text = groq_call(messages, model_name)
                messages.append({"role": "assistant", "content": response_text})
                print(f"\nJill: {response_text}")
                speak(response_text)

            except KeyboardInterrupt:
                print("\nJill: Goodbye!")
                break
            except Exception as e:
                print(f"\nAn error occurred during chat: {e}")

    except Exception as e:
        print(f"\nError initializing model '{model_name}': {e}")
        print("\nListing available models...")
        try:
            with open("models.txt", "w") as f:
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        print(f"- {m.name}")
                        f.write(f"{m.name}\n")
            print("Models written to models.txt")
        except Exception as list_e:
            print(f"Could not list models: {list_e}")
        print("\nPlease update the 'model_name' in jill_agent.py to one of the available models above.")

if __name__ == "__main__":
    main()
