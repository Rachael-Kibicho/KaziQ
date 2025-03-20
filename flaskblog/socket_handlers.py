from flask_socketio import SocketIO, emit, join_room, leave_room

# Initialize SocketIO
socketio = SocketIO()

def register_socket_handlers(app):
    """Register all the Socket.IO event handlers."""
    @socketio.on('connect')
    def handle_connect():
        print("Client connected")

    @socketio.on('disconnect')
    def handle_disconnect():
        print("Client disconnected")

    @socketio.on('private_message')
    def handle_private_message(data):
        sender = data['sender']
        receiver = data['receiver']
        message = data['message']

        # Emit the message to the receiver
        emit('new_message', {'sender': sender, 'message': message}, room=receiver)

        # Optionally emit back to the sender
        emit('new_message', {'sender': sender, 'message': message}, room=sender)

    # Initialize SocketIO with the app
    socketio.init_app(app)
