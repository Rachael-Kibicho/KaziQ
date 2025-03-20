from flaskblog import app  # Import your Flask app instance
from flaskblog.socket_handlers import socketio, register_socket_handlers

# Register Socket.IO handlers
register_socket_handlers(app)

if __name__ == '__main__':
    # Use socketio.run instead of app.run to enable WebSocket functionality
    socketio.run(app, debug=True)
