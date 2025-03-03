from livereload import Server
from flaskblog import app  # Import your Flask app

server = Server(app.wsgi)  # Use WSGI interface of your app
server.watch('flaskblog.py')  # Watch your main Flask file
server.serve()

