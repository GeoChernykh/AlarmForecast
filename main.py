from flask import Flask
from app.errors import register_error_handlers


def create_app():
    app = Flask(__name__)

    

    register_error_handlers(app)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)