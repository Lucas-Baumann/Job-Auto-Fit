import sqlite3
import hashlib
from datetime import datetime
from config import Config

def get_db_connection():
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_hash TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT,
            url TEXT,
            platform TEXT NOT NULL,
            description TEXT,
            contact_email TEXT,
            match_score INTEGER DEFAULT 0,
            match_reason TEXT,
            status TEXT DEFAULT 'pending', -- pending, ats_done, applied, skipped, failed
            resume_pdf_path TEXT,
            cover_letter_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            applied_at TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def generate_job_hash(title: str, company: str, url: str) -> str:
    raw = f"{title.lower()}:{company.lower()}:{url.lower()}"
    return hashlib.md5(raw.encode('utf-8')).hexdigest()

def is_job_processed(job_hash: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM jobs WHERE job_hash = ?", (job_hash,))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def save_job(job_data: dict) -> int:
    job_hash = generate_job_hash(job_data['title'], job_data['company'], job_data.get('url', ''))
    if is_job_processed(job_hash):
        return -1
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO jobs (
            job_hash, title, company, location, url, platform, description, contact_email, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        job_hash,
        job_data['title'],
        job_data['company'],
        job_data.get('location', ''),
        job_data.get('url', ''),
        job_data.get('platform', 'unknown'),
        job_data.get('description', ''),
        job_data.get('contact_email', ''),
        job_data.get('status', 'pending')
    ))
    conn.commit()
    job_id = cursor.lastrowid
    conn.close()
    return job_id

def update_job_match(job_id: int, score: int, reason: str, status: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if status:
        cursor.execute("UPDATE jobs SET match_score = ?, match_reason = ?, status = ? WHERE id = ?", (score, reason, status, job_id))
    else:
        cursor.execute("UPDATE jobs SET match_score = ?, match_reason = ? WHERE id = ?", (score, reason, job_id))
    conn.commit()
    conn.close()

def update_job_status(job_id: int, status: str, resume_path: str = None, cover_path: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    applied_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if status == 'applied' else None
    
    cursor.execute("""
        UPDATE jobs 
        SET status = ?, 
            resume_pdf_path = COALESCE(?, resume_pdf_path),
            cover_letter_path = COALESCE(?, cover_letter_path),
            applied_at = COALESCE(?, applied_at)
        WHERE id = ?
    """, (status, resume_path, cover_path, applied_at, job_id))
    conn.commit()
    conn.close()

def get_all_jobs_in_session(start_time_iso: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if start_time_iso:
        cursor.execute("SELECT * FROM jobs WHERE created_at >= ? ORDER BY id DESC", (start_time_iso,))
    else:
        cursor.execute("SELECT * FROM jobs ORDER BY id DESC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows
