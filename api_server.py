#!/usr/bin/env python3
"""
Library Management System - Flask API Server (Rewritten)
Simple token-based authentication with localStorage
"""

from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_cors import CORS
from database_setup import DatabaseManager
import secrets
import os
from datetime import datetime, timedelta
import sqlite3
import threading
import time

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-library-management-2024')

# Enable CORS for all routes
CORS(app, 
     resources={r"/*": {"origins": "*"}},
     supports_credentials=True,
     allow_headers=['Content-Type', 'Authorization'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])

# Initialize database
db = DatabaseManager()

# Background task to auto-expire bookings
def background_expiry_task():
    """Background thread to expire pending-scan bookings after 10 minutes"""
    while True:
        try:
            expired_count = db.auto_expire_pending_scans()
            if expired_count > 0:
                print(f"⏰ Auto-expired {expired_count} pending-scan bookings")
        except Exception as e:
            print(f"❌ Error in expiry task: {e}")
        
        # Run every 2 minutes
        time.sleep(120)

# Start background task
expiry_thread = threading.Thread(target=background_expiry_task, daemon=True)
expiry_thread.start()

# NOTE: Deprecated in-memory token store removed. Using persistent DB-backed sessions.

# Helper functions
def success_response(data=None, message="Success"):
    """Create success response"""
    response = {"success": True, "message": message}
    if data is not None:
        response["data"] = data
    return jsonify(response)

def error_response(message="Error", status_code=400):
    """Create error response"""
    return jsonify({"success": False, "error": message}), status_code

def extract_bearer_token():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    return auth_header.replace('Bearer ', '')

def verify_token():
    """Verify authentication token against persistent sessions"""
    token = extract_bearer_token()
    if not token:
        return None
    return db.validate_session(token)

def verify_admin_token():
    """Validate that the provided bearer token belongs to an admin session.
    Returns the admin_id if valid, else None.
    Note: Admin sessions reuse the shared sessions table; token maps to an id
    which must exist in the admins table.
    """
    token = extract_bearer_token()
    if not token:
        return None
    uid = db.validate_session(token)
    if not uid:
        return None
    # Check if uid exists in admins table
    try:
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM admins WHERE id = ? AND is_active = TRUE", (uid,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None

def require_auth():
    """Authentication middleware"""
    user_id = verify_token()
    if not user_id:
        return error_response("Authentication required", 401)
    return None

# Routes

@app.route('/')
def index():
    """Redirect to login page"""
    return redirect('/offline_form.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory('.', path)

# Authentication Routes

@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['fullName', 'username', 'email', 'rollNumber', 'password']
        for field in required_fields:
            if not data.get(field):
                return error_response(f"{field} is required")
        
        # Register user
        user = db.register_user(
            full_name=data['fullName'],
            username=data['username'],
            email=data['email'],
            roll_number=data['rollNumber'],
            password=data['password']
        )
        # Create persistent session
        session = db.create_session(user['id'])
        user['token'] = session['token']
        user['token_expires_at'] = session['expires_at'].isoformat()

        print(f"✅ User registered: {user['username']} (Roll: {user['roll_number']}, ID: {user['id']})")
        
        return success_response(user, "Registration successful")
        
    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return error_response("Registration failed", 500)

@app.route('/api/login', methods=['POST'])
def login():
    """Authenticate user login"""
    try:
        data = request.get_json()
        
        login_id = data.get('loginId')
        password = data.get('password')
        
        if not login_id or not password:
            return error_response("Login ID and password required")
        
        # Authenticate user
        user = db.authenticate_user(login_id, password)
        # Create persistent session
        session = db.create_session(user['id'])
        user['token'] = session['token']
        user['token_expires_at'] = session['expires_at'].isoformat()

        print(f"✅ User logged in: {user['username']} (ID: {user['id']}) - Token: {user['token'][:8]}...")
        
        return success_response(user, "Login successful")
        
    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        print(f"❌ Login error: {e}")
        return error_response("Login failed", 500)

@app.route('/api/logout', methods=['POST'])
def logout():
    """Logout user"""
    try:
        token = extract_bearer_token()
        user_id = verify_token()
        if token:
            db.invalidate_session(token)
            if user_id:
                print(f"✅ User logged out: {user_id}")
        
        return success_response(message="Logout successful")
    except Exception as e:
        print(f"❌ Logout error: {e}")
        return success_response(message="Logout successful")

@app.route('/api/user/profile', methods=['GET'])
def get_profile():
    """Get user profile"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        user_id = verify_token()
        user = db.get_user_by_id(user_id)
        
        return success_response(user)
        
    except Exception as e:
        print(f"❌ Profile error: {e}")
        return error_response("Failed to get profile", 500)

# Utility route used by group booking UI to resolve emails/usernames
@app.route('/api/user/find', methods=['POST'])
def find_user():
    """Find a user by email or username (requires authentication)."""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    try:
        data = request.get_json() or {}
        identifier = data.get('identifier')
        if not identifier:
            return error_response("identifier is required")
        user = db.find_user_by_email_or_username(identifier)
        if not user:
            return error_response("User not found", 404)
        return success_response(user)
    except Exception as e:
        print(f"❌ Find user error: {e}")
        return error_response("Failed to find user", 500)

# Seat Routes

@app.route('/api/seats', methods=['GET'])
def get_all_seats():
    """Get all seats"""
    try:
        seats = db.get_all_seats()
        return success_response(seats)
        
    except Exception as e:
        print(f"❌ Get seats error: {e}")
        return error_response("Failed to get seats", 500)

@app.route('/api/seats/available', methods=['GET'])
def get_available_seats():
    """Get available seats with optional time range filter"""
    try:
        # Get optional time filter parameters
        start_time_str = request.args.get('start_time')
        end_time_str = request.args.get('end_time')
        
        # If time range provided, filter by availability in that slot
        if start_time_str and end_time_str:
            try:
                from datetime import datetime
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                
                # Get all seats and check availability for each
                all_seats = db.get_all_seats()
                available_in_slot = []
                
                for seat in all_seats:
                    if db.check_seat_availability(seat['seat_number'], start_time, end_time):
                        available_in_slot.append(seat)
                
                return success_response(available_in_slot)
            except Exception as e:
                return error_response(f"Invalid time range: {str(e)}", 400)
        else:
            # No time filter - return all seats (frontend will show booking status)
            seats = db.get_all_seats()
            return success_response(seats)
        
    except Exception as e:
        print(f"❌ Get available seats error: {e}")
        return error_response("Failed to get available seats", 500)

# Booking Routes

@app.route('/api/bookings', methods=['POST'])
def create_booking():
    """Create a new booking"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        user_id = verify_token()
        data = request.get_json()
        
        seat_number = data.get('seatNumber')
        duration = data.get('duration', 60)
        start_time_str = data.get('startTime')  # ISO format string
        
        if not seat_number:
            return error_response("Seat number is required")
        
        # Parse start time if provided (for future bookings)
        start_time = None
        if start_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            except:
                return error_response("Invalid start time format")
        
        # Create booking with optional future start time
        booking = db.create_booking(user_id, seat_number, duration, start_time)
        
        print(f"✅ Booking created: Seat {seat_number} for user {user_id} starting at {booking['start_time']}")
        
        return success_response(booking, "Booking created successfully")
        
    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        print(f"❌ Booking error: {e}")
        return error_response("Failed to create booking", 500)

@app.route('/api/bookings/user', methods=['GET'])
def get_user_bookings():
    """Get user's bookings"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        user_id = verify_token()
        bookings = db.get_user_bookings(user_id)
        
        return success_response(bookings)
        
    except Exception as e:
        print(f"❌ Get bookings error: {e}")
        return error_response("Failed to get bookings", 500)

@app.route('/api/seats/<seat_number>/bookings', methods=['GET'])
def get_seat_bookings(seat_number):
    """Get all bookings for a specific seat on a given day"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        date_str = request.args.get('date')  # YYYY-MM-DD format
        bookings = db.get_seat_bookings_for_day(seat_number, date_str)
        
        return success_response(bookings)
        
    except Exception as e:
        print(f"❌ Get seat bookings error: {e}")
        return error_response("Failed to get seat bookings", 500)

@app.route('/api/bookings/<int:booking_id>/cancel', methods=['POST'])
def cancel_booking(booking_id):
    """Cancel a booking"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        user_id = verify_token()
        
        # Cancel booking
        result = db.cancel_booking(booking_id, user_id)
        
        print(f"✅ Booking cancelled: {booking_id} by user {user_id}")
        
        return success_response(result, "Booking cancelled successfully")
        
    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        print(f"❌ Cancel booking error: {e}")
        return error_response("Failed to cancel booking", 500)

# New Booking State Endpoints

@app.route('/api/bookings/<int:booking_id>/scan', methods=['POST'])
def scan_booking(booking_id):
    """Scan QR code at library kiosk to confirm booking (transitions from pending-scan to scanned)"""
    try:
        result = db.scan_booking(booking_id)
        
        # Update daily usage
        user_id = result['user_id']
        start_time = datetime.fromisoformat(result['start_time'])
        end_time = datetime.fromisoformat(result['end_time'])
        duration_min = int((end_time - start_time).total_seconds() / 60)
        
        db.update_daily_usage(user_id, duration_min)
        
        print(f"✅ Booking scanned: {booking_id}")
        return success_response(result, "Booking confirmed at library")
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        print(f"❌ Scan booking error: {e}")
        return error_response("Failed to scan booking", 500)

@app.route('/api/bookings/<int:booking_id>/leave-early', methods=['POST'])
def leave_early(booking_id):
    """User leaves seat early"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        user_id = verify_token()
        result = db.leave_seat_early(booking_id, user_id)
        
        print(f"✅ User {user_id} left seat early: booking {booking_id}")
        return success_response(result, "Seat vacated successfully")
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        print(f"❌ Leave early error: {e}")
        return error_response("Failed to leave seat", 500)

@app.route('/api/bookings/<int:booking_id>/reallocate', methods=['POST'])
def reallocate_booking(booking_id):
    """Reallocate user to a different available seat"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        user_id = verify_token()
        data = request.get_json()
        new_seat_id = data.get('newSeatId') or data.get('new_seat_id')
        
        if not new_seat_id:
            return error_response("New seat ID is required")
        
        result = db.reallocate_seat(booking_id, user_id, new_seat_id)
        
        print(f"✅ Booking reallocated: {booking_id} user {user_id} to seat {new_seat_id}")
        return success_response(result, "Seat reallocated successfully")
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        print(f"❌ Reallocate error: {e}")
        return error_response("Failed to reallocate seat", 500)

@app.route('/api/user/daily-usage', methods=['GET'])
def get_user_daily_usage():
    """Get user's daily usage (max 4 hours/day in 2 sections)"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        user_id = verify_token()
        usage = db.get_daily_usage(user_id)
        
        return success_response(usage)
        
    except Exception as e:
        print(f"❌ Daily usage error: {e}")
        return error_response("Failed to get daily usage", 500)

# Status Routes

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get system statistics"""
    try:
        stats = db.get_statistics()
        return success_response(stats)
        
    except Exception as e:
        print(f"❌ Status error: {e}")
        return error_response("Failed to get status", 500)

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return success_response({"status": "healthy", "timestamp": datetime.now().isoformat()})

# Kiosk Routes (Library System)

@app.route('/api/kiosk/verify-qr', methods=['POST'])
def verify_qr():
    """Verify QR code and get booking details"""
    try:
        data = request.get_json()
        qr_code = data.get('qrCode')
        
        if not qr_code:
            return error_response("QR code is required")
        
        # Verify QR code
        booking = db.verify_qr_code(qr_code)
        
        if not booking:
            return error_response("Invalid QR code or booking not found")
        
        print(f"✅ QR verified: Booking {booking['id']} - {booking['full_name']} (Roll: {booking['roll_number']})")
        
        return success_response(booking, "QR code verified successfully")
        
    except Exception as e:
        print(f"❌ QR verification error: {e}")
        return error_response("Failed to verify QR code", 500)

@app.route('/api/kiosk/confirm-booking', methods=['POST'])
def confirm_booking_kiosk():
    """Confirm booking at kiosk (mark as completed)"""
    try:
        data = request.get_json()
        booking_id = data.get('bookingId')
        
        if not booking_id:
            return error_response("Booking ID is required")
        
        # Confirm booking
        result = db.confirm_booking(booking_id)
        
        print(f"✅ Booking confirmed at kiosk: {booking_id}")
        
        return success_response(result, "Booking confirmed successfully")
        
    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        print(f"❌ Confirm booking error: {e}")
        return error_response("Failed to confirm booking", 500)

@app.route('/api/kiosk/verify-student', methods=['POST'])
def verify_student():
    """Verify student by roll number"""
    try:
        data = request.get_json()
        roll_number = data.get('rollNumber')
        
        if not roll_number:
            return error_response("Roll number is required")
        
        # Get student by roll number
        user = db.get_user_by_roll_number(roll_number)
        
        if not user:
            return error_response("Student not found. Please register first.")
        
        print(f"✅ Student verified: {user['full_name']} (Roll: {roll_number})")
        
        return success_response(user, "Student verified successfully")
        
    except Exception as e:
        print(f"❌ Student verification error: {e}")
        return error_response("Failed to verify student", 500)

@app.route('/api/kiosk/verify-password', methods=['POST'])
def verify_password():
    """Verify student's account password for walk-in booking"""
    try:
        data = request.get_json()
        roll_number = data.get('rollNumber')
        password = data.get('password')
        
        if not roll_number or not password:
            return error_response("Roll number and password are required")
        
        # Get user by roll number
        user = db.get_user_by_roll_number(roll_number)
        
        if not user or user.get('id') is None:
            return error_response("No online account found for this roll number")
        
        # Verify password without updating login count (read-only operation)
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT password_hash FROM users 
            WHERE (email = ? OR username = ?) AND is_active = TRUE
        ''', (user.get('email'), user.get('username')))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and db.verify_password(password, result[0]):
            print(f"✅ Password verified for: {roll_number}")
            return success_response({'verified': True}, "Password verified successfully")
        else:
            return error_response("Incorrect password")
        
    except Exception as e:
        print(f"❌ Password verification error: {e}")
        return error_response("Failed to verify password", 500)
        return error_response("Failed to verify student", 500)

@app.route('/api/kiosk/book-seat', methods=['POST'])
def book_seat_kiosk():
    """Book seat at kiosk for walk-in students"""
    try:
        data = request.get_json()
        
        roll_number = data.get('rollNumber')
        seat_number = data.get('seatNumber')
        duration = data.get('duration', 60)
        link_to_account = data.get('linkToAccount', False)  # True if "Send to Account" chosen
        
        if not roll_number or not seat_number:
            return error_response("Roll number and seat number are required")
        
        # Check if student is approved
        student_status = db.is_student_approved(roll_number)
        if not student_status or student_status != 'approved':
            return error_response("Student not approved or not found in system")
        
        # Get student details from approved_students
        approved_student = db.get_approved_student_by_roll(roll_number)
        
        # Check if student has an online account
        online_user = db.get_user_by_roll_number(roll_number)
        has_online_account = online_user is not None and online_user.get('id') is not None
        
        # Create walk-in booking with code
        booking_result = db.create_walk_in_booking(
            roll_number=roll_number,
            seat_number=seat_number,
            duration_minutes=duration,
            link_to_user=has_online_account and link_to_account,
            user_id=online_user.get('id') if (has_online_account and link_to_account) else None
        )
        
        # Prepare response with student details
        response_data = {
            'booking': booking_result,
            'student': {
                'full_name': approved_student['full_name'],
                'roll_number': roll_number,
                'email': online_user.get('email') if has_online_account else None,
                'has_online_account': has_online_account
            },
            'walk_in_code': booking_result['walk_in_code'],
            'linked_to_account': has_online_account and link_to_account
        }
        
        print(f"✅ Walk-in booking created: Seat {seat_number} for {roll_number} (Code: {booking_result['walk_in_code']})")
        
        return success_response(response_data, "Walk-in booking created successfully")
        
    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        print(f"❌ Kiosk booking error: {e}")
        return error_response("Failed to book seat", 500)

@app.route('/api/kiosk/cancel-by-code', methods=['POST'])
def cancel_walk_in_by_code():
    """Cancel walk-in booking using walk-in code"""
    try:
        data = request.get_json()
        walk_in_code = data.get('walkInCode')
        
        if not walk_in_code:
            return error_response("Walk-in code is required")
        
        # Cancel booking by code
        result = db.cancel_walk_in_booking_by_code(walk_in_code)
        
        print(f"✅ Walk-in booking cancelled by code: {walk_in_code}")
        
        return success_response(result, "Walk-in booking cancelled successfully")
        
    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        print(f"❌ Cancel by code error: {e}")
        return error_response("Failed to cancel booking", 500)


# Admin Routes

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """Admin login"""
    try:
        data = request.get_json()
        
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return error_response("Username and password required")
        
        # Authenticate admin
        admin = db.authenticate_admin(username, password)
        # Create persistent session with longer TTL for admin (7 days)
        session = db.create_session(admin['id'], ttl_minutes=7*24*60)
        admin['token'] = session['token']
        admin['token_expires_at'] = session['expires_at'].isoformat()

        print(f"✅ Admin logged in: {admin['username']} (ID: {admin['id']})")
        
        return success_response(admin, "Admin login successful")
        
    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        print(f"❌ Admin login error: {e}")
        return error_response("Admin login failed", 500)

@app.route('/api/admin/create', methods=['POST'])
def create_admin():
    """Create new admin account"""
    try:
        # Verify admin token
        creator_id = verify_admin_token()
        if not creator_id:
            return error_response("Admin authentication required", 401)
        
        data = request.get_json()
        
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        
        if not username or not password:
            return error_response("Username and password required")
        
        # Create admin
        admin = db.create_admin(username, password, email, creator_id)
        
        print(f"✅ Admin created: {admin['username']} by admin {creator_id}")
        
        return success_response(admin, "Admin created successfully")
        
    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        print(f"❌ Create admin error: {e}")
        return error_response("Failed to create admin", 500)

@app.route('/api/admin/change-password', methods=['POST'])
def change_admin_password():
    """Change admin password"""
    try:
        # Verify admin token
        admin_id = verify_admin_token()
        if not admin_id:
            return error_response("Admin authentication required", 401)
        
        data = request.get_json()
        
        new_password = data.get('newPassword')
        target_admin_id = data.get('adminId', admin_id)
        
        if not new_password:
            return error_response("New password required")
        
        # Change password
        db.change_admin_password(target_admin_id, new_password)
        
        print(f"✅ Password changed for admin {target_admin_id}")
        
        return success_response(message="Password changed successfully")
        
    except Exception as e:
        print(f"❌ Change password error: {e}")
        return error_response("Failed to change password", 500)

@app.route('/api/admin/admins', methods=['GET'])
def get_admins():
    """Get all admin accounts"""
    try:
        # Verify admin token
        admin_id = verify_admin_token()
        if not admin_id:
            return error_response("Admin authentication required", 401)
        
        admins = db.get_all_admins()
        
        return success_response(admins)
        
    except Exception as e:
        print(f"❌ Get admins error: {e}")
        return error_response("Failed to get admins", 500)

@app.route('/api/admin/students/upload', methods=['POST'])
def upload_students():
    """Upload approved students from CSV"""
    try:
        # Verify admin token
        admin_id = verify_admin_token()
        if not admin_id:
            return error_response("Admin authentication required", 401)
        
        data = request.get_json()
        students = data.get('students', [])
        
        if not students:
            return error_response("No students data provided")
        
        result = db.upload_approved_students(students, admin_id)
        
        print(f"✅ Uploaded {result['added']} students, skipped {result['skipped']}")
        
        return success_response(result, "Students uploaded successfully")
        
    except Exception as e:
        print(f"❌ Upload students error: {e}")
        return error_response("Failed to upload students", 500)

@app.route('/api/admin/students', methods=['GET'])
def get_approved_students():
    """Get all approved students"""
    try:
        # Verify admin token
        admin_id = verify_admin_token()
        if not admin_id:
            return error_response("Admin authentication required", 401)
        
        students = db.get_approved_students()
        
        return success_response(students)
        
    except Exception as e:
        print(f"❌ Get students error: {e}")
        return error_response("Failed to get students", 500)

@app.route('/api/admin/students/<roll_number>/status', methods=['PUT'])
def update_student_status(roll_number):
    """Update student status (approved/blocked/waiting)"""
    try:
        # Verify admin token
        admin_id = verify_admin_token()
        if not admin_id:
            return error_response("Admin authentication required", 401)
        
        data = request.get_json()
        status = data.get('status')
        
        if status not in ['approved', 'blocked', 'waiting']:
            return error_response("Invalid status")
        
        db.update_student_status(roll_number, status)
        
        print(f"✅ Student {roll_number} status updated to {status}")
        
        return success_response(message=f"Student status updated to {status}")
        
    except Exception as e:
        print(f"❌ Update status error: {e}")
        return error_response("Failed to update status", 500)

@app.route('/api/admin/users', methods=['GET'])
def get_all_users():
    """Get all registered users"""
    try:
        # Verify admin token
        admin_id = verify_admin_token()
        if not admin_id:
            return error_response("Admin authentication required", 401)
        
        users = db.get_all_users_with_status()
        
        return success_response(users)
        
    except Exception as e:
        print(f"❌ Get users error: {e}")
        return error_response("Failed to get users", 500)

@app.route('/api/admin/users/<int:user_id>/block', methods=['POST'])
def block_user(user_id):
    """Block a user"""
    try:
        # Verify admin token
        admin_id = verify_admin_token()
        if not admin_id:
            return error_response("Admin authentication required", 401)
        
        admin_id = int(admin_id.replace('admin_', ''))
        
        data = request.get_json()
        reason = data.get('reason', 'Blocked by admin')
        
        db.block_user(user_id, reason, admin_id)
        
        print(f"✅ User {user_id} blocked by admin {admin_id}")
        
        return success_response(message="User blocked successfully")
        
    except Exception as e:
        print(f"❌ Block user error: {e}")
        return error_response("Failed to block user", 500)

@app.route('/api/admin/users/<int:user_id>/unblock', methods=['POST'])
def unblock_user(user_id):
    """Unblock a user"""
    try:
        # Verify admin token
        admin_id = verify_admin_token()
        if not admin_id:
            return error_response("Admin authentication required", 401)
        
        db.unblock_user(user_id)
        
        print(f"✅ User {user_id} unblocked")
        
        return success_response(message="User unblocked successfully")
        
    except Exception as e:
        print(f"❌ Unblock user error: {e}")
        return error_response("Failed to unblock user", 500)

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Permanently delete a user and all their data"""
    try:
        # Verify admin token
        admin_id = verify_admin_token()
        if not admin_id:
            return error_response("Admin authentication required", 401)
        
        # Delete all user's bookings
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bookings WHERE user_id = ?", (user_id,))
        
        # Delete from blocked_users if exists
        cursor.execute("DELETE FROM blocked_users WHERE user_id = ?", (user_id,))
        
        # Delete the user
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        
        conn.commit()
        conn.close()
        
        print(f"✅ User {user_id} permanently deleted")
        
        return success_response(message="User permanently deleted")
        
    except Exception as e:
        print(f"❌ Delete user error: {e}")
        return error_response("Failed to delete user", 500)

@app.route('/api/admin/users/<int:user_id>/reset-usage', methods=['POST'])
def reset_user_daily_usage(user_id):
    """Reset daily usage counters for a specific user"""
    try:
        # Verify admin token
        admin_id = verify_admin_token()
        if not admin_id:
            return error_response("Admin authentication required", 401)
        
        # Reset the user's daily usage
        db.reset_daily_usage(user_id)
        
        print(f"✅ Daily usage reset for user {user_id} by admin")
        
        return success_response(message="Daily usage reset successfully")
        
    except Exception as e:
        print(f"❌ Reset daily usage error: {e}")
        return error_response("Failed to reset daily usage", 500)

@app.route('/api/admin/bookings', methods=['GET'])
def get_all_bookings():
    """Get all bookings"""
    try:
        # Verify admin token
        admin_id = verify_admin_token()
        if not admin_id:
            return error_response("Admin authentication required", 401)
        
        bookings = db.get_all_bookings_admin()
        
        return success_response(bookings)
        
    except Exception as e:
        print(f"❌ Get bookings error: {e}")
        return error_response("Failed to get bookings", 500)

@app.route('/api/admin/bookings/<int:booking_id>', methods=['DELETE'])
def remove_booking(booking_id):
    """Remove a specific booking"""
    try:
        # Verify admin token
        admin_id = verify_admin_token()
        if not admin_id:
            return error_response("Admin authentication required", 401)
        
        db.remove_booking_admin(booking_id)
        
        print(f"✅ Booking {booking_id} removed by admin")
        
        return success_response(message="Booking removed successfully")
        
    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        print(f"❌ Remove booking error: {e}")
        return error_response("Failed to remove booking", 500)

@app.route('/api/admin/bookings/clear-all', methods=['POST'])
def clear_all_bookings_route():
    """Clear all bookings"""
    try:
        # Verify admin token
        admin_id = verify_admin_token()
        if not admin_id:
            return error_response("Admin authentication required", 401)
        
        db.clear_all_bookings()
        
        print(f"✅ All bookings cleared by admin")
        
        return success_response(message="All bookings cleared successfully")
        
    except Exception as e:
        print(f"❌ Clear bookings error: {e}")
        return error_response("Failed to clear bookings", 500)

@app.route('/api/admin/seats/<seat_number>/status', methods=['POST'])
def update_seat_status(seat_number):
    """Admin: Update seat status (maintenance/available)"""
    admin_error = require_admin()
    if admin_error:
        return admin_error
    
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if new_status not in ['available', 'maintenance']:
            return error_response("Invalid status. Use 'available' or 'maintenance'")
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('UPDATE seats SET status = ? WHERE seat_number = ?', (new_status, seat_number))
        
        if cursor.rowcount == 0:
            conn.close()
            return error_response("Seat not found", 404)
        
        conn.commit()
        conn.close()
        
        print(f"✅ Seat {seat_number} status updated to {new_status}")
        return success_response({'seat_number': seat_number, 'status': new_status}, message=f"Seat status updated to {new_status}")
        
    except Exception as e:
        print(f"❌ Update seat status error: {e}")
        return error_response("Failed to update seat status", 500)

# Error handlers

@app.errorhandler(404)
def not_found(error):
    return error_response("Not found", 404)

@app.errorhandler(500)
def internal_error(error):
    return error_response("Internal server error", 500)

# ============================
# BOOK MANAGEMENT ROUTES
# ============================

# Get all book categories
@app.route('/api/books/categories', methods=['GET'])
def get_categories():
    try:
        categories = db.get_all_categories()
        return success_response({
            'categories': [dict(c) for c in categories]
        })
    except Exception as e:
        print(f"Error getting categories: {e}")
        return error_response(str(e))

# Add new category (Admin only)
@app.route('/api/admin/books/categories', methods=['POST'])
def add_category():
    if not verify_admin_token():
        return error_response("Unauthorized", 401)
    
    try:
        data = request.json
        name = data.get('name')
        description = data.get('description')
        
        if not name:
            return error_response("Category name is required")
        
        category_id = db.add_category(name, description)
        return success_response({'category_id': category_id})
    except Exception as e:
        print(f"Error adding category: {e}")
        return error_response(str(e))

# Delete category (Admin only)
@app.route('/api/admin/books/categories/<int:category_id>', methods=['DELETE'])
def delete_category(category_id):
    if not verify_admin_token():
        return error_response("Unauthorized", 401)
    
    try:
        db.delete_category(category_id)
        return success_response({'message': 'Category deleted'})
    except Exception as e:
        print(f"Error deleting category: {e}")
        return error_response(str(e))

# Get all books (Public)
@app.route('/api/books', methods=['GET'])
def get_books():
    try:
        category_id = request.args.get('category_id')
        search_query = request.args.get('search')
        
        books = db.get_all_books(category_id=category_id, search_query=search_query)
        return success_response({
            'books': [dict(b) for b in books]
        })
    except Exception as e:
        print(f"Error getting books: {e}")
        return error_response(str(e))

# Get single book details
@app.route('/api/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    try:
        book = db.get_book_by_id(book_id)
        if not book:
            return error_response("Book not found", 404)
        return success_response({'book': dict(book)})
    except Exception as e:
        print(f"Error getting book: {e}")
        return error_response(str(e))

# Add new book (Admin only)
@app.route('/api/admin/books', methods=['POST'])
def add_book():
    if not verify_admin_token():
        return error_response("Unauthorized", 401)
    
    try:
        data = request.json
        book_id = db.add_book(
            title=data.get('title'),
            author=data.get('author'),
            isbn=data.get('isbn'),
            category_id=data.get('category_id'),
            shelf_number=data.get('shelf_number'),
            rack_number=data.get('rack_number'),
            total_copies=data.get('total_copies', 1),
            cover_image_url=data.get('cover_image_url'),
            online_resource_link=data.get('online_resource_link'),
            description=data.get('description'),
            publisher=data.get('publisher'),
            publication_year=data.get('publication_year')
        )
        return success_response({'book_id': book_id})
    except Exception as e:
        print(f"Error adding book: {e}")
        return error_response(str(e))

# Update book (Admin only)
@app.route('/api/admin/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    if not verify_admin_token():
        return error_response("Unauthorized", 401)
    
    try:
        data = request.json
        db.update_book(book_id, **data)
        return success_response({'message': 'Book updated'})
    except Exception as e:
        print(f"Error updating book: {e}")
        return error_response(str(e))

# Delete book (Admin only)
@app.route('/api/admin/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    if not verify_admin_token():
        return error_response("Unauthorized", 401)
    
    try:
        db.delete_book(book_id)
        return success_response({'message': 'Book deleted'})
    except Exception as e:
        print(f"Error deleting book: {e}")
        return error_response(str(e))

# Issue book to user
@app.route('/api/books/<int:book_id>/issue', methods=['POST'])
def issue_book(book_id):
    user = verify_session(request)
    if not user:
        return error_response("Unauthorized", 401)
    
    try:
        data = request.json
        due_days = data.get('due_days', 14)
        result = db.issue_book(book_id, user['id'], due_days)
        
        if result.get('success'):
            return success_response(result)
        else:
            return error_response(result.get('error', 'Failed to issue book'))
    except Exception as e:
        print(f"Error issuing book: {e}")
        return error_response(str(e))

# Return book
@app.route('/api/books/issues/<int:issue_id>/return', methods=['POST'])
def return_book(issue_id):
    user = verify_session(request)
    if not user:
        return error_response("Unauthorized", 401)
    
    try:
        data = request.json
        fine_amount = data.get('fine_amount', 0.0)
        result = db.return_book(issue_id, fine_amount)
        
        if result.get('success'):
            return success_response(result)
        else:
            return error_response(result.get('error', 'Failed to return book'))
    except Exception as e:
        print(f"Error returning book: {e}")
        return error_response(str(e))

# Get user's issued books
@app.route('/api/books/my-issues', methods=['GET'])
def get_my_issued_books():
    user = verify_session(request)
    if not user:
        return error_response("Unauthorized", 401)
    
    try:
        issues = db.get_user_issued_books(user['id'])
        return success_response({
            'issues': [dict(i) for i in issues]
        })
    except Exception as e:
        print(f"Error getting issued books: {e}")
        return error_response(str(e))

# Get all issued books (Admin only)
@app.route('/api/admin/books/issues', methods=['GET'])
def get_all_issued_books():
    if not verify_admin_token():
        return error_response("Unauthorized", 401)
    
    try:
        status = request.args.get('status')
        issues = db.get_all_issued_books(status=status)
        return success_response({
            'issues': [dict(i) for i in issues]
        })
    except Exception as e:
        print(f"Error getting all issued books: {e}")
        return error_response(str(e))

# Run server
if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Starting Library Management System API Server...")
    print("="*50)
    print(f"📊 Database: {db.db_path}")
    print(f"🌐 Server will run on: http://localhost:5000")
    print("\n📋 Available API endpoints:")
    print("  POST /api/register     - Register new user")
    print("  POST /api/login        - User login")
    print("  POST /api/logout       - User logout")
    print("  GET  /api/user/profile - Get user profile")
    print("  GET  /api/seats        - Get all seats")
    print("  GET  /api/seats/available - Get available seats")
    print("  POST /api/bookings     - Create booking")
    print("  GET  /api/bookings/user - Get user bookings")
    print("  POST /api/bookings/{id}/cancel - Cancel booking")
    print("  GET  /api/status       - System statistics")
    print("  GET  /api/health       - Health check")
    print("\n🏛️ Library Kiosk endpoints:")
    print("  POST /api/kiosk/verify-qr - Verify QR code")
    print("  POST /api/kiosk/confirm-booking - Confirm booking")
    print("  POST /api/kiosk/verify-student - Verify student by roll number")
    print("  POST /api/kiosk/book-seat - Book seat for walk-in student")
    print("\n👑 Admin Panel endpoints:")
    print("  POST /api/admin/login - Admin login")
    print("  POST /api/admin/create - Create new admin")
    print("  POST /api/admin/students/upload - Upload students CSV")
    print("  GET  /api/admin/students - Get approved students")
    print("  GET  /api/admin/users - Get all users")
    print("  GET  /api/admin/bookings - Get all bookings")
    print("  POST /api/admin/users/{id}/block - Block user")
    print("  POST /api/admin/users/{id}/unblock - Unblock user")
    print("  DELETE /api/admin/bookings/{id} - Remove booking")
    print("  POST /api/admin/bookings/clear-all - Clear all bookings")
    print("\n🌐 Access the system:")
    print("  📚 Student Portal:  http://localhost:5000/offline_form.html")
    print("  🏛️ Library Kiosk:   http://localhost:5000/library_kiosk.html")
    print("  👑 Admin Panel:     http://localhost:5000/admin.html")
    print("\n🔐 Default super admin: admin123 / nani#322989")
    print("\n✅ Starting server...\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
