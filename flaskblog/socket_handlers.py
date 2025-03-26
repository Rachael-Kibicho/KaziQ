from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import login_user, current_user, logout_user, login_required

# Initialize SocketIO
socketio = SocketIO()

def register_socket_handlers(app):
    """Register all the Socket.IO event handlers."""
    @socketio.on("connect")
    @login_required
    def handle_connect():
        join_room(str(current_user.id))
        print(f"{current_user.username} connected to room {current_user.id}")


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
