#!/usr/bin/env python3
"""
Library Management System - Database Schema
Creates SQLite database with proper tables for the library seat booking system
"""

import sqlite3
import hashlib
from datetime import datetime, timedelta
import os

class DatabaseManager:
    def __init__(self, db_path="library_database.db"):
        self.db_path = db_path
        self._setup_wal_mode()
        self.init_database()
    
    def _setup_wal_mode(self):
        """Setup WAL mode once during initialization"""
        conn = sqlite3.connect(self.db_path, timeout=60.0)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        conn.execute('PRAGMA cache_size=10000')  # Larger cache
        conn.execute('PRAGMA temp_store=MEMORY')  # Use memory for temp tables
        conn.close()
    
    def get_connection(self):
        """Get database connection with timeout and proper settings"""
        conn = sqlite3.connect(self.db_path, timeout=60.0, check_same_thread=False, isolation_level=None)
        conn.execute('PRAGMA busy_timeout=60000')  # 60 second timeout
        conn.execute('PRAGMA journal_mode=WAL')  # Ensure WAL mode
        return conn
    
    def init_database(self):
        """Initialize database with all required tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if bookings table has the new columns; if not, add them
        try:
            cursor.execute("PRAGMA table_info(bookings)")
            columns = [row[1] for row in cursor.fetchall()]
            
            # Add is_walk_in column if missing
            if 'is_walk_in' not in columns:
                print("🔄 Adding is_walk_in column to bookings table...")
                cursor.execute('ALTER TABLE bookings ADD COLUMN is_walk_in BOOLEAN DEFAULT 0')
                conn.commit()
            
            # Add walk_in_code column if missing
            if 'walk_in_code' not in columns:
                print("🔄 Adding walk_in_code column to bookings table...")
                cursor.execute('ALTER TABLE bookings ADD COLUMN walk_in_code TEXT')
                conn.commit()
            
            # Check if old schema without scanned_at exists
            if 'scanned_at' not in columns:
                print("🔄 Migrating bookings table schema...")
                cursor.execute('DROP TABLE IF EXISTS bookings')
                cursor.execute('DROP TABLE IF EXISTS daily_usage')
        except Exception as e:
            print(f"⚠️ Schema check warning: {e}")
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                roll_number TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                login_count INTEGER DEFAULT 0,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Seats table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS seats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seat_number TEXT UNIQUE NOT NULL,
                row_number INTEGER NOT NULL,
                column_number INTEGER NOT NULL,
                status TEXT DEFAULT 'available' CHECK(status IN ('available', 'booked', 'maintenance', 'reserved')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Bookings table - Enhanced with booking state and reallocation tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                seat_id INTEGER NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                duration_minutes INTEGER NOT NULL,
                status TEXT DEFAULT 'pending-scan' CHECK(status IN ('pending-scan', 'scanned', 'active', 'completed', 'cancelled', 'expired', 'leave-early', 'reallocated')),
                qr_code TEXT UNIQUE NOT NULL,
                booking_type TEXT DEFAULT 'solo' CHECK(booking_type IN ('solo', 'group')),
                group_id INTEGER,
                is_walk_in BOOLEAN DEFAULT 0,
                walk_in_code TEXT,
                scanned_at TIMESTAMP,
                left_early_at TIMESTAMP,
                reallocated_to_seat_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (seat_id) REFERENCES seats (id),
                FOREIGN KEY (reallocated_to_seat_id) REFERENCES seats (id),
                FOREIGN KEY (group_id) REFERENCES groups (id)
            )
        ''')
        
        # Groups table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                created_by INTEGER NOT NULL,
                status TEXT DEFAULT 'active' CHECK(status IN ('active', 'completed', 'cancelled')),
                max_members INTEGER DEFAULT 10,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')
        
        # Group members table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'accepted', 'declined')),
                invited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                responded_at TIMESTAMP,
                UNIQUE(group_id, user_id),
                FOREIGN KEY (group_id) REFERENCES groups (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Sessions table for authentication
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_token TEXT UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Admin users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                is_super_admin BOOLEAN DEFAULT FALSE,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (created_by) REFERENCES admins (id)
            )
        ''')
        
        # Approved students table (CSV uploads)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS approved_students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roll_number TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                status TEXT DEFAULT 'approved' CHECK(status IN ('approved', 'blocked', 'waiting')),
                uploaded_by INTEGER,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (uploaded_by) REFERENCES admins (id)
            )
        ''')
        
        # Blocked users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blocked_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                reason TEXT,
                blocked_by INTEGER NOT NULL,
                blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (blocked_by) REFERENCES admins (id)
            )
        ''')
        
        # Daily usage tracking (max 4 hours per user per day)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                usage_date DATE NOT NULL,
                total_minutes_used INTEGER DEFAULT 0,
                section_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, usage_date),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Book Categories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS book_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Books table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                isbn TEXT UNIQUE,
                category_id INTEGER,
                shelf_number TEXT,
                rack_number TEXT,
                total_copies INTEGER DEFAULT 1,
                available_copies INTEGER DEFAULT 1,
                cover_image_url TEXT,
                online_resource_link TEXT,
                description TEXT,
                publisher TEXT,
                publication_year INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES book_categories (id)
            )
        ''')
        
        # Book Issues/Borrowing table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS book_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                due_date TIMESTAMP NOT NULL,
                returned_at TIMESTAMP,
                status TEXT DEFAULT 'issued' CHECK(status IN ('issued', 'returned', 'overdue', 'lost')),
                fine_amount REAL DEFAULT 0.0,
                notes TEXT,
                FOREIGN KEY (book_id) REFERENCES books (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_roll_number ON users(roll_number)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_seats_number ON seats(seat_number)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_seats_status ON seats(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bookings_seat ON bookings(seat_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_admins_username ON admins(username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_approved_students_roll ON approved_students(roll_number)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_blocked_users_user ON blocked_users(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_usage_user ON daily_usage(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_usage_date ON daily_usage(usage_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bookings_scanned_at ON bookings(scanned_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bookings_created_at ON bookings(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_books_category ON books(category_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_books_title ON books(title)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_books_author ON books(author)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_book_issues_book ON book_issues(book_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_book_issues_user ON book_issues(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_book_issues_status ON book_issues(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_book_issues_due_date ON book_issues(due_date)')
        
        conn.commit()
        
        # Initialize seats (10x10 grid = 100 seats)
        self.init_seats(cursor, conn)
        
        # Initialize super admin
        self.init_super_admin(cursor, conn)
        
        conn.close()
        print(f"✅ Database initialized successfully at: {os.path.abspath(self.db_path)}")

    # -----------------------------
    # Walk-in Code Generator
    # -----------------------------
    def generate_walk_in_code(self):
        """Generate unique 5-character alphanumeric walk-in code (e.g., A3B9K)"""
        import random
        import string
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        max_attempts = 100
        for _ in range(max_attempts):
            # Generate 5-character code: uppercase letters + numbers
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            
            # Check if code already exists
            cursor.execute('SELECT id FROM bookings WHERE walk_in_code = ?', (code,))
            if not cursor.fetchone():
                conn.close()
                return code
        
        conn.close()
        raise ValueError("Failed to generate unique walk-in code after 100 attempts")

    # -----------------------------
    # Session Management (Persistent)
    # -----------------------------
    def create_session(self, user_id, ttl_minutes=43200):
        """Create a persistent session token for the user.
        Default TTL: 30 days (43200 minutes)
        Returns generated token and expiry timestamp.
        """
        import secrets
        from datetime import datetime, timedelta

        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(minutes=ttl_minutes)

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO sessions (user_id, session_token, expires_at, is_active)
               VALUES (?, ?, ?, TRUE)''',
            (user_id, token, expires_at)
        )
        conn.commit()
        conn.close()

        return {
            'token': token,
            'expires_at': expires_at
        }

    def validate_session(self, token):
        """Validate session token. Returns user_id if valid, else None.
        Also deactivates expired sessions lazily.
        """
        from datetime import datetime

        if not token:
            return None

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, user_id, expires_at, is_active
            FROM sessions
            WHERE session_token = ?
        ''', (token,))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        session_id, user_id, expires_at, is_active = row

        # Coerce expires_at to datetime if stored as string
        if isinstance(expires_at, str):
            try:
                expires_at = datetime.fromisoformat(expires_at)
            except Exception:
                # If parse fails, consider expired and deactivate
                cursor.execute('UPDATE sessions SET is_active = FALSE WHERE id = ?', (session_id,))
                conn.commit()
                conn.close()
                return None

        if not is_active or datetime.now() > expires_at:
            # Deactivate expired session
            cursor.execute('UPDATE sessions SET is_active = FALSE WHERE id = ?', (session_id,))
            conn.commit()
            conn.close()
            return None

        conn.close()
        return user_id

    def invalidate_session(self, token):
        """Invalidate a specific session token"""
        if not token:
            return
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE sessions SET is_active = FALSE WHERE session_token = ?', (token,))
        conn.commit()
        conn.close()

    def invalidate_user_sessions(self, user_id):
        """Invalidate all sessions for a user (e.g., on password change)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE sessions SET is_active = FALSE WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
    
    def init_seats(self, cursor, conn):
        """Initialize the seat grid (10x10 = 100 seats)"""
        cursor.execute('SELECT COUNT(*) FROM seats')
        seat_count = cursor.fetchone()[0]
        
        if seat_count == 0:
            print("🪑 Initializing seat grid...")
            seats_data = []
            for row in range(1, 11):  # Rows 1-10
                for col in range(1, 11):  # Columns 1-10
                    seat_number = f"{row}-{col}"
                    seats_data.append((seat_number, row, col))
            
            cursor.executemany(
                'INSERT INTO seats (seat_number, row_number, column_number) VALUES (?, ?, ?)',
                seats_data
            )
            conn.commit()
            print(f"✅ Created {len(seats_data)} seats (10x10 grid)")
    
    def init_super_admin(self, cursor, conn):
        """Initialize super admin account"""
        cursor.execute('SELECT COUNT(*) FROM admins WHERE is_super_admin = TRUE')
        admin_count = cursor.fetchone()[0]
        
        if admin_count == 0:
            print("👤 Creating super admin account...")
            password_hash = self.hash_password('nani#322989')
            cursor.execute('''
                INSERT INTO admins (username, password_hash, is_super_admin)
                VALUES (?, ?, TRUE)
            ''', ('admin123', password_hash))
            conn.commit()
            print(f"✅ Super admin created - Username: admin123")
    
    def hash_password(self, password):
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password, password_hash):
        """Verify password against hash"""
        return self.hash_password(password) == password_hash
    
    def create_user(self, full_name, username, email, roll_number, password):
        """Create a new user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            password_hash = self.hash_password(password)
            cursor.execute('''
                INSERT INTO users (full_name, username, email, roll_number, password_hash)
                VALUES (?, ?, ?, ?, ?)
            ''', (full_name, username, email, roll_number, password_hash))
            
            user_id = cursor.lastrowid
            conn.commit()
            
            # Get the created user
            cursor.execute('''
                SELECT id, full_name, username, email, roll_number, registered_at
                FROM users WHERE id = ?
            ''', (user_id,))
            
            user_data = cursor.fetchone()
            conn.close()
            
            return {
                'id': user_data[0],
                'full_name': user_data[1],
                'username': user_data[2],
                'email': user_data[3],
                'roll_number': user_data[4],
                'registered_at': user_data[5]
            }
            
        except sqlite3.IntegrityError as e:
            conn.close()
            if 'username' in str(e):
                raise ValueError("Username already exists")
            elif 'email' in str(e):
                raise ValueError("Email already registered")
            elif 'roll_number' in str(e):
                raise ValueError("Roll number already registered")
            else:
                raise ValueError("User creation failed")
    
    def register_user(self, full_name, username, email, roll_number, password):
        """Register a new user (alias for create_user)"""
        return self.create_user(full_name, username, email, roll_number, password)
    
    def authenticate_user(self, login_id, password):
        """Authenticate user by username/email and password"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if login_id is email or username
        cursor.execute('''
            SELECT id, full_name, username, email, roll_number, password_hash, login_count
            FROM users 
            WHERE (username = ? OR email = ?) AND is_active = TRUE
        ''', (login_id, login_id))
        
        user_data = cursor.fetchone()
        
        if not user_data:
            conn.close()
            raise ValueError("Invalid credentials")
        
        user_id, full_name, username, email, roll_number, password_hash, login_count = user_data
        
        if not self.verify_password(password, password_hash):
            conn.close()
            raise ValueError("Invalid credentials")
        
        # Update login count and last login
        cursor.execute('''
            UPDATE users 
            SET login_count = login_count + 1, last_login = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (user_id,))
        
        conn.commit()
        conn.close()
        
        return {
            'id': user_id,
            'full_name': full_name,
            'username': username,
            'email': email,
            'roll_number': roll_number,
            'login_count': login_count + 1
        }
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, full_name, username, email, roll_number, registered_at, login_count, last_login
            FROM users 
            WHERE id = ? AND is_active = TRUE
        ''', (user_id,))
        
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            return {
                'id': user_data[0],
                'full_name': user_data[1],
                'username': user_data[2],
                'email': user_data[3],
                'roll_number': user_data[4],
                'registered_at': user_data[5],
                'login_count': user_data[6],
                'last_login': user_data[7]
            }
        return None
    
    def get_user_by_roll_number(self, roll_number):
        """Get user by roll number - checks both online registration and approved CSV list"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if user registered online
        cursor.execute('''
            SELECT id, full_name, username, email, roll_number, registered_at, is_active
            FROM users 
            WHERE roll_number = ?
        ''', (roll_number,))
        
        user_data = cursor.fetchone()
        
        # Check if roll number is in approved CSV list
        cursor.execute('''
            SELECT id, roll_number, full_name, status
            FROM approved_students 
            WHERE roll_number = ?
        ''', (roll_number,))
        
        approved_data = cursor.fetchone()
        
        conn.close()
        
        # Verification Logic:
        # 1. If in CSV + registered online → Allow (show username)
        # 2. If in CSV + NOT registered online → Allow (show roll number)
        # 3. If NOT in CSV + registered online → REJECT (fake account)
        # 4. If NOT in CSV + NOT registered online → REJECT
        
        if approved_data:
            # Roll number is in approved CSV list
            approved_status = approved_data[3]
            
            if approved_status == 'blocked':
                raise ValueError("Student is blocked")
            
            if approved_status == 'waiting':
                raise ValueError("Student is on waiting list")
            
            if user_data:
                # Registered online + in CSV → Allow
                if not user_data[6]:  # is_active check
                    raise ValueError("User account is blocked")
                
                return {
                    'id': user_data[0],
                    'full_name': user_data[1],
                    'username': user_data[2],
                    'email': user_data[3],
                    'roll_number': user_data[4],
                    'registered_at': user_data[5],
                    'source': 'online',
                    'display_name': user_data[2]  # Show username
                }
            else:
                # NOT registered online but in CSV → Allow
                return {
                    'id': None,  # No user ID
                    'full_name': approved_data[2],
                    'username': None,
                    'email': None,
                    'roll_number': approved_data[1],
                    'registered_at': None,
                    'source': 'csv',
                    'display_name': approved_data[1]  # Show roll number
                }
        else:
            # Roll number NOT in approved CSV list
            if user_data:
                # Registered online but NOT in CSV → REJECT (fake account)
                raise ValueError("Roll number not in approved student list. Please contact admin.")
            else:
                # NOT in CSV + NOT registered → REJECT
                raise ValueError("Roll number not found. Please register or contact admin.")
        
        return None
    
    def find_user_by_email_or_username(self, identifier):
        """Find user by email or username"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, full_name, username, email, registered_at
            FROM users 
            WHERE (username = ? OR email = ?) AND is_active = TRUE
        ''', (identifier, identifier))
        
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            return {
                'id': user_data[0],
                'full_name': user_data[1],
                'username': user_data[2],
                'email': user_data[3],
                'registered_at': user_data[4]
            }
        return None
    
    def get_available_seats(self):
        """Get all available seats"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, seat_number, row_number, column_number, status
            FROM seats 
            WHERE status = 'available'
            ORDER BY row_number, column_number
        ''')
        
        seats = []
        for row in cursor.fetchall():
            seats.append({
                'id': row[0],
                'seat_number': row[1],
                'row': row[2],
                'column': row[3],
                'status': row[4]
            })
        
        conn.close()
        return seats
    
    def get_all_seats(self):
        """Get all seats with their current real-time booking status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        from datetime import datetime
        now = datetime.now()
        
        cursor.execute('''
            SELECT s.id, s.seat_number, s.row_number, s.column_number, s.status
            FROM seats s
            ORDER BY s.row_number, s.column_number
        ''')
        
        seats = []
        for row in cursor.fetchall():
            seat_id = row[0]
            seat_number = row[1]
            base_status = row[4]  # 'available' or 'maintenance'
            
            # Check if seat has any active bookings
            # Seat should be RED (booked) if:
            # 1. Booking is pending-scan and hasn't ended yet (someone booked it, waiting to scan)
            # 2. Booking is scanned/active and currently in progress
            cursor.execute('''
                SELECT COUNT(*) FROM bookings
                WHERE seat_id = ?
                AND (
                    (status = 'pending-scan' AND end_time > datetime('now', 'localtime'))
                    OR (status IN ('scanned', 'active') AND start_time <= datetime('now', 'localtime') AND end_time > datetime('now', 'localtime'))
                )
            ''', (seat_id,))
            
            active_count = cursor.fetchone()[0]
            
            # Determine display status
            if base_status == 'maintenance':
                display_status = 'maintenance'
            elif active_count > 0:
                display_status = 'booked'  # Someone is using it right now
            else:
                display_status = 'available'
            
            seats.append({
                'id': seat_id,
                'seat_number': seat_number,
                'row': row[2],
                'column': row[3],
                'status': display_status,
                'booking_id': None,
                'last_updated': now.isoformat()
            })
        
        conn.close()
        return seats
    
    def create_booking(self, user_id, seat_number, duration_minutes, start_time=None, roll_number=None):
        """Create a booking (alias for book_seat using seat_number)
        
        Args:
            user_id: User ID making the booking
            seat_number: Seat number (e.g., '5-6')
            duration_minutes: Duration in minutes
            start_time: Optional datetime for future booking (default: now)
            roll_number: Optional roll number for CSV-only students
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get seat ID from seat number
            cursor.execute('SELECT id, status FROM seats WHERE seat_number = ?', (seat_number,))
            seat_data = cursor.fetchone()
            
            if not seat_data:
                raise ValueError("Seat not found")
            
            seat_id = seat_data[0]
            
            # Use provided start_time or default to now
            booking_start_time = start_time if start_time else datetime.now()
            end_time = booking_start_time + timedelta(minutes=duration_minutes)
            
            # Check for time slot overlap instead of seat status
            if not self.check_seat_availability(seat_number, booking_start_time, end_time):
                raise ValueError("Seat not available in this time slot")
            
            # Use user_id if available, otherwise use roll_number for CSV-only students
            identifier = user_id if user_id else roll_number
            qr_code = f"LIBRARY_SEAT_{seat_id}_{identifier}_{int(booking_start_time.timestamp())}"
            
            # For CSV-only students without user_id, we need to handle it differently
            if user_id is None:
                user_id = 0
            
            cursor.execute('''
                INSERT INTO bookings (user_id, seat_id, start_time, end_time, 
                                    duration_minutes, qr_code)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, seat_id, booking_start_time, end_time, duration_minutes, qr_code))
            
            booking_id = cursor.lastrowid
            conn.commit()
            
            # Get booking details
            cursor.execute('''
                SELECT b.id, s.seat_number, b.user_id, b.start_time, b.end_time, 
                       b.duration_minutes, b.status, b.qr_code, b.created_at
                FROM bookings b
                JOIN seats s ON b.seat_id = s.id
                WHERE b.id = ?
            ''', (booking_id,))
            
            booking_data = cursor.fetchone()
            
            return {
                'id': booking_data[0],
                'seat_number': booking_data[1],
                'user_id': booking_data[2] if booking_data[2] != 0 else None,
                'start_time': booking_data[3],
                'end_time': booking_data[4],
                'duration': booking_data[5],
                'status': booking_data[6],
                'qr_code': booking_data[7],
                'created_at': booking_data[8],
                'roll_number': roll_number
            }
            
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            raise e
        finally:
            if conn:
                conn.close()
    
    def book_seat(self, user_id, seat_id, duration_minutes):
        """Book a seat for specified duration"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if seat is available
            cursor.execute('SELECT status FROM seats WHERE id = ?', (seat_id,))
            seat_data = cursor.fetchone()
            
            if not seat_data or seat_data[0] != 'available':
                raise ValueError("Seat not available")
            
            # Create booking
            start_time = datetime.now()
            end_time = start_time + timedelta(minutes=duration_minutes)
            qr_code = f"LIBRARY_SEAT_{seat_id}_{user_id}_{int(start_time.timestamp())}"
            
            cursor.execute('''
                INSERT INTO bookings (user_id, seat_id, start_time, end_time, 
                                    duration_minutes, qr_code)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, seat_id, start_time, end_time, duration_minutes, qr_code))
            
            booking_id = cursor.lastrowid
            
            # Don't lock seat - allow multiple time-slot bookings
            
            conn.commit()
            
            # Get booking details
            cursor.execute('''
                SELECT b.id, s.seat_number, b.start_time, b.end_time, 
                       b.duration_minutes, b.qr_code
                FROM bookings b
                JOIN seats s ON b.seat_id = s.id
                WHERE b.id = ?
            ''', (booking_id,))
            
            booking_data = cursor.fetchone()
            conn.close()
            
            return {
                'id': booking_data[0],
                'seat_number': booking_data[1],
                'start_time': booking_data[2],
                'end_time': booking_data[3],
                'duration': booking_data[4],
                'qr_code': booking_data[5]
            }
            
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e
    
    def expire_booking(self, booking_id):
        """Mark booking as expired - seat becomes available automatically via time-slot checking"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE bookings SET status = 'expired', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (booking_id,))
        
        # No need to update seat status - seat availability is determined by active bookings
        # When booking is expired, check_seat_availability() will automatically show seat as free
        
        conn.commit()
        conn.close()
    
    def get_user_bookings(self, user_id):
        """Get all bookings for a user including walk-in bookings linked to their account"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT b.id, s.seat_number, b.start_time, b.end_time,
                       b.duration_minutes, b.status, b.qr_code, b.is_walk_in, b.walk_in_code
                FROM bookings b
                JOIN seats s ON b.seat_id = s.id
                WHERE b.user_id = ?
                ORDER BY b.created_at DESC
            ''', (user_id,))
            
            bookings = []
            for row in cursor.fetchall():
                bookings.append({
                    'id': row[0],
                    'seat_number': row[1],
                    'start_time': row[2],
                    'end_time': row[3],
                    'duration': row[4],
                    'status': row[5],
                    'qr_code': row[6],
                    'is_walk_in': bool(row[7]),
                    'walk_in_code': row[8] if row[8] else None
                })
            
            return bookings
        finally:
            if conn:
                conn.close()
    
    def cancel_booking(self, booking_id, user_id):
        """Cancel a booking"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Verify booking belongs to user and is cancellable
            cursor.execute('''
                SELECT seat_id, status FROM bookings 
                WHERE id = ? AND user_id = ? AND status IN ('pending-scan', 'scanned', 'active')
            ''', (booking_id, user_id))
            
            booking_data = cursor.fetchone()
            
            if not booking_data:
                raise ValueError("Booking not found or already cancelled")
            
            seat_id = booking_data[0]
            current_status = booking_data[1]
            
            # Update booking status to cancelled
            cursor.execute('''
                UPDATE bookings SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (booking_id,))
            
            # No need to update seat status - seat availability is determined by active bookings
            # When booking is cancelled, check_seat_availability() will automatically show seat as free
            
            conn.commit()
            conn.close()
            
            return {'success': True, 'message': 'Booking cancelled successfully'}
            
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e
    
    def verify_qr_code(self, qr_code):
        """Verify QR code and get booking details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT b.id, b.user_id, b.seat_id, s.seat_number, b.status, 
                   u.full_name, u.roll_number, b.start_time, b.end_time, b.duration_minutes
            FROM bookings b
            JOIN seats s ON b.seat_id = s.id
            JOIN users u ON b.user_id = u.id
            WHERE b.qr_code = ?
        ''', (qr_code,))
        
        booking_data = cursor.fetchone()
        conn.close()
        
        if not booking_data:
            return None
        
        return {
            'id': booking_data[0],
            'user_id': booking_data[1],
            'seat_id': booking_data[2],
            'seat_number': booking_data[3],
            'status': booking_data[4],
            'full_name': booking_data[5],
            'roll_number': booking_data[6],
            'start_time': booking_data[7],
            'end_time': booking_data[8],
            'duration': booking_data[9]
        }
    
    def confirm_booking(self, booking_id):
        """Confirm a booking (mark as completed when scanned at library)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if booking exists and is active
            cursor.execute('''
                SELECT id, status FROM bookings 
                WHERE id = ?
            ''', (booking_id,))
            
            booking_data = cursor.fetchone()
            
            if not booking_data:
                raise ValueError("Booking not found")
            
            if booking_data[1] == 'completed':
                raise ValueError("Booking already confirmed")
            
            if booking_data[1] != 'active':
                raise ValueError(f"Booking is {booking_data[1]}, cannot confirm")
            
            # Update booking status to completed
            cursor.execute('''
                UPDATE bookings SET status = 'completed', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (booking_id,))
            
            conn.commit()
            conn.close()
            
            return {'success': True, 'message': 'Booking confirmed successfully'}
            
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e
    
    def clear_all_bookings(self):
        """Clear all seat bookings and make all seats available"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Delete all bookings
            cursor.execute("DELETE FROM bookings")
            
            # Update all seats to be available
            cursor.execute("UPDATE seats SET status = 'available', reserved_by = NULL")
            
            # Delete all groups
            cursor.execute("DELETE FROM groups")
            
            # Delete all group_members
            cursor.execute("DELETE FROM group_members")
            
            conn.commit()
            print("🧹 All seats cleared and made available!")
            
        except sqlite3.Error as e:
            conn.rollback()
            raise Exception(f"Failed to clear seats: {str(e)}")
        finally:
            conn.close()
    
    # Admin Management Methods
    
    def authenticate_admin(self, username, password):
        """Authenticate admin user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, password_hash, is_super_admin, email
            FROM admins 
            WHERE username = ? AND is_active = TRUE
        ''', (username,))
        
        admin_data = cursor.fetchone()
        
        if not admin_data:
            conn.close()
            raise ValueError("Invalid credentials")
        
        admin_id, username, password_hash, is_super_admin, email = admin_data
        
        if not self.verify_password(password, password_hash):
            conn.close()
            raise ValueError("Invalid credentials")
        
        # Update last login
        cursor.execute('''
            UPDATE admins SET last_login = CURRENT_TIMESTAMP WHERE id = ?
        ''', (admin_id,))
        
        conn.commit()
        conn.close()
        
        return {
            'id': admin_id,
            'username': username,
            'is_super_admin': bool(is_super_admin),
            'email': email
        }
    
    def create_admin(self, username, password, email=None, created_by=None):
        """Create new admin account"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            password_hash = self.hash_password(password)
            cursor.execute('''
                INSERT INTO admins (username, password_hash, email, created_by)
                VALUES (?, ?, ?, ?)
            ''', (username, password_hash, email, created_by))
            
            admin_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return {'id': admin_id, 'username': username, 'email': email}
            
        except sqlite3.IntegrityError:
            conn.close()
            raise ValueError("Admin username already exists")
    
    def change_admin_password(self, admin_id, new_password):
        """Change admin password"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        password_hash = self.hash_password(new_password)
        cursor.execute('''
            UPDATE admins SET password_hash = ? WHERE id = ?
        ''', (password_hash, admin_id))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
    
    def get_all_admins(self):
        """Get all admin accounts"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, email, is_super_admin, created_at, last_login, is_active
            FROM admins
            ORDER BY is_super_admin DESC, created_at ASC
        ''')
        
        admins = []
        for row in cursor.fetchall():
            admins.append({
                'id': row[0],
                'username': row[1],
                'email': row[2],
                'is_super_admin': bool(row[3]),
                'created_at': row[4],
                'last_login': row[5],
                'is_active': bool(row[6])
            })
        
        conn.close()
        return admins
    
    def upload_approved_students(self, students_data, uploaded_by):
        """Upload approved students from CSV"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        added = 0
        skipped = 0
        
        for student in students_data:
            try:
                cursor.execute('''
                    INSERT INTO approved_students (roll_number, full_name, uploaded_by)
                    VALUES (?, ?, ?)
                ''', (student['roll_number'], student['full_name'], uploaded_by))
                added += 1
            except sqlite3.IntegrityError:
                skipped += 1
        
        conn.commit()
        conn.close()
        
        return {'added': added, 'skipped': skipped}
    
    def get_approved_students(self):
        """Get all approved students"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, roll_number, full_name, status, uploaded_at
            FROM approved_students
            ORDER BY roll_number
        ''')
        
        students = []
        for row in cursor.fetchall():
            students.append({
                'id': row[0],
                'roll_number': row[1],
                'full_name': row[2],
                'status': row[3],
                'uploaded_at': row[4]
            })
        
        conn.close()
        return students
    
    def is_student_approved(self, roll_number):
        """Check if student is in approved list"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT status FROM approved_students WHERE roll_number = ?
        ''', (roll_number,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        return result[0]  # Returns 'approved', 'blocked', or 'waiting'
    
    def get_approved_student_by_roll(self, roll_number):
        """Get approved student details by roll number"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, roll_number, full_name, status
            FROM approved_students WHERE roll_number = ?
        ''', (roll_number,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        return {
            'id': result[0],
            'roll_number': result[1],
            'full_name': result[2],
            'status': result[3]
        }
    
    def create_walk_in_booking(self, roll_number, seat_number, duration_minutes, link_to_user=False, user_id=None):
        """Create a walk-in booking with alphanumeric code
        
        Args:
            roll_number: Student roll number
            seat_number: Seat to book
            duration_minutes: Booking duration
            link_to_user: If True, link booking to online account
            user_id: User ID if linking to account
            
        Returns:
            Booking details with walk-in code
        """
        from datetime import datetime, timedelta
        import time
        
        # Retry logic for database locks
        max_retries = 3
        for attempt in range(max_retries):
            conn = None
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                # Get seat info
                cursor.execute('SELECT id, status FROM seats WHERE seat_number = ?', (seat_number,))
                seat_data = cursor.fetchone()
                
                if not seat_data:
                    raise ValueError("Seat not found")
                
                seat_id = seat_data[0]
                
                # Set booking times
                start_time = datetime.now()
                end_time = start_time + timedelta(minutes=duration_minutes)
                
                # Check seat availability for this time slot
                if not self.check_seat_availability(seat_number, start_time, end_time):
                    raise ValueError("Seat not available in this time slot")
                
                # Generate unique walk-in code
                walk_in_code = self.generate_walk_in_code()
                
                # Create QR code (still needed for data consistency)
                qr_code = f"WALK_IN_{seat_id}_{roll_number}_{int(start_time.timestamp())}"
                
                # If linking to account, use user_id; otherwise use 0 for walk-ins
                effective_user_id = user_id if link_to_user else 0
                
                # Insert booking with 'active' status (skip pending-scan for walk-ins)
                cursor.execute('''
                    INSERT INTO bookings (
                        user_id, seat_id, start_time, end_time, duration_minutes,
                        status, qr_code, is_walk_in, walk_in_code
                    )
                    VALUES (?, ?, ?, ?, ?, 'active', ?, 1, ?)
                ''', (effective_user_id, seat_id, start_time, end_time, duration_minutes, qr_code, walk_in_code))
                
                booking_id = cursor.lastrowid
                
                # Update daily usage if linked to user account
                if link_to_user and user_id:
                    self.update_daily_usage(user_id, duration_minutes)
                
                conn.commit()
                
                return {
                    'id': booking_id,
                    'seat_number': seat_number,
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'duration': duration_minutes,
                    'status': 'active',
                    'walk_in_code': walk_in_code,
                    'roll_number': roll_number,
                    'linked_to_account': link_to_user
                }
                
            except sqlite3.OperationalError as e:
                if conn:
                    try:
                        conn.rollback()
                    except:
                        pass
                if 'locked' in str(e).lower() and attempt < max_retries - 1:
                    # Wait and retry on database lock
                    time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    raise e
            except Exception as e:
                if conn:
                    try:
                        conn.rollback()
                    except:
                        pass
                raise e
            finally:
                if conn:
                    conn.close()
    
    def cancel_walk_in_booking_by_code(self, walk_in_code):
        """Cancel a walk-in booking using the walk-in code
        
        Args:
            walk_in_code: 5-character alphanumeric code
            
        Returns:
            Success message with booking details
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Find booking by walk-in code
            cursor.execute('''
                SELECT id, seat_id, status, user_id
                FROM bookings
                WHERE walk_in_code = ? AND is_walk_in = 1
            ''', (walk_in_code,))
            
            booking_data = cursor.fetchone()
            
            if not booking_data:
                raise ValueError("Invalid walk-in code or booking not found")
            
            booking_id, seat_id, status, user_id = booking_data
            
            # Check if booking can be cancelled
            if status not in ['active', 'scanned', 'pending-scan']:
                raise ValueError(f"Booking already {status}, cannot cancel")
            
            # Cancel the booking
            cursor.execute('''
                UPDATE bookings 
                SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (booking_id,))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'booking_id': booking_id,
                'seat_id': seat_id,
                'message': 'Walk-in booking cancelled successfully'
            }
            
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e

    
    def block_user(self, user_id, reason, blocked_by):
        """Block a user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE users SET is_active = FALSE WHERE id = ?
            ''', (user_id,))
            
            cursor.execute('''
                INSERT INTO blocked_users (user_id, reason, blocked_by)
                VALUES (?, ?, ?)
            ''', (user_id, reason, blocked_by))
            
            conn.commit()
            conn.close()
            return {'success': True}
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e
    
    def unblock_user(self, user_id):
        """Unblock a user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET is_active = TRUE WHERE id = ?
        ''', (user_id,))
        
        cursor.execute('''
            DELETE FROM blocked_users WHERE user_id = ?
        ''', (user_id,))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
    
    def get_all_users_with_status(self):
        """Get all registered users with their status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.id, u.full_name, u.username, u.email, u.roll_number, 
                   u.registered_at, u.is_active, b.reason as block_reason
            FROM users u
            LEFT JOIN blocked_users b ON u.id = b.user_id
            ORDER BY u.registered_at DESC
        ''')
        
        users = []
        for row in cursor.fetchall():
            users.append({
                'id': row[0],
                'full_name': row[1],
                'username': row[2],
                'email': row[3],
                'roll_number': row[4],
                'registered_at': row[5],
                'is_active': bool(row[6]),
                'block_reason': row[7]
            })
        
        conn.close()
        return users
    
    def get_all_bookings_admin(self):
        """Get all bookings for admin view"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT b.id, u.full_name, u.roll_number, s.seat_number, 
                   b.start_time, b.end_time, b.status, b.created_at
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            JOIN seats s ON b.seat_id = s.id
            ORDER BY b.created_at DESC
        ''')
        
        bookings = []
        for row in cursor.fetchall():
            bookings.append({
                'id': row[0],
                'student_name': row[1],
                'roll_number': row[2],
                'seat_number': row[3],
                'start_time': row[4],
                'end_time': row[5],
                'status': row[6],
                'created_at': row[7]
            })
        
        conn.close()
        return bookings
    
    def remove_booking_admin(self, booking_id):
        """Admin removes a specific booking"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get seat_id before deleting
            cursor.execute('SELECT seat_id FROM bookings WHERE id = ?', (booking_id,))
            result = cursor.fetchone()
            
            if not result:
                raise ValueError("Booking not found")
            
            seat_id = result[0]
            
            # Delete booking
            cursor.execute('DELETE FROM bookings WHERE id = ?', (booking_id,))
            
            # No need to update seat status - availability determined by active bookings
            
            conn.commit()
            conn.close()
            
            return {'success': True}
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e
    
    def update_student_status(self, roll_number, status):
        """Update approved student status (approved/blocked/waiting)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE approved_students SET status = ? WHERE roll_number = ?
        ''', (status, roll_number))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
    
    # ============================================
    # New Booking Flow Methods (10-min timer, scanning, leaving early, reallocation)
    # ============================================
    
    def auto_expire_pending_scans(self):
        """Auto-cancel bookings that weren't scanned within 10 minutes of their start time"""
        from datetime import datetime, timedelta
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Find pending-scan bookings where start_time + 10 minutes has passed
            cursor.execute('''
                SELECT id, seat_id, user_id FROM bookings
                WHERE status = 'pending-scan' 
                AND datetime(start_time, '+10 minutes') < datetime('now', 'localtime')
            ''')
            
            expired = cursor.fetchall()
            for booking_id, seat_id, user_id in expired:
                cursor.execute('UPDATE bookings SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', 
                             ('expired', booking_id))
                print(f"  ⏰ Expired booking {booking_id} (seat {seat_id}, user {user_id})")
            
            conn.commit()
            result = len(expired)
        except Exception as e:
            print(f"❌ Error in auto_expire_pending_scans: {e}")
            result = 0
        finally:
            if conn:
                conn.close()
        
        return result
    
    def scan_booking(self, booking_id):
        """Mark booking as scanned (library staff scans QR)"""
        from datetime import datetime
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, status, user_id, seat_id, start_time, end_time
                FROM bookings WHERE id = ?
            ''', (booking_id,))
            
            booking = cursor.fetchone()
            if not booking:
                raise ValueError("Booking not found")
            
            booking_id_check, status, user_id, seat_id, start_time, end_time = booking
            
            if status != 'pending-scan':
                raise ValueError(f"Booking is in {status} state, cannot scan")
            
            # Update booking to scanned state
            cursor.execute('''
                UPDATE bookings SET status = 'scanned', scanned_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (booking_id_check,))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'booking_id': booking_id_check,
                'user_id': user_id,
                'seat_id': seat_id,
                'start_time': start_time,
                'end_time': end_time
            }
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e
    
    def leave_seat_early(self, booking_id, user_id):
        """User leaves seat before booking time ends"""
        from datetime import datetime
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, status, seat_id, user_id, duration_minutes
                FROM bookings WHERE id = ? AND user_id = ?
            ''', (booking_id, user_id))
            
            booking = cursor.fetchone()
            if not booking:
                raise ValueError("Booking not found")
            
            booking_id, status, seat_id, uid, duration = booking
            
            if status not in ['scanned', 'active']:
                raise ValueError(f"Cannot leave seat from {status} state")
            
            # Mark as leave-early
            cursor.execute('''
                UPDATE bookings SET status = 'leave-early', left_early_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (booking_id,))
            
            # No need to update seat status - availability determined by active bookings
            # When booking is marked leave-early, check_seat_availability() will show seat as free
            
            conn.commit()
            conn.close()
            
            return {'success': True, 'seat_freed': seat_id}
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e
    
    def check_seat_availability_for_reallocation(self, original_seat_id, user_id, start_time_str, end_time_str):
        """Check if original seat is available for reallocation after user's time ends"""
        from datetime import datetime
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            end_time = datetime.fromisoformat(end_time_str)
            
            # Check if seat is booked after the user's end time
            cursor.execute('''
                SELECT COUNT(*) FROM bookings
                WHERE seat_id = ? AND start_time >= ? AND status IN ('pending-scan', 'scanned', 'active')
            ''', (original_seat_id, end_time))
            
            count = cursor.fetchone()[0]
            conn.close()
            
            return count == 0  # True if seat is free after user's time
        except Exception as e:
            conn.close()
            raise e
    
    def reallocate_seat(self, booking_id, user_id, new_seat_id):
        """Reallocate user to a different seat for remaining time"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get booking details
            cursor.execute('''
                SELECT id, seat_id, status FROM bookings WHERE id = ? AND user_id = ?
            ''', (booking_id, user_id))
            
            booking = cursor.fetchone()
            if not booking:
                raise ValueError("Booking not found")
            
            booking_id, old_seat_id, status = booking
            
            if status not in ['scanned', 'active']:
                raise ValueError(f"Cannot reallocate from {status} state")
            
            # No need to update seat status - seats track bookings via time slots
            
            # Update booking with reallocation
            cursor.execute('''
                UPDATE bookings SET reallocated_to_seat_id = ?, seat_id = ?, status = 'reallocated'
                WHERE id = ?
            ''', (old_seat_id, new_seat_id, booking_id))
            
            conn.commit()
            conn.close()
            
            return {'success': True, 'old_seat': old_seat_id, 'new_seat': new_seat_id}
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e
    
    def check_seat_availability(self, seat_number, start_time, end_time):
        """Check if a seat is available in a given time range (no overlapping bookings)
        
        Args:
            seat_number: Seat number to check
            start_time: Start datetime of desired booking
            end_time: End datetime of desired booking
            
        Returns:
            True if seat is free in that time range, False if overlapping booking exists
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get seat_id from seat_number
        cursor.execute('SELECT id FROM seats WHERE seat_number = ?', (seat_number,))
        seat_data = cursor.fetchone()
        
        if not seat_data:
            conn.close()
            return False
        
        seat_id = seat_data[0]
        
        # Check for overlapping bookings (exclude cancelled, expired, completed)
        cursor.execute('''
            SELECT COUNT(*) FROM bookings
            WHERE seat_id = ?
            AND status IN ('pending-scan', 'scanned', 'active')
            AND (
                (start_time < ? AND end_time > ?)
                OR (start_time < ? AND end_time > ?)
                OR (start_time >= ? AND end_time <= ?)
            )
        ''', (seat_id, end_time, start_time, end_time, start_time, start_time, end_time))
        
        overlap_count = cursor.fetchone()[0]
        conn.close()
        
        return overlap_count == 0
    
    def get_seat_bookings_for_day(self, seat_number, date_str=None):
        """Get all active bookings for a seat on a specific day
        
        Args:
            seat_number: Seat number
            date_str: Date in YYYY-MM-DD format (default: today)
            
        Returns:
            List of booking time slots for that seat
        """
        from datetime import datetime
        if not date_str:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get seat_id
        cursor.execute('SELECT id FROM seats WHERE seat_number = ?', (seat_number,))
        seat_data = cursor.fetchone()
        
        if not seat_data:
            conn.close()
            return []
        
        seat_id = seat_data[0]
        
        # Get all active bookings for this seat on the specified day
        cursor.execute('''
            SELECT id, user_id, start_time, end_time, status
            FROM bookings
            WHERE seat_id = ?
            AND DATE(start_time) = ?
            AND status IN ('pending-scan', 'scanned', 'active')
            ORDER BY start_time
        ''', (seat_id, date_str))
        
        bookings = []
        for row in cursor.fetchall():
            bookings.append({
                'id': row[0],
                'user_id': row[1],
                'start_time': row[2],
                'end_time': row[3],
                'status': row[4]
            })
        
        conn.close()
        return bookings
    
    def get_daily_usage(self, user_id, date_str=None):
        """Get user's daily usage for today or specified date (max 4 hours = 240 min)"""
        from datetime import datetime
        if not date_str:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT total_minutes_used, section_count FROM daily_usage
            WHERE user_id = ? AND usage_date = ?
        ''', (user_id, date_str))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'minutes_used': result[0],
                'minutes_remaining': max(0, 240 - result[0]),
                'section_count': result[1],
                'sections_remaining': max(0, 4 - result[1]),
                'can_book': (result[0] < 240 and result[1] < 4)
            }
        else:
            return {
                'minutes_used': 0,
                'minutes_remaining': 240,
                'section_count': 0,
                'sections_remaining': 4,
                'can_book': True
            }
    
    def update_daily_usage(self, user_id, duration_minutes):
        """Update user's daily usage after booking scanned"""
        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%d')
        
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if user has usage record for today
            cursor.execute('''
                SELECT id, total_minutes_used, section_count FROM daily_usage
                WHERE user_id = ? AND usage_date = ?
            ''', (user_id, today))
            
            usage = cursor.fetchone()
            
            if usage:
                usage_id, used, section_count = usage
                # Determine if this is a new section (>= 60 min gap from last booking)
                new_section_count = section_count + 1 if (used + duration_minutes) >= 60 else section_count
                
                cursor.execute('''
                    UPDATE daily_usage
                    SET total_minutes_used = ?, section_count = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (used + duration_minutes, new_section_count, usage_id))
            else:
                cursor.execute('''
                    INSERT INTO daily_usage (user_id, usage_date, total_minutes_used, section_count)
                    VALUES (?, ?, ?, 1)
                ''', (user_id, today, duration_minutes))
            
            conn.commit()
            return True
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            raise e
        finally:
            if conn:
                conn.close()
    
    def reset_daily_usage(self, user_id):
        """Reset daily usage counters for a user (admin function)"""
        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%d')
        
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Delete today's usage record
            cursor.execute('''
                DELETE FROM daily_usage
                WHERE user_id = ? AND usage_date = ?
            ''', (user_id, today))
            
            conn.commit()
            return True
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            raise e
        finally:
            if conn:
                conn.close()
    
    # ============================
    # BOOK CATEGORY OPERATIONS
    # ============================
    
    def add_category(self, name, description=None):
        """Add a new book category"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO book_categories (name, description)
                VALUES (?, ?)
            ''', (name, description))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            raise e
        finally:
            if conn:
                conn.close()
    
    def get_all_categories(self):
        """Get all book categories"""
        conn = None
        try:
            conn = self.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM book_categories ORDER BY name')
            return cursor.fetchall()
        except Exception as e:
            raise e
        finally:
            if conn:
                conn.close()
    
    def delete_category(self, category_id):
        """Delete a book category"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM book_categories WHERE id = ?', (category_id,))
            conn.commit()
            return True
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            raise e
        finally:
            if conn:
                conn.close()
    
    # ============================
    # BOOK OPERATIONS
    # ============================
    
    def add_book(self, title, author, isbn=None, category_id=None, shelf_number=None, 
                 rack_number=None, total_copies=1, cover_image_url=None, 
                 online_resource_link=None, description=None, publisher=None, publication_year=None):
        """Add a new book to the library"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO books (title, author, isbn, category_id, shelf_number, rack_number,
                                  total_copies, available_copies, cover_image_url, online_resource_link,
                                  description, publisher, publication_year)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (title, author, isbn, category_id, shelf_number, rack_number, 
                  total_copies, total_copies, cover_image_url, online_resource_link,
                  description, publisher, publication_year))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            raise e
        finally:
            if conn:
                conn.close()
    
    def update_book(self, book_id, **kwargs):
        """Update book details"""
        from datetime import datetime
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Build dynamic update query
            allowed_fields = ['title', 'author', 'isbn', 'category_id', 'shelf_number', 
                            'rack_number', 'total_copies', 'available_copies', 'cover_image_url', 
                            'online_resource_link', 'description', 'publisher', 'publication_year']
            
            update_fields = []
            values = []
            for key, value in kwargs.items():
                if key in allowed_fields:
                    update_fields.append(f"{key} = ?")
                    values.append(value)
            
            if not update_fields:
                return False
            
            # Add updated_at timestamp
            update_fields.append("updated_at = ?")
            values.append(datetime.now())
            values.append(book_id)
            
            query = f"UPDATE books SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
            return True
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            raise e
        finally:
            if conn:
                conn.close()
    
    def delete_book(self, book_id):
        """Delete a book from the library"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
            conn.commit()
            return True
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            raise e
        finally:
            if conn:
                conn.close()
    
    def get_all_books(self, category_id=None, search_query=None):
        """Get all books with optional filtering"""
        conn = None
        try:
            conn = self.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = '''
                SELECT b.*, c.name as category_name
                FROM books b
                LEFT JOIN book_categories c ON b.category_id = c.id
                WHERE 1=1
            '''
            params = []
            
            if category_id:
                query += ' AND b.category_id = ?'
                params.append(category_id)
            
            if search_query:
                query += ' AND (b.title LIKE ? OR b.author LIKE ? OR b.isbn LIKE ?)'
                search_term = f'%{search_query}%'
                params.extend([search_term, search_term, search_term])
            
            query += ' ORDER BY b.title'
            
            cursor.execute(query, params)
            return cursor.fetchall()
        except Exception as e:
            raise e
        finally:
            if conn:
                conn.close()
    
    def get_book_by_id(self, book_id):
        """Get a single book by ID"""
        conn = None
        try:
            conn = self.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT b.*, c.name as category_name
                FROM books b
                LEFT JOIN book_categories c ON b.category_id = c.id
                WHERE b.id = ?
            ''', (book_id,))
            return cursor.fetchone()
        except Exception as e:
            raise e
        finally:
            if conn:
                conn.close()
    
    # ============================
    # BOOK ISSUE/BORROWING OPERATIONS
    # ============================
    
    def issue_book(self, book_id, user_id, due_days=14):
        """Issue a book to a user"""
        from datetime import datetime, timedelta
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if book is available
            cursor.execute('SELECT available_copies FROM books WHERE id = ?', (book_id,))
            result = cursor.fetchone()
            if not result or result[0] <= 0:
                return {'success': False, 'error': 'No copies available'}
            
            # Create issue record
            due_date = datetime.now() + timedelta(days=due_days)
            cursor.execute('''
                INSERT INTO book_issues (book_id, user_id, due_date)
                VALUES (?, ?, ?)
            ''', (book_id, user_id, due_date))
            
            # Update available copies
            cursor.execute('''
                UPDATE books SET available_copies = available_copies - 1
                WHERE id = ?
            ''', (book_id,))
            
            conn.commit()
            return {'success': True, 'issue_id': cursor.lastrowid}
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            raise e
        finally:
            if conn:
                conn.close()
    
    def return_book(self, issue_id, fine_amount=0.0):
        """Return a borrowed book"""
        from datetime import datetime
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get issue details
            cursor.execute('SELECT book_id, status FROM book_issues WHERE id = ?', (issue_id,))
            result = cursor.fetchone()
            if not result:
                return {'success': False, 'error': 'Issue not found'}
            
            book_id, status = result
            if status == 'returned':
                return {'success': False, 'error': 'Book already returned'}
            
            # Update issue record
            cursor.execute('''
                UPDATE book_issues
                SET returned_at = ?, status = 'returned', fine_amount = ?
                WHERE id = ?
            ''', (datetime.now(), fine_amount, issue_id))
            
            # Update available copies
            cursor.execute('''
                UPDATE books SET available_copies = available_copies + 1
                WHERE id = ?
            ''', (book_id,))
            
            conn.commit()
            return {'success': True}
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            raise e
        finally:
            if conn:
                conn.close()
    
    def get_user_issued_books(self, user_id):
        """Get all books currently issued to a user"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT bi.*, b.title, b.author, b.cover_image_url
                FROM book_issues bi
                JOIN books b ON bi.book_id = b.id
                WHERE bi.user_id = ? AND bi.status = 'issued'
                ORDER BY bi.issued_at DESC
            ''', (user_id,))
            return cursor.fetchall()
        except Exception as e:
            raise e
        finally:
            if conn:
                conn.close()
    
    def get_all_issued_books(self, status=None):
        """Get all book issues (for admin)"""
        conn = None
        try:
            conn = self.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = '''
                SELECT bi.*, b.title, b.author, u.username, u.email
                FROM book_issues bi
                JOIN books b ON bi.book_id = b.id
                JOIN users u ON bi.user_id = u.id
                WHERE 1=1
            '''
            params = []
            
            if status:
                query += ' AND bi.status = ?'
                params.append(status)
            
            query += ' ORDER BY bi.issued_at DESC'
            
            cursor.execute(query, params)
            return cursor.fetchall()
        except Exception as e:
            raise e
        finally:
            if conn:
                conn.close()
    
    def mark_book_overdue(self, issue_id):
        """Mark a book issue as overdue"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE book_issues SET status = 'overdue'
                WHERE id = ? AND status = 'issued'
            ''', (issue_id,))
            conn.commit()
            return True
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            raise e
        finally:
            if conn:
                conn.close()

if __name__ == "__main__":
    # Initialize database
    print("🚀 Initializing Library Management System Database...")
    db = DatabaseManager()
    print("✅ Database setup complete!")
    
    # Show database location
    print(f"📁 Database file: {os.path.abspath('library_database.db')}")
    print("🔧 Backend server can now connect to this database.")