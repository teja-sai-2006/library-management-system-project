#!/bin/bash

echo "🚀 Starting Library Management System..."
echo "======================================="

# Go to project directory
cd /home/teja_sai/Music/dta_lab_project

# Kill any existing Python servers
echo "🧹 Cleaning up existing servers..."
pkill -9 -f "python.*api_server" 2>/dev/null
fuser -k 5000/tcp 2>/dev/null
sleep 1

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source library_env/bin/activate

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ Failed to activate virtual environment"
    exit 1
fi

# Start the backend server
echo "🌐 Starting backend server..."
echo ""

# Run server in background and redirect output
nohup python api_server.py > server.log 2>&1 &
SERVER_PID=$!

# Wait for server to start
echo "⏳ Waiting for server to initialize..."
sleep 3

# Check if server is running
if ps -p $SERVER_PID > /dev/null; then
    echo ""
    echo "✅ Server started successfully! (PID: $SERVER_PID)"
    echo ""
    
    # Test if server is responding
    if curl -s http://localhost:5000/api/health > /dev/null 2>&1; then
        echo "✅ Server is responding to requests"
    else
        echo "⚠️  Server process running but not responding yet (may need a few more seconds)"
    fi
    
    echo ""
    echo "📱 Access the system at:"
    echo "   Student Portal:  http://localhost:5000/offline_form.html"
    echo "   Seat Booking:    http://localhost:5000/seat_booking.html"
    echo "   Library Kiosk:   http://localhost:5000/library_kiosk.html"
    echo "   Dashboard:       http://localhost:5000/dashboard.html"
    echo "   Books Tracking:  http://localhost:5000/books_tracking.html"
    echo "   Admin Panel:     http://localhost:5000/admin.html"
    echo ""
    echo "📋 Server logs: tail -f server.log"
    echo "🛑 Stop server: pkill -f 'python.*api_server' or kill $SERVER_PID"
    echo ""
    echo "Press Ctrl+C to stop monitoring (server will continue running)"
    echo ""
    
    # Monitor server log
    tail -f server.log
else
    echo ""
    echo "❌ Failed to start server. Check server.log for errors:"
    cat server.log
    exit 1
fi
