from flask import Flask, render_template, request, jsonify, url_for
from pymongo import MongoClient, ReturnDocument
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "llave_secreta_desarrollo")

# --- CONEXIÓN MONGODB ---
# Se recomienda configurar MONGO_URI en las variables de entorno de Render
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://<usuario>:<password>@cluster0.dtureen.mongodb.net/?appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client['NestleDB']

# Colecciones
solicitudes_col = db['solicitudes']
counters_col = db['counters']

# Configuración de carpeta para guardar imágenes localmente
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def obtener_siguiente_consecutivo():
    """Genera un número consecutivo secuencial único en MongoDB sin duplicados."""
    resultado = counters_col.find_one_and_update(
        {'_id': 'solicitud_id'},
        {'$inc': {'seq': 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    return resultado['seq']


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/submit', methods=['POST'])
def submit():
    # 1. Obtener el siguiente consecutivo atómico
    consecutivo = obtener_siguiente_consecutivo()

    # 2. Procesar y guardar la imagen
    foto = request.files.get('placa')
    url_foto = "No adjuntada"
    filename_guardado = None

    if foto and foto.filename != '':
        ext = os.path.splitext(foto.filename)[1]
        filename_guardado = secure_filename(f"placa_solicitud_{consecutivo}{ext}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename_guardado)
        foto.save(filepath)

        # Generar la URL pública completa de la imagen para que WhatsApp la previsualice
        url_foto = request.host_url.rstrip('/') + url_for('static', filename=f'uploads/{filename_guardado}')

    # 3. Datos del formulario
    bmb = request.form.get('bmb')
    poc = request.form.get('poc')
    funcionario = request.form.get('funcionario')
    motivo = request.form.get('motivo')  # "Actualización" o "Creación de POC"
    departamento = request.form.get('departamento')
    ciudad = request.form.get('ciudad')
    lat = request.form.get('lat')
    lon = request.form.get('lon')

    # 4. Guardar registro completo en MongoDB
    documento_solicitud = {
        "consecutivo": consecutivo,
        "funcionario": funcionario,
        "bmb": bmb,
        "poc": poc,
        "motivo": motivo,
        "departamento": departamento,
        "ciudad": ciudad,
        "coordenadas": {"lat": lat, "lon": lon},
        "foto_url": url_foto,
        "foto_filename": filename_guardado
    }
    solicitudes_col.insert_one(documento_solicitud)

    # 5. Construir mensaje formateado para WhatsApp
    mensaje = (
        f"*SOLICITUD #{consecutivo}*%0A"
        f"*Funcionario:* {funcionario}%0A"
        f"*BMB:* {bmb}%0A"
        f"*POC (Base TA):* {poc}%0A"
        f"*Motivo:* {motivo}%0A"
        f"*Departamento:* {departamento}%0A"
        f"*Ciudad:* {ciudad}%0A"
        f"*Coordenadas:* {lat}, {lon}%0A"
        f"*Ubicación Maps:* https://maps.google.com/?q={lat},{lon}%0A"
        f"*Foto Placa:* {url_foto}"
    )

    numero_telefono = "573132691744"
    url_whatsapp = f"https://wa.me/{numero_telefono}?text={mensaje}"

    return jsonify({"success": True, "whatsapp_url": url_whatsapp, "consecutivo": consecutivo})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
