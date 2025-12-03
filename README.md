# 🎯 AI Recruiter System

An intelligent, voice-based recruitment system where AI agents (Jack & Jill) interview people and then discuss matches together.

---

## 🚀 Quick Start Workflow

### **1. Interview Hiring Manager (Jill)**
**Goal:** Create a Job Specification.
```bash
python jill_agent.py
```
- **Voice Interview:** Jill asks you about the role, company, and requirements.
- **Optional Input:** Create `job_input.txt` beforehand to pre-load details (auto-deleted after use).
- **Optional Upload:** At the end, Jill asks if you have a JD file to upload (cross-references it).
- **Output:** Saves a job spec to `jobs/` folder.

### **2. Interview Candidates (Jack)**
**Goal:** Create Candidate Profiles.
```bash
python jack_agent.py
```
- **Voice Interview:** Jack asks you about your experience, education, and behavioral scenarios.
- **Optional Input:** Create `cv_input.txt` beforehand to pre-load your CV (auto-deleted after use).
- **Optional Upload:** At the end, Jack asks if you have a CV file to upload (cross-references it).
- **Output:** Saves a candidate profile to `candidates/` folder.

### **3. Match & Discuss (The Magic ✨)**
**Goal:** Agents discuss candidates and decide who to interview.
```bash
python discuss_matches.py
```
- **Process:**
  1. Jack screens ALL candidates for each job.
  2. Jack shortlists the top 3-5 matches.
  3. Jill reviews the shortlist.
  4. They agree on a decision: 🎯 INTERVIEW, ⚠️ BACKUP, or ❌ PASS.
- **Output:** Generates detailed reports in `matches/` folder.

### **4. View Results**
**Goal:** See what happened.
- **Match Reports:** Open `matches/job_discussions_*.md` (Best for reading rankings & decisions).
- **Full Log:** Open `conversation_log.md` (Chronological history of everything).
- **Check Messages:** Run `python check_messages.py` to see the internal message queue.

---

## 📂 Key Files
- `jack_agent.py`: Candidate interviewer.
- `jill_agent.py`: Hiring manager interviewer.
- `discuss_matches.py`: The matching engine.
- `check_messages.py`: Message viewer.
- `candidates/`: Where candidate profiles live.
- `jobs/`: Where job specs live.
- `matches/`: Where final decisions live.

## 🔒 Security Note
- Any input files (`cv_input.txt`, `job_input.txt`, etc.) are **automatically deleted** after being read to prevent data leakage between users.

## 🛠️ Setup
1. Install requirements: `pip install -r requirements.txt`
2. Add API key to `.env`: `GEMINI_API_KEY=your_key`
3. Run the scripts!
