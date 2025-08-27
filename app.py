from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello World!'

@app.route('/login')
def login():
    return 'Hello Login!'

@app.route('/user/<username>')
def profile(username): pass

if __name__ == '__main__':
    app.debug = True
    app.run(port=8900)
