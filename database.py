"""
Database Layer for AI Recruiter Multi-Agent System
SQLite-based storage for candidates, jobs, matches, and agent communication.
"""

import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path

DATABASE_PATH = Path(__file__).parent / "data" / "recruiter.db"

def get_connection():
    """Get a database connection, creating the database if it doesn't exist."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Enable dict-like access
    return conn

def init_database():
    """Initialize the database schema."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Candidates table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            linkedin_url TEXT,
            profile_file TEXT,
            skills TEXT,
            preferences TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Jobs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            title TEXT,
            company TEXT,
            linkedin_url TEXT,
            spec_file TEXT,
            requirements TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Matches table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            id TEXT PRIMARY KEY,
            candidate_id TEXT,
            job_id TEXT,
            score REAL,
            source TEXT,
            status TEXT DEFAULT 'pending',
            jack_notes TEXT,
            jill_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id),
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
    ''')
    
    # Outreach queue table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS outreach_queue (
            id TEXT PRIMARY KEY,
            target_type TEXT,
            target_name TEXT,
            target_linkedin_url TEXT,
            message TEXT,
            status TEXT DEFAULT 'pending',
            sent_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Agent messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agent_messages (
            id TEXT PRIMARY KEY,
            from_agent TEXT,
            to_agent TEXT,
            message_type TEXT,
            content TEXT,
            metadata TEXT,
            read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

# ============================================================
# CANDIDATE OPERATIONS
# ============================================================

def add_candidate(name, email=None, linkedin_url=None, profile_file=None, skills=None, preferences=None):
    """Add a new candidate to the database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    candidate_id = str(uuid.uuid4())[:8]
    cursor.execute('''
        INSERT INTO candidates (id, name, email, linkedin_url, profile_file, skills, preferences)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        candidate_id,
        name,
        email,
        linkedin_url,
        profile_file,
        json.dumps(skills) if skills else None,
        json.dumps(preferences) if preferences else None
    ))
    
    conn.commit()
    conn.close()
    return candidate_id

def get_candidate(candidate_id):
    """Get a candidate by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM candidates WHERE id = ?', (candidate_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_candidates():
    """Get all candidates."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM candidates ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# ============================================================
# JOB OPERATIONS
# ============================================================

def add_job(title, company, linkedin_url=None, spec_file=None, requirements=None):
    """Add a new job to the database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    job_id = str(uuid.uuid4())[:8]
    cursor.execute('''
        INSERT INTO jobs (id, title, company, linkedin_url, spec_file, requirements)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        job_id,
        title,
        company,
        linkedin_url,
        spec_file,
        json.dumps(requirements) if requirements else None
    ))
    
    conn.commit()
    conn.close()
    return job_id

def get_job(job_id):
    """Get a job by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM jobs WHERE id = ?', (job_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_jobs():
    """Get all jobs."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM jobs ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# ============================================================
# MATCH OPERATIONS
# ============================================================

def add_match(candidate_id, job_id, score, source='jack_jill'):
    """Add a new match to the database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    match_id = str(uuid.uuid4())[:8]
    cursor.execute('''
        INSERT INTO matches (id, candidate_id, job_id, score, source)
        VALUES (?, ?, ?, ?, ?)
    ''', (match_id, candidate_id, job_id, score, source))
    
    conn.commit()
    conn.close()
    return match_id

def get_matches_for_job(job_id):
    """Get all matches for a specific job."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT m.*, c.name as candidate_name, c.linkedin_url as candidate_linkedin
        FROM matches m
        JOIN candidates c ON m.candidate_id = c.id
        WHERE m.job_id = ?
        ORDER BY m.score DESC
    ''', (job_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_matches_for_candidate(candidate_id):
    """Get all matches for a specific candidate."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT m.*, j.title as job_title, j.company
        FROM matches m
        JOIN jobs j ON m.job_id = j.id
        WHERE m.candidate_id = ?
        ORDER BY m.score DESC
    ''', (candidate_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_match_status(match_id, status, jack_notes=None, jill_notes=None):
    """Update a match's status and notes."""
    conn = get_connection()
    cursor = conn.cursor()
    
    updates = ['status = ?']
    params = [status]
    
    if jack_notes:
        updates.append('jack_notes = ?')
        params.append(jack_notes)
    if jill_notes:
        updates.append('jill_notes = ?')
        params.append(jill_notes)
    
    params.append(match_id)
    cursor.execute(f'UPDATE matches SET {", ".join(updates)} WHERE id = ?', params)
    
    conn.commit()
    conn.close()

# ============================================================
# OUTREACH QUEUE OPERATIONS
# ============================================================

def queue_outreach(target_type, target_name, target_linkedin_url, message):
    """Add an outreach message to the queue."""
    conn = get_connection()
    cursor = conn.cursor()
    
    outreach_id = str(uuid.uuid4())[:8]
    cursor.execute('''
        INSERT INTO outreach_queue (id, target_type, target_name, target_linkedin_url, message)
        VALUES (?, ?, ?, ?, ?)
    ''', (outreach_id, target_type, target_name, target_linkedin_url, message))
    
    conn.commit()
    conn.close()
    return outreach_id

def get_pending_outreach():
    """Get all pending outreach messages."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM outreach_queue WHERE status = "pending" ORDER BY created_at')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def mark_outreach_sent(outreach_id):
    """Mark an outreach message as sent."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE outreach_queue 
        SET status = "sent", sent_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    ''', (outreach_id,))
    conn.commit()
    conn.close()

# ============================================================
# AGENT MESSAGE OPERATIONS
# ============================================================

def send_agent_message(from_agent, to_agent, message_type, content, metadata=None):
    """Send a message between agents."""
    conn = get_connection()
    cursor = conn.cursor()
    
    msg_id = str(uuid.uuid4())[:8]
    cursor.execute('''
        INSERT INTO agent_messages (id, from_agent, to_agent, message_type, content, metadata)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (msg_id, from_agent, to_agent, message_type, content, json.dumps(metadata) if metadata else None))
    
    conn.commit()
    conn.close()
    return msg_id

def get_agent_messages(to_agent, unread_only=True, message_type=None):
    """Get messages for an agent."""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = 'SELECT * FROM agent_messages WHERE to_agent = ?'
    params = [to_agent]
    
    if unread_only:
        query += ' AND read = 0'
    if message_type:
        query += ' AND message_type = ?'
        params.append(message_type)
    
    query += ' ORDER BY created_at DESC'
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def mark_message_read(message_id):
    """Mark a message as read."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE agent_messages SET read = 1 WHERE id = ?', (message_id,))
    conn.commit()
    conn.close()

# Initialize on import
if __name__ == "__main__":
    init_database()
    print(f"Database created at: {DATABASE_PATH}")
