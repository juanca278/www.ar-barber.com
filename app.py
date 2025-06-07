from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import sqlite3
import requests
from waitress import serve
from jinja2 import DictLoader
import os

# ───── Configuración principal ─────
app = Flask(__name__)
app.secret_key = 'TU_CLAVE_SECRETA_AQUI'  # Cámbiala por algo seguro en producción

# Token y chat_id de Telegram (obtenidos de BotFather y getUpdates)
TELEGRAM_TOKEN   = "7713952607:AAH2eu_0X3zyA-7dFp-hG7N7p6kkk8ix9bI"
TELEGRAM_CHAT_ID = "7374570414"

# ───── Funciones de Base de Datos ─────
def get_db_connection():
    """Abre o crea cotizaciones.db y retorna conexión."""
    conn = sqlite3.connect('cotizaciones.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Crea la tabla cotizaciones si no existe."""
    conn = get_db_connection()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS cotizaciones (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      nombre TEXT NOT NULL,
      telefono TEXT NOT NULL,
      email TEXT NOT NULL,
      ancho TEXT NOT NULL,
      alto TEXT NOT NULL,
      colores TEXT NOT NULL,
      detalle TEXT NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

# ───── Ruta personalizada para servir archivos estáticos ─────
@app.route('/my_static/<path:filename>')
def my_static(filename):
    directory = os.path.join(app.root_path, 'static')
    return send_from_directory(directory, filename)

# ───── Plantillas en memoria (DictLoader) ─────
base_template = '''
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>{{ title }}</title>
  <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
  <style>
    body { background: #f0f8ff; }
    .navbar { background-color: #003366 !important; }
    .navbar-brand, .nav-link { color: #fff !important; }
    .jumbotron {
      background: linear-gradient(45deg, #ff6f61, #de3163);
      color: #fff;
    }
    button.btn-primary {
      background-color: #ff6f61;
      border: none;
    }
  </style>
</head>
<body>
  <nav class="navbar navbar-expand-lg navbar-light bg-light">
    <a class="navbar-brand" href="{{ url_for('home') }}">Bienvenido</a>
    <button class="navbar-toggler" type="button" data-toggle="collapse" data-target="#navbarNavDropdown">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse justify-content-end" id="navbarNavDropdown">
      <ul class="navbar-nav">
        <li class="nav-item"><a class="nav-link" href="{{ url_for('cotizar') }}">Cotizar</a></li>
        <li class="nav-item"><a class="nav-link" href="{{ url_for('login') }}">Administrador</a></li>
      </ul>
    </div>
  </nav>
  <div class="container mt-4">
    {% block content %}{% endblock %}
  </div>
  <script src="https://code.jquery.com/jquery-3.5.1.slim.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@4.5.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''

home_template = '''
{% extends "base_template.html" %}
{% block content %}
  <div class="jumbotron text-center">
    <h1 class="display-4">Bienvenido a Nuestro Sitio</h1>
    <p class="lead">Diseños creativos y cotización de banners en un clic.</p>
  </div>
  
  <div id="carouselWelcome" class="carousel slide" data-ride="carousel">
    <ol class="carousel-indicators">
      {% for i in range(images|length) %}
        <li data-target="#carouselWelcome" data-slide-to="{{ i }}" {% if i == 0 %}class="active"{% endif %}></li>
      {% endfor %}
    </ol>
    <div class="carousel-inner">
      {% for img in images %}
        <div class="carousel-item {% if loop.index0 == 0 %}active{% endif %}">
          <img src="{{ img }}" class="d-block w-100" style="height:400px; object-fit:cover;" alt="Imagen del carrusel">
        </div>
      {% endfor %}
    </div>
    <a class="carousel-control-prev" href="#carouselWelcome" role="button" data-slide="prev">
      <span class="carousel-control-prev-icon" aria-hidden="true"></span>
      <span class="sr-only">Anterior</span>
    </a>
    <a class="carousel-control-next" href="#carouselWelcome" role="button" data-slide="next">
      <span class="carousel-control-next-icon" aria-hidden="true"></span>
      <span class="sr-only">Siguiente</span>
    </a>
  </div>
{% endblock %}
'''

cotizar_template = '''
{% extends "base_template.html" %}
{% block content %}
  <h2>Cotiza tu Banner</h2>
  <form method="post">
    <div class="form-group">
      <label>Nombre</label>
      <input name="nombre" class="form-control" required>
    </div>
    <div class="form-group">
      <label>Teléfono</label>
      <input name="telefono" class="form-control" placeholder="+521234567890" required>
    </div>
    <div class="form-group">
      <label>Email</label>
      <input type="email" name="email" class="form-control" required>
    </div>
    <div class="form-group">
      <label>Ancho (m)</label>
      <input type="number" step="0.01" name="ancho" class="form-control" placeholder="1.50" required>
    </div>
    <div class="form-group">
      <label>Alto (m)</label>
      <input type="number" step="0.01" name="alto" class="form-control" placeholder="0.75" required>
    </div>
    <div class="form-group">
      <label>Paleta de Colores</label>
      <select name="colores" class="form-control" required>
        <option value="">--Selecciona--</option>
        <option value="vibrantes">Vibrantes</option>
        <option value="pastel">Pastel</option>
        <option value="neon">Neón</option>
        <option value="personalizado">Personalizado</option>
      </select>
    </div>
    <div class="form-group">
      <label>Detalles Adicionales</label>
      <textarea name="detalle" class="form-control" rows="3" placeholder="Ideas, inspiraciones..." required></textarea>
    </div>
    <button class="btn btn-primary">Enviar Cotización</button>
  </form>
{% endblock %}
'''

login_template = '''
{% extends "base_template.html" %}
{% block content %}
  <h2>Login Administrador</h2>
  <form method="post">
    <div class="form-group">
      <label>Usuario</label>
      <input name="username" class="form-control" required>
    </div>
    <div class="form-group">
      <label>Contraseña</label>
      <input type="password" name="password" class="form-control" required>
    </div>
    <button class="btn btn-primary">Ingresar</button>
  </form>
{% endblock %}
'''

admin_template = '''
{% extends "base_template.html" %}
{% block content %}
  <h2>Panel de Administrador</h2>
  <a href="{{ url_for('logout') }}" class="btn btn-danger mb-3">Cerrar Sesión</a>
  {% if quotes %}
    <table class="table table-striped">
      <thead>
        <tr>
          <th>#</th>
          <th>Nombre</th>
          <th>Teléfono</th>
          <th>Email</th>
          <th>Ancho(m)</th>
          <th>Alto(m)</th>
          <th>Colores</th>
          <th>Detalles</th>
        </tr>
      </thead>
      <tbody>
        {% for q in quotes %}
          <tr>
            <td>{{ loop.index }}</td>
            <td>{{ q.nombre }}</td>
            <td>{{ q.telefono }}</td>
            <td>{{ q.email }}</td>
            <td>{{ q.ancho }}</td>
            <td>{{ q.alto }}</td>
            <td>{{ q.colores }}</td>
            <td>{{ q.detalle }}</td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  {% else %}
    <p>No hay cotizaciones aún.</p>
  {% endif %}
{% endblock %}
'''

error_404_template = '''
{% extends "base_template.html" %}
{% block content %}
  <div class="text-center">
    <h1>404 - Página No Encontrada</h1>
    <p>La página que buscas no pudo ser encontrada.</p>
    <a href="{{ url_for('home') }}" class="btn btn-primary">Volver al inicio</a>
  </div>
{% endblock %}
'''

# Carga de plantillas en memoria
templates = {
  "base_template.html":   base_template,
  "home_template.html":   home_template,
  "cotizar_template.html": cotizar_template,
  "login_template.html":  login_template,
  "admin_template.html":  admin_template,
  "404_template.html":    error_404_template
}
app.jinja_loader = DictLoader(templates)

# ───── Rutas ─────

@app.route('/')
def home():
    # Usaremos nuestra ruta personalizada para servir las imágenes
    images = [
        url_for('my_static', filename='imagen1.jpg'),
        url_for('my_static', filename='imagen2.jpg'),
        url_for('my_static', filename='imagen3.jpg')
    ]
    return render_template("home_template.html", title="Bienvenido", images=images)

@app.route('/cotizar', methods=['GET','POST'])
def cotizar():
    if request.method == 'POST':
        data = { k: request.form[k] for k in ('nombre','telefono','email','ancho','alto','colores','detalle') }
        conn = get_db_connection()
        conn.execute("""
          INSERT INTO cotizaciones (nombre, telefono, email, ancho, alto, colores, detalle)
          VALUES (?, ?, ?, ?, ?, ?, ?)
        """, tuple(data.values()))
        conn.commit()
        conn.close()
        msg = (
          f"Nuevo Banner:\n"
          f"Nombre: {data['nombre']}\n"
          f"Tel: {data['telefono']}\n"
          f"Email: {data['email']}\n"
          f"Dimensiones: {data['ancho']}x{data['alto']}m\n"
          f"Paleta: {data['colores']}\n"
          f"Detalles: {data['detalle']}"
        )
        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.get(telegram_url, params={"chat_id": TELEGRAM_CHAT_ID, "text": msg})
        return redirect(url_for('home'))
    return render_template("cotizar_template.html", title="Cotizar")

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'admin123':
            session['logged_in'] = True
            return redirect(url_for('admin'))
        return "Credenciales incorrectas", 401
    return render_template("login_template.html", title="Login")

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('home'))

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM cotizaciones ORDER BY id DESC").fetchall()
    conn.close()
    quotes = [dict(r) for r in rows]
    return render_template("admin_template.html", title="Administrador", quotes=quotes)

@app.errorhandler(404)
def page_not_found(error):
    return render_template("404_template.html", title="404 Not Found"), 404

# ───── Inicio del servidor ─────
if __name__ == '__main__':
    with app.app_context():
        init_db()
    # Nota: En PythonAnywhere, no ejecutes "python app.py" manualmente.
    # Usa el sistema WSGI y recarga la Web App desde la pestaña Web.
    serve(app, host="0.0.0.0", port=5000)