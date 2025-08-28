export FLASK_APP=app
export FLASK_ENV=development
PORT=8900 python app.py --debug
# alternative without websocket (and with reload)
# python -m flask run --port=5000 --debug
