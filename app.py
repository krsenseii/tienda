import os
import random
from flask import Flask, render_template, send_from_directory, request, jsonify
import requests
from functools import lru_cache
import time
from dotenv import load_dotenv
load_dotenv()
app = Flask(__name__, template_folder='templates', static_folder='fotos', static_url_path='/fotos')

# ================= CONFIGURACIÓN =================
CARPETA_BASE = os.path.dirname(os.path.abspath(__file__))
CARPETA_FOTOS = os.path.join(CARPETA_BASE, 'fotos')

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
# =================================================
# Decorador para que la caché expire cada X segundos
def tiempo_cache(segundos):
    def decorador(func):
        @lru_cache(maxsize=1)
        def wrapper_con_tiempo(*args, **kwargs):
            return func(*args, **kwargs)
        
        def wrapper(*args, **kwargs):
            tiempo_actual = time.time()
            if tiempo_actual - wrapper.ultimo_calculo > segundos:
                wrapper_con_tiempo.cache_clear()
                wrapper.ultimo_calculo = tiempo_actual
            return wrapper_con_tiempo(*args, **kwargs)
        
        wrapper.ultimo_calculo = 0
        return wrapper
    return decorador
@tiempo_cache(600)
def escanear_carpetas():
    productos = []
    categorias = set()
    ext_validas = ('.jpg', '.jpeg', '.png', '.webp')

    if not os.path.exists(CARPETA_FOTOS):
        print(f"⚠️ Alerta: No encuentro la carpeta {CARPETA_FOTOS}")
        return [], []

    try:
        nombres_carpetas = [d for d in os.listdir(CARPETA_FOTOS) if os.path.isdir(os.path.join(CARPETA_FOTOS, d))]
        
        for carpeta in nombres_carpetas:
            if carpeta.startswith('.') or carpeta in {'__pycache__', 'static'}: continue
            
            ruta_absoluta_carpeta = os.path.join(CARPETA_FOTOS, carpeta)
            
            # --- DETECTAR CATEGORÍA Y TIPO ---
            if "_" in carpeta:
                parts = carpeta.split("_", 1)
                categoria_nombre = parts[0]
                tipo = parts[1]
            else:
                categoria_nombre = carpeta
                tipo = "Otros"

            cat_lower = categoria_nombre.lower()
            tipo_lower = tipo.lower()
            carpeta_lower = carpeta.lower()

            es_personalizable = "camisetas" in tipo_lower or "kits" in tipo_lower or "retro" in tipo_lower
            
            # --- CORRECCIÓN DE EDADES ---
            
            # 1. Detectamos Mujer explícitamente
            es_mujer = "mujer" in carpeta_lower or "femenino" in carpeta_lower or "women" in carpeta_lower

            # 2. Bebé
            es_bebe = "bebe" in carpeta_lower or "baby" in carpeta_lower
            
            # 3. Niño: ES IMPORTANTE QUE NO SEA MUJER
            # Esto evita que "Femenino" active "nino"
            es_nino = False
            if not es_bebe and not es_mujer:
                if "niño" in carpeta_lower or "nino" in carpeta_lower or "kids" in carpeta_lower:
                    es_nino = True

            # Prioridad
            prioridad = 3 
            if "retro" in carpeta_lower: prioridad = 1
            elif "laliga" in carpeta_lower: prioridad = 1
            elif "selecciones" in carpeta_lower: prioridad = 1
            elif "premier" in carpeta_lower: prioridad = 1
            elif "chandal" in carpeta_lower: prioridad = 2

            archivos = os.listdir(ruta_absoluta_carpeta)
            for archivo in archivos:
                if archivo.lower().endswith(ext_validas):
                    ruta_web = f"{carpeta}/{archivo}"
                    
                    productos.append({
                        "nombre": os.path.splitext(archivo)[0].replace('_', ' ').title(),
                        "ruta_web": ruta_web,
                        "categoria": categoria_nombre,
                        "categoria_original": carpeta,
                        "tipo": tipo,
                        "personalizable": es_personalizable,
                        "es_nino": es_nino,
                        "es_bebe": es_bebe,
                        "es_mujer": es_mujer, # Pasamos este dato al HTML por si acaso
                        "prioridad": prioridad
                    })
                    categorias.add(categoria_nombre)

    except Exception as e:
        print(f"❌ Error escaneando: {e}")

    # Ordenamiento Aleatorio Inteligente
    grupo_top = [p for p in productos if p['prioridad'] == 1]
    grupo_medio = [p for p in productos if p['prioridad'] == 2]
    grupo_resto = [p for p in productos if p['prioridad'] == 3]

    random.shuffle(grupo_top)
    random.shuffle(grupo_medio)
    random.shuffle(grupo_resto)

    productos_ordenados = grupo_top + grupo_medio + grupo_resto
    
    return productos_ordenados, sorted(list(categorias))

# --- RUTAS WEB ---

@app.route('/')
def catalogo():
    productos, categorias = escanear_carpetas()
    return render_template('catalogo.html', productos=productos, categorias=categorias)

@app.route('/procesar_pedido', methods=['POST'])
def procesar_pedido():
    data = request.json
    contacto = data.get('contacto', 'Sin contacto')
    carrito = data.get('carrito', [])
    
    # --- NUEVO: Calcular el precio total sumando los precios del carrito ---
    total_pedido = sum(item.get('precio', 0) for item in carrito)
    
    print(f"📩 Pedido recibido de: {contacto} - Total: {total_pedido}€")

    try:
        # --- MODIFICADO: Añadimos el Total al mensaje principal ---
        mensaje_principal = f"🔔 NUEVO PEDIDO\n👤 Contacto: {contacto}\n💰 Total a cobrar: {total_pedido} €"
        
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      data={"chat_id": TELEGRAM_CHAT_ID, "text": mensaje_principal})

        for item in carrito:
            lines = []
            if item.get('talla') and item['talla'] != "SIN TALLA":
                lines.append(f"SIZE: {item['talla']}")
            if item.get('dorsal'):
                lines.append(f"NAME AND NUMBER: {item['dorsal']}")
            
            caption = "\n".join(lines)

            ruta_foto = os.path.join(CARPETA_FOTOS, item['ruta_web'].replace("/", os.sep))
            
            if os.path.exists(ruta_foto):
                with open(ruta_foto, "rb") as f:
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
                        data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption},
                        files={"photo": f}
                    )
            else:
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                              data={"chat_id": TELEGRAM_CHAT_ID, "text": f"⚠️ (Sin foto) {caption}"})

    except Exception as e:
        print(f"Error Telegram: {e}")
        return jsonify({"status": "error"}), 500

    return jsonify({"status": "ok"})
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)
