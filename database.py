import sqlite3
import os
import datetime

class ElectionDatabase:
    def __init__(self, db_path="data/voting_db.db"):
        self.db_path = db_path
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.create_tables()
        self.initialize_default_admin()

    def connect(self):
        """Returns a connection to the SQLite database."""
        return sqlite3.connect(self.db_path)

    def create_tables(self):
        """Creates all necessary tables for the voting system."""
        conn = self.connect()
        cursor = conn.cursor()
        
        # 1. SETTINGS TABLE (Stores Status and Election Times)
        cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')
        
        # Initialize default settings if not present
        defaults = [
            ('election_status', 'stopped'),
            ('election_start_time', '07:00'),
            ('election_end_time', '18:00')
        ]
        cursor.executemany("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", defaults)

        # 2. Master Voters Table (UPDATED with is_active)
        cursor.execute('''CREATE TABLE IF NOT EXISTS voters (
            reg_no TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            class TEXT,
            department TEXT, 
            fingerprint_template BLOB,
            has_voted INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1
        )''')

        # 3. Admins Table
        cursor.execute('''CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )''')

        # 4. Candidates Table
        cursor.execute('''CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            logo_path TEXT,
            vote_count INTEGER DEFAULT 0
        )''')

        # 5. Election Enrollment List
        cursor.execute('''CREATE TABLE IF NOT EXISTS election_voter_list (
            reg_no TEXT PRIMARY KEY,
            FOREIGN KEY(reg_no) REFERENCES voters(reg_no)
        )''')

        # 6. Audit Logs
        cursor.execute('''CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            action TEXT,
            details TEXT
        )''')

        conn.commit()
        conn.close()

    def initialize_default_admin(self):
        """Creates the first admin account and the NOTA option if they don't exist."""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM admins")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO admins (username, password) VALUES (?, ?)", 
                           ("admin", "admin123"))
        
        cursor.execute("SELECT * FROM candidates WHERE id = 0")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO candidates (id, name, logo_path, vote_count) VALUES (0, 'NOTA', '', 0)")
            
        conn.commit()
        conn.close()

    # --- ELECTION CONTROL & SETTINGS ---

    def get_setting(self, key):
        """Helper to get a single setting value."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def get_all_settings(self):
        """Returns all settings as a dictionary for the Admin Panel."""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM settings")
            data = dict(cursor.fetchall())
            conn.close()
            return data
        except:
            return {}

    def update_setting(self, key, value):
        """Helper to update a setting value."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("UPDATE settings SET value = ? WHERE key = ?", (value, key))
        conn.commit()
        conn.close()

    def is_election_time_valid(self):
        """Checks if current system time is within the set election hours."""
        try:
            settings = self.get_all_settings()
            status = settings.get('election_status', 'stopped')
            
            if status != 'active':
                return False, "The election is currently STOPPED by the administrator."

            now = datetime.datetime.now().time()
            start_str = settings.get('election_start_time', '07:00')
            end_str = settings.get('election_end_time', '18:00')
            
            start_time = datetime.datetime.strptime(start_str, "%H:%M").time()
            end_time = datetime.datetime.strptime(end_str, "%H:%M").time()

            if now < start_time:
                formatted_start = start_time.strftime("%I:%M %p")
                return False, f"Voting has not started yet. Please come back at {formatted_start}."
            
            if now > end_time:
                formatted_end = end_time.strftime("%I:%M %p")
                return False, f"Voting is now CLOSED. It ended at {formatted_end}."
            
            return True, "Election is currently LIVE."

        except Exception as e:
            return False, f"Error validating election time: {e}"

    # --- VOTER MANAGEMENT ---

    def check_fingerprint_exists(self, new_template, scanner_obj):
        """Checks if a fingerprint belongs to any currently ACTIVE voter."""
        all_voters = self.get_all_voters_with_biometrics()
        for voter in all_voters:
            reg_no, name, _, _, stored_blob, _ = voter
            if stored_blob:
                if isinstance(stored_blob, memoryview):
                    stored_blob = stored_blob.tobytes()
                try:
                    if scanner_obj.verify_match(stored_blob, new_template):
                        return True, f"{name} ({reg_no})"
                except Exception as e:
                    print(f"Error during biometric comparison: {e}")
        return False, None

    def add_voter(self, reg_no, name, v_class, dep, template):
        """Adds a new voter as 'active' by default."""
        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO voters (reg_no, name, class, department, fingerprint_template, is_active) 
                VALUES (?, ?, ?, ?, ?, 1)
            """, (reg_no, name, v_class, dep, template))
            cursor.execute("INSERT OR IGNORE INTO election_voter_list (reg_no) VALUES (?)", (reg_no,))
            conn.commit()
            self.log_event("VOTER_REGISTRATION", f"Registered: {name} ({reg_no})")
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def get_all_voters_with_biometrics(self):
        """Fetches only ACTIVE voters from the database."""
        conn = self.connect()
        cursor = conn.cursor()
        # Only select students where is_active is 1
        cursor.execute("""
            SELECT reg_no, name, class, department, fingerprint_template, has_voted 
            FROM voters 
            WHERE is_active = 1
        """)
        voters = cursor.fetchall()
        conn.close()
        return voters

    # --- VOTING LOGIC ---

    def cast_vote(self, reg_no, candidate_id):
        """Records a vote and updates candidate count."""
        is_valid, _ = self.is_election_time_valid()
        if not is_valid:
            return False

        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE voters SET has_voted = 1 WHERE reg_no = ?", (reg_no,))
            cursor.execute("UPDATE candidates SET vote_count = vote_count + 1 WHERE id = ?", (candidate_id,))
            conn.commit()
            self.log_event("VOTE_CAST", f"Voter {reg_no} successfully voted for Candidate ID {candidate_id}")
            return True
        except Exception as e:
            conn.rollback()
            print(f"Vote casting failed: {e}")
            return False
        finally:
            conn.close()

    def get_candidates(self):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, logo_path FROM candidates WHERE id != 0")
        candidates = cursor.fetchall()
        conn.close()
        return candidates

    def log_event(self, action, details):
        """Logs important system actions for audit trails."""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO audit_logs (timestamp, action, details) VALUES (?, ?, ?)", 
                           (timestamp, action, details))
            conn.commit()
            conn.close()
        except:
            pass
