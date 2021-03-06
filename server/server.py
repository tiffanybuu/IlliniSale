from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from flask import Flask, g, request, make_response
from core.database import connect_db
from core.permission import auth
from core.auto_complete import AutoCompleteProvider
from threading import Thread
import jobs
import json
import jwt
import config

app = Flask(__name__)

from core.user import user
app.register_blueprint(user, url_prefix="/api")
from core.product import product
app.register_blueprint(product, url_prefix="/api")
from core.wantlist import wantlist
app.register_blueprint(wantlist, url_prefix="/api")
from core.message import message
app.register_blueprint(message, url_prefix="/api")
from core.bid import bid
app.register_blueprint(bid, url_prefix="/api")
from core.comment import comment
app.register_blueprint(comment, url_prefix="/api")
from core.notification import notification
app.register_blueprint(notification, url_prefix="/api")

def start_autocomplete_init():
    app.autocomplete_provider = AutoCompleteProvider()
    autocomplete_job_thread = Thread(target=autocomplete_init)
    autocomplete_job_thread.setDaemon(True)
    autocomplete_job_thread.start()

def autocomplete_init():
    app.autocomplete_provider.load_candidates()

@app.before_request
def before_request():
    g.db = connect_db()

    g.user_id = None
    auth_header = request.headers.get("Authorization")
    if auth_header is not None and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        payload = jwt.decode(token, config.SERVER_SECRET, algorithms=['HS256'])
        cur = g.db.cursor()
        cur.execute("SELECT UserId FROM User WHERE UserId = %s", (str(payload["user_id"]),))
        user_data = cur.fetchone()
        if user_data:
            g.user_id = payload["user_id"]

@app.after_request
def after_request(response):
    if g.db:
        g.db.close()

    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    response.headers.add("Access-Control-Allow-Headers", "Authorization, Content-Type")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")

    return response

@auth.verify_password
def verify_password(username, password):
    return False if g.user_id is None else True

    # try:
    #     payload = jwt.decode(g.token, config.SERVER_SECRET, algorithms=['HS256'])
    #     cur = g.db.cursor()
    #     cur.execute("SELECT UserId FROM User WHERE UserId = %s", str(payload["user_id"]))
    #     user_data = cur.fetchone()
    #     if user_data:
    #         g.user_id = payload["user_id"]
    #         return True
    #     else:
    #         return False
    # except:
    #     return False

@auth.error_handler
def unauthorized():
    return make_response(json.dumps({"msg": "Unauthorized access"}), 403)

@app.errorhandler(404)
def not_found(error):
    return make_response(json.dumps({"msg": "Not found"}), 404)

start_autocomplete_init()
jobs.start_background_jobs()

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', debug=True)

if __name__ == '__main__':
    http_server = HTTPServer(WSGIContainer(app))
    http_server.listen(5000)
    print "Flask app starting..."
    IOLoop.instance().start()