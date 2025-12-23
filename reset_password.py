#!/usr/bin/env python3
"""
Simple utility to reset user password in the database for testing
"""

import sqlite3
import hashlib
import sys
import os

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def reset_user_password(username, new_password):
    """Reset password for a specific user"""
    db_path = 'library_database.db'
    
    if not os.path.exists(db_path):
        print("❌ Database file not found!")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id, username, email FROM users WHERE username = ? OR email = ?", (username, username))
        user = cursor.fetchone()
        
        if not user:
            print(f"❌ User '{username}' not found!")
            conn.close()
            return False
        
        # Update password
        hashed_password = hash_password(new_password)
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed_password, user[0]))
        conn.commit()
        
        print(f"✅ Password updated successfully!")
        print(f"👤 User ID: {user[0]}")
        print(f"📛 Username: {user[1]}")
        print(f"📧 Email: {user[2]}")
        print(f"🔐 New Password: {new_password}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error updating password: {e}")
        return False

if __name__ == "__main__":
    print("🔐 Password Reset Utility")
    print("=" * 40)
    
    # Reset teja_sai password to a known value
    username = "teja_sai"
    new_password = "test123"
    
    print(f"Resetting password for user: {username}")
    print(f"New password will be: {new_password}")
    print()
    
    if reset_user_password(username, new_password):
        print("\n🎉 You can now login with:")
        print(f"   Username: {username}")
        print(f"   Password: {new_password}")
        print("\n🔗 Test at: http://localhost:5000/login_diagnostic.html")
    else:
        print("\n❌ Failed to reset password!")