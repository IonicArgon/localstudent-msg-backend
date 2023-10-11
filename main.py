from flask import Flask

app = Flask(__name__)


if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=5000, use_reloader=True)