from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient, ReturnDocument
from werkzeug.utils import secure_filename
import os
import urllib.parse

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "nestle_bi_fixed_2026")

# --- CONEXIÓN MONGODB ---
MONGO_URI = os.environ.get(
    "MONGO_URI",
    "mongodb+srv://ANDRES_VANEGAS:CF32fUhOhrj70dY5@cluster0.dtureen.mongodb.net/?appName=Cluster0"
)
client = MongoClient(MONGO_URI)
db = client['NestleDB']

solicitudes_col = db['solicitudes']
counters_col = db['counters']

# Configuración de carpeta para guardar imágenes en static/imagenes
UPLOAD_FOLDER = os.path.join('static', 'imagenes')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def obtener_siguiente_consecutivo():
    """Genera un consecutivo secuencial único en MongoDB sin duplicados."""
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
    try:
        # 1. Obtener el consecutivo único
        consecutivo = obtener_siguiente_consecutivo()

        # 2. Guardar la foto en la carpeta static/imagenes
        foto = request.files.get('placa')
        url_foto = "No adjuntada"
        filename_guardado = None

        if foto and foto.filename != '':
            ext = os.path.splitext(foto.filename)[1]
            filename_guardado = secure_filename(f"placa_solicitud_{consecutivo}{ext}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename_guardado)

            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            foto.save(filepath)

            base_url = request.host_url.rstrip('/')
            url_foto = f"{base_url}/static/imagenes/{filename_guardado}"

        # 3. Leer campos enviados desde el formulario
        bmb = request.form.get('bmb', '')
        poc = request.form.get('poc', '')
        funcionario = request.form.get('funcionario', '')
        motivo = request.form.get('motivo', '')
        departamento = request.form.get('departamento', '')
        ciudad = request.form.get('ciudad', '')
        lat = request.form.get('lat', '')
        lon = request.form.get('lon', '')

        # 4. Registrar en MongoDB
        documento = {
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
        solicitudes_col.insert_one(documento)

        # 5. Formatear texto sin codificar
        texto_raw = (
            f"*SOLICITUD #{consecutivo}*\n"
            f"*Funcionario:* {funcionario}\n"
            f"*BMB:* {bmb}\n"
            f"*POC (Base TA):* {poc}\n"
            f"*Motivo:* {motivo}\n"
            f"*Departamento:* {departamento}\n"
            f"*Ciudad:* {ciudad}\n"
            f"*Coordenadas:* {lat}, {lon}\n"
            f"*Ubicación Maps:* https://maps.google.com/?q={lat},{lon}\n"
            f"*Foto Placa:* {url_foto}"
        )

        # Codificar texto para evitar problemas con '#', espacios y saltos de línea
        mensaje_codificado = urllib.parse.quote(texto_raw)

        numero_telefono = "573132691744"
        url_whatsapp = f"https://wa.me/{numero_telefono}?text={mensaje_codificado}"

        return jsonify({"success": True, "whatsapp_url": url_whatsapp})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
