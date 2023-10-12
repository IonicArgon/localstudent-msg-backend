from flask import Flask

from app.routes.leadsRoute import leads_route_bp

app = Flask(__name__)

# register the blueprints
app.register_blueprint(leads_route_bp, url_prefix="/api")


if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=5000, use_reloader=True)