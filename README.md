# 🏛️ Library Management System

A comprehensive web-based library management system with seat booking, book tracking, student management, and admin dashboard functionalities. Built with Flask backend and vanilla JavaScript frontend.

## ✨ Features

### 📚 Core Modules
- **Student Dashboard** - View bookings, borrow books, and manage profile
- **Seat Booking System** - Real-time seat reservation with QR code scanning
- **Book Tracking** - Borrow and return books with due date management
- **Admin Panel** - Comprehensive control over students, seats, books, and system settings
- **Library Kiosk** - Walk-in student registration and seat allocation
- **Offline Mode** - Continue operations without internet connectivity

### 🔐 Security Features
- Token-based authentication with persistent sessions
- Password hashing with SHA-256
- Role-based access control (Student/Admin)
- Session management with automatic cleanup

### 🎯 Key Capabilities
- **Real-time Seat Management** - View available seats with live updates
- **QR Code Integration** - Scan codes for quick seat check-in
- **Auto-expiry System** - Automatic cleanup of expired bookings
- **Walk-in Support** - Generate temporary codes for non-registered students
- **Fine Management** - Automated fine calculation for overdue books
- **Multi-threading** - Background tasks for booking expiry

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Linux/macOS/Windows with bash support

### Installation

1. **Clone or download the project**
```bash
cd /path/to/dta_lab_project
```

2. **Create a virtual environment**
```bash
python3 -m venv library_env
```

3. **Activate the virtual environment**

On Linux/macOS:
```bash
source library_env/bin/activate
```

On Windows:
```bash
library_env\Scripts\activate
```

4. **Install dependencies**
```bash
pip install -r requirements.txt
```

5. **Initialize the database**
```bash
python database_setup.py
```

6. **Populate sample data (optional)**
```bash
python populate_library.py
```

This will create:
- Sample students from `sample_students.csv`
- Library seats (1-50)
- Sample books

### Running the Application

#### Option 1: Using the run script (Linux/macOS)
```bash
chmod +x run.sh
./run.sh
```

#### Option 2: Manual start
```bash
# Activate virtual environment
source library_env/bin/activate  # On Windows: library_env\Scripts\activate

# Start the server
python api_server.py
```

The server will start on `http://localhost:5000`

### Accessing the Application

Open your web browser and navigate to:
- **Login Page**: http://localhost:5000
- **Admin Dashboard**: http://localhost:5000/admin.html
- **Student Dashboard**: http://localhost:5000/dashboard.html
- **Library Kiosk**: http://localhost:5000/library_kiosk.html

### Default Credentials

After running `populate_library.py`, you can use:

**Admin Account:**
- Email: `admin@library.com`
- Password: `admin123`

**Sample Student Account:**
- Email: Check `sample_students.csv` for student emails
- Password: `password123` (default for all sample students)

---

## 📁 Project Structure

```
dta_lab_project/
├── api_server.py              # Flask backend server
├── database_setup.py          # Database schema and manager
├── populate_library.py        # Script to populate sample data
├── reset_password.py          # Password reset utility
├── requirements.txt           # Python dependencies
├── run.sh                     # Startup script
│
├── index.html                 # Login page
├── dashboard.html             # Student dashboard
├── admin.html                 # Admin panel
├── seat_booking.html          # Seat booking interface
├── books_tracking.html        # Book management
├── library_kiosk.html         # Walk-in kiosk
├── offline_form.html          # Offline booking form
│
├── sample_students.csv        # Sample student data
├── library_database.db        # SQLite database (created on init)
├── library_env/               # Virtual environment
└── offline_resources/         # Offline mode assets
```

---

## 🗄️ Database Schema

The system uses SQLite with the following main tables:

- **students** - User accounts and profiles
- **seats** - Library seat information
- **bookings** - Seat reservations and history
- **books** - Book catalog
- **borrowed_books** - Borrowing transactions
- **sessions** - User session management
- **walk_in_students** - Temporary walk-in registrations

---

## 🛠️ API Endpoints

### Authentication
- `POST /api/login` - User login
- `POST /api/logout` - User logout
- `POST /api/register` - Student registration
- `POST /api/check-session` - Validate session

### Student Operations
- `GET /api/student/profile` - Get student profile
- `PUT /api/student/profile` - Update profile
- `GET /api/student/bookings` - Get booking history
- `GET /api/student/borrowed-books` - Get borrowed books

### Seat Management
- `GET /api/seats` - Get all seats with availability
- `POST /api/book-seat` - Book a seat
- `POST /api/cancel-booking` - Cancel booking
- `POST /api/check-in` - Check-in with QR code
- `POST /api/check-out` - Check-out from seat

### Book Management
- `GET /api/books` - Get all books
- `POST /api/borrow-book` - Borrow a book
- `POST /api/return-book` - Return a book

### Admin Operations
- `GET /api/admin/*` - Various admin endpoints
- `POST /api/admin/*` - Admin data modifications
- `DELETE /api/admin/*` - Admin deletions

### Walk-in System
- `POST /api/walk-in/check-in` - Walk-in student check-in
- `POST /api/walk-in/verify-code` - Verify walk-in code

---

## ⚙️ Configuration

### Environment Variables
Create a `.env` file in the root directory:

```env
SECRET_KEY=your-secret-key-here
DATABASE_PATH=library_database.db
PORT=5000
DEBUG=False
```

### Database Configuration
Edit `database_setup.py` to modify:
- Database path
- Table schemas
- Default values

---

## 🔧 Maintenance

### Reset Password
```bash
python reset_password.py
```

### Backup Database
```bash
cp library_database.db library_database_backup_$(date +%Y%m%d).db
```

### View Logs
```bash
tail -f server.log
```

### Stop Server
```bash
pkill -f "python.*api_server"
# or
fuser -k 5000/tcp
```

---

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Find and kill the process using port 5000
fuser -k 5000/tcp
# or
lsof -ti:5000 | xargs kill -9
```

### Database Locked
- Check if another process is accessing the database
- Restart the server
- Database uses WAL mode for better concurrency

### Virtual Environment Issues
```bash
# Deactivate and recreate
deactivate
rm -rf library_env
python3 -m venv library_env
source library_env/bin/activate
pip install -r requirements.txt
```

### Module Not Found
```bash
# Ensure virtual environment is activated
source library_env/bin/activate
pip install -r requirements.txt
```

---

## 📝 Development

### Adding New Features
1. Update database schema in `database_setup.py`
2. Add API endpoints in `api_server.py`
3. Create/update frontend HTML files
4. Test thoroughly before deployment

### Code Style
- Python: PEP 8 compliant
- JavaScript: ES6+ with clear comments
- HTML/CSS: Semantic and responsive design

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

## 📄 License

This project is created for educational purposes.

---

## 👨‍💻 Support

For issues or questions:
- Check the troubleshooting section
- Review server logs in `server.log`
- Check browser console for frontend errors

---

## 🎉 Acknowledgments

Built with:
- Flask - Web framework
- SQLite - Database
- Vanilla JavaScript - Frontend
- Bootstrap concepts - Styling inspiration

---

**Version:** 1.0.0  
**Last Updated:** December 2025  
**Status:** Active Development
# library-management-system-project
