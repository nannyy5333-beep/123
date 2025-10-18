import os
from flask import Flask, session, request, redirect, url_for
from dotenv import load_dotenv


def create_app():
    load_dotenv()

    app = Flask(__name__)
    # Один способ задания секрета, без дублей:
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "change_me")

    # Blueprints
    from blueprints.auth import bp as auth_bp
    from blueprints.products import bp as products_bp
    from blueprints.orders import bp as orders_bp
    from blueprints.customers import bp as customers_bp
    from blueprints.inventory import bp as inventory_bp
    from blueprints.analytics import bp as analytics_bp
    from blueprints.finances import bp as finances_bp
    from blueprints.scheduled import bp as scheduled_bp
    from blueprints.categories import bp as categories_bp
    from blueprints.exports import bp as exports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp, url_prefix="/products")
    app.register_blueprint(orders_bp, url_prefix="/orders")
    app.register_blueprint(customers_bp, url_prefix="/customers")
    app.register_blueprint(inventory_bp, url_prefix="/inventory")
    app.register_blueprint(analytics_bp, url_prefix="/analytics")
    app.register_blueprint(finances_bp, url_prefix="/finances")
    app.register_blueprint(scheduled_bp, url_prefix="/scheduled")
    app.register_blueprint(categories_bp, url_prefix="/categories")
    app.register_blueprint(exports_bp, url_prefix="/exports")

    # Хелперы ролей в шаблонах
    from utils.auth import role_in, has_role

    @app.context_processor
    def inject_roles():
        env = (os.getenv("APP_ENV") or os.getenv("FLASK_ENV") or "prod").lower()
        mapping = {
            "production": ("Production", "env-prod"),
            "prod": ("Production", "env-prod"),
            "staging": ("Staging", "env-stage"),
            "stage": ("Staging", "env-stage"),
            "dev": ("Development", "env-dev"),
            "development": ("Development", "env-dev"),
        }
        env_label, env_class = mapping.get(env, ("Production", "env-prod"))
        return dict(role_in=role_in, has_role=has_role, env_label=env_label, env_class=env_class)

    @app.route("/")
    def idx():
        # Если у тебя другой landing — поменяй endpoint ниже
        return redirect(url_for("analytics.dashboard"))

    @app.route("/i18n/<lang>")
    def set_lang(lang):
        lang = (lang or "").lower()
        if lang in ("ru", "uz"):
            session["lang"] = lang
        nxt = request.referrer or url_for("idx")
        return redirect(nxt)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)

