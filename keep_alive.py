<<<<<<< HEAD
from flask import Flask
from threading import Thread

app = Flask(' ')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0',port=8080)

def keep_alive():
    t = Thread(target=run)
=======
from flask import Flask
from threading import Thread

app = Flask(' ')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0',port=8080)

def keep_alive():
    t = Thread(target=run)
>>>>>>> 3d47149e842d3b694a1328ce4575c6dae81ffacc
    t.start()