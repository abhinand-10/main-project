import sqlite3
import os

class ElectionDatabase:
    def __init__(self, db_path="data/voting_db.db"):
        self.db_path = db_path
        # Create data folder if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.create_tables()

    def connect(self):
        """Creates and returns a connection to the database."""
        return sqlite3.connect(self.db_path)

    def create_tables(self):
        conn = self.connect()
        cursor = conn.cursor()
        
        # 1. Voter Master Table: 'department' കോളം കൂടി ചേർത്തു
        cursor.execute('''CREATE TABLE IF NOT EXISTS voters (
            reg_no TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            class TEXT,
            department TEXT, 
            fingerprint_template BLOB,
            has_voted INTEGER DEFAULT 0
        )''')

        # 2. Candidate Table: Stores election participants
        cursor.execute('''CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            logo_path TEXT,
            vote_count INTEGER DEFAULT 0
        )''')

        # 3. Active Election List: Links registered voters to the current election
        cursor.execute('''CREATE TABLE IF NOT EXISTS election_voter_list (
            reg_no TEXT PRIMARY KEY,
            FOREIGN KEY(reg_no) REFERENCES voters(reg_no)
        )''')

        # 4. Admin Table: For secure login
        cursor.execute('''CREATE TABLE IF NOT EXISTS admin (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )''')

        conn.commit()
        conn.close()

    def add_voter(self, reg_no, name, v_class, dep, template):
        """Department (dep) കൂടി സ്വീകരിക്കുന്ന രീതിയിൽ അപ്‌ഡേറ്റ് ചെയ്തു."""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            # 5 വാല്യൂസ് INSERT ചെയ്യുന്നു
            cursor.execute("INSERT INTO voters (reg_no, name, class, department, fingerprint_template) VALUES (?, ?, ?, ?, ?)", 
                           (reg_no, name, v_class, dep, template))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding voter: {e}")
            return False

    def cast_vote(self, reg_no, candidate_id):
        """Function to cast a vote and update counts."""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            # 1. Update Candidate vote count
            cursor.execute("UPDATE candidates SET vote_count = vote_count + 1 WHERE id = ?", (candidate_id,))
            # 2. Mark Voter as 'voted'
            cursor.execute("UPDATE voters SET has_voted = 1 WHERE reg_no = ?", (reg_no,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Vote failed: {e}")
            return False