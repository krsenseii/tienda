import requests
import google.generativeai as genai
from datetime import datetime, timedelta
import os
import random
import unicodedata
from dotenv import load_dotenv

load_dotenv()

# ================= CONFIGURACIÓN =================
CARPETA_BASE = os.path.dirname(os.path.abspath(__file__))
CARPETA_FOTOS = os.path.join(CARPETA_BASE, 'fotos')

# CLAVES API (GEMINI + FOOTBALL)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")

# --- CONFIGURACIÓN DEL BOT DE CONTENIDO ---
# Pega aquí el token de tu NUEVO bot (o el antiguo si usas el mismo)
TELEGRAM_CONTENT_TOKEN = os.getenv("TELEGRAM_CONTENT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# CÓDIGOS DE COMPETICIONES
COMPS_5_LIGAS = ['PL', 'SA', 'BL1', 'FL1'] 
COMP_LIGA = ['PD'] 
COMPS_EUROPA = ['CL', 'EL', 'EC', 'CDR'] 

# ================= FUNCIONES AUXILIARES =================

def buscar_fotos_en_carpeta(subcarpeta, cantidad=1):
    """Busca fotos reales y devuelve SUS RUTAS COMPLETAS."""
    ruta_busqueda = os.path.join(CARPETA_FOTOS, subcarpeta)
    
    # Búsqueda inteligente de carpeta (por si mayúsculas/minúsculas)
    if not os.path.exists(ruta_busqueda) and os.path.exists(CARPETA_FOTOS):
        for d in os.listdir(CARPETA_FOTOS):
            if subcarpeta.lower() in d.lower():
                ruta_busqueda = os.path.join(CARPETA_FOTOS, d)
                break
    
    if os.path.exists(ruta_busqueda):
        archivos = [f for f in os.listdir(ruta_busqueda) if f.lower().endswith(('.jpg', '.png', '.webp'))]
        if archivos:
            seleccion = random.sample(archivos, min(len(archivos), cantidad))
            # CAMBIO IMPORTANTE: Devolvemos la ruta completa (path)
            return [os.path.join(ruta_busqueda, f) for f in seleccion]
    return []

def consultar_api_partidos(date_from, date_to, competitions=None):
    print(f"⏳ Conectando a API Fútbol ({date_from} al {date_to})...") # DEBUG
    url = "https://api.football-data.org/v4/matches"
    headers = {'X-Auth-Token': FOOTBALL_API_KEY}
    params = {'dateFrom': date_from, 'dateTo': date_to}
    if competitions:
        params['competitions'] = ",".join(competitions)

    try:
        # AÑADIDO timeout=10 para que no se congele
        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"✅ Respuesta API recibida: Código {response.status_code}") # DEBUG
        data = response.json()
        return data.get('matches', [])
    except requests.exceptions.Timeout:
        print("❌ Error: La API tardó demasiado en responder (Timeout).")
        return []
    except Exception as e:
        print(f"⚠️ Error conectando con API Fútbol: {e}")
        return []

def generar_texto_gemini(prompt):
    instruccion_extra = """
    \n--- INSTRUCCIÓN FINAL ---
    Al final, añade un apartado: "🎨 PROMPT PARA IMAGEN:" con una descripción detallada en INGLÉS para generar la imagen.
    """
    
    print("🧠 Gemini está pensando... (Esto puede tardar 5-10 seg)") # CHIVATO 1
    
    try:
        # Añadimos una configuración de seguridad básica para evitar bloqueos tontos
        resultado = model.generate_content(
            prompt + instruccion_extra,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7 # Creatividad controlada
            )
        )
        print("✅ ¡Gemini ha respondido!") # CHIVATO 2
        return resultado.text
    except Exception as e:
        print(f"❌ Error en Gemini: {e}")
        return f"Error generando texto con IA: {e}"
    
def enviar_a_telegram(titulo, texto, archivos_reales=None):
    """Envía Texto + FOTOS REALES (Adjuntas) a Telegram."""
    print(f"🚀 Enviando a Telegram: {titulo}...")
    
    # 1. ENVIAR EL TEXTO
    mensaje_final = f"📝 **NUEVO POST: {titulo}**\n\n{texto}"
    if archivos_reales:
        # Solo ponemos los nombres en el texto para referencia
        nombres = [os.path.basename(f) for f in archivos_reales]
        mensaje_final += f"\n\n📸 **FOTOS ADJUNTAS:** {', '.join(nombres)}"

    url_msg = f"https://api.telegram.org/bot{TELEGRAM_CONTENT_TOKEN}/sendMessage"
    try:
        requests.post(url_msg, data={"chat_id": TELEGRAM_CHAT_ID, "text": mensaje_final})
        print("✅ Texto enviado.")
    except Exception as e:
        print(f"❌ Error enviando texto: {e}")

    # 2. ENVIAR LAS FOTOS (Si las hay)
    if archivos_reales:
        print("📸 Subiendo fotos a Telegram...")
        url_photo = f"https://api.telegram.org/bot{TELEGRAM_CONTENT_TOKEN}/sendPhoto"
        
        for ruta_foto in archivos_reales:
            try:
                if os.path.exists(ruta_foto):
                    with open(ruta_foto, "rb") as f:
                        requests.post(
                            url_photo, 
                            data={"chat_id": TELEGRAM_CHAT_ID}, 
                            files={"photo": f}
                        )
            except Exception as e:
                print(f"❌ Error subiendo foto {ruta_foto}: {e}")
        print("✅ Fotos enviadas.")

def guardar_post(titulo, texto, archivos_reales=None):
    filename = f"post_{datetime.now().strftime('%A')}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"--- {titulo} ---\n\n")
        if archivos_reales:
            nombres = [os.path.basename(f) for f in archivos_reales]
            f.write(f"📸 FOTOS: {', '.join(nombres)}\n\n")
        f.write(texto)
    print(f"📁 Backup guardado en '{filename}'")

# ================= ESTRATEGIAS =================

def estrategia_lunes_resumen():
    hoy = datetime.now()
    inicio = (hoy - timedelta(days=3)).strftime('%Y-%m-%d')
    fin = hoy.strftime('%Y-%m-%d')
    matches = consultar_api_partidos(inicio, fin, COMP_LIGA)
    terminados = [m for m in matches if m['status'] == 'FINISHED']
    
    if not terminados: return estrategia_comodin()
    
    destacados = terminados[:4]
    resumen_txt = "\n".join([f"- {m['homeTeam']['name']} {m['score']['fullTime']['home']}-{m['score']['fullTime']['away']} {m['awayTeam']['name']}" for m in destacados])
    prompt = f"Actúa como CM. Lunes. Resumen jornada LaLiga: {resumen_txt}. Genera debate."
    return generar_texto_gemini(prompt), None

def estrategia_martes_miercoles():
    dia = "Martes" if datetime.now().weekday() == 1 else "Miércoles"
    hoy = datetime.now().strftime('%Y-%m-%d')
    matches = consultar_api_partidos(hoy, hoy, COMPS_EUROPA)
    
    if not matches:
        all_matches = consultar_api_partidos(hoy, hoy, []) 
        matches = [m for m in all_matches if "Cup" in m['competition']['name'] or "Copa" in m['competition']['name']]

    if matches:
        cdr = [m for m in matches if m['competition']['code'] == 'CDR']
        if cdr: matches = cdr
        lista = "\n".join([f"{m['homeTeam']['name']} vs {m['awayTeam']['name']}" for m in matches[:3]])
        prompt = f"Actúa como CM. Hoy es {dia}. Partidazos: {lista}. Hype máximo."
        return generar_texto_gemini(prompt), None
    return estrategia_comodin()

def estrategia_jueves_otros():
    tema = random.choice(['NBA', 'Motor']) 
    carpeta = "NBA_Todo" if tema == 'NBA' else "Motor_Polos"
    rutas_archivos = buscar_fotos_en_carpeta(carpeta, 1) # Devuelve rutas completas
    
    if rutas_archivos:
        # Sacamos el nombre limpio del archivo para el prompt
        archivo_nombre = os.path.basename(rutas_archivos[0])
        nombre_limpio = os.path.splitext(archivo_nombre)[0].replace('_', ' ').title()
        try:
            prompt = f"CM FullFutbol. Vende este producto: {nombre_limpio} ({tema}). Estilo urbano. SIN prompt de imagen."
            texto = model.generate_content(prompt).text
            return texto, rutas_archivos
        except: return "Error IA", rutas_archivos
    return estrategia_comodin()

def estrategia_viernes_previa():
    hoy = datetime.now(); fin = (hoy + timedelta(days=3)).strftime('%Y-%m-%d')
    matches = consultar_api_partidos(hoy.strftime('%Y-%m-%d'), fin, COMP_LIGA)
    if matches:
        lista = "\n".join([f"- {m['homeTeam']['name']} vs {m['awayTeam']['name']}" for m in matches[:3]])
        return generar_texto_gemini(f"CM. Viernes previa. Partidos: {lista}. ¿Camiseta lista?"), None
    return estrategia_comodin()

def estrategia_sabado_internacional():
    hoy = datetime.now().strftime('%Y-%m-%d')
    matches = consultar_api_partidos(hoy, hoy, COMPS_5_LIGAS)
    if matches:
        lista = "\n".join([f"- {m['homeTeam']['name']} vs {m['awayTeam']['name']}" for m in matches[:4]])
        return generar_texto_gemini(f"CM. Sábado internacional. Partidos: {lista}. Camisetas de fuera."), None
    return estrategia_comodin()

def estrategia_domingo_retro():
    rutas_archivos = buscar_fotos_en_carpeta("Retro_Camisetas", 2)
    if rutas_archivos:
        nombres = ", ".join([os.path.splitext(os.path.basename(f))[0].replace('_', ' ').title() for f in rutas_archivos])
        try:
            prompt = f"CM FullFutbol. Domingo Retro. Joyas: {nombres}. Nostalgia. SIN prompt de imagen."
            texto = model.generate_content(prompt).text
            return texto, rutas_archivos
        except: return "Error IA", rutas_archivos
    return estrategia_comodin()

def estrategia_comodin():
    temas = ["Tarjetas roja/amarilla", "Balón blanco y negro", "Partido 149-0", "Perro Pickles", "Porteros diferente color", "Origen VAR", "Tacos botas", "Estadio más grande", "Gol más rápido", "11 contra 11", "90 minutos", "Soccer vs Football", "Guerra Fútbol", "Luis Monti 2 países", "Hat-trick", "Barbados vs Granada", "Tregua Navidad", "Brasil amarillo", "Liga Sorlingas", "Cesión portero", "Lucien Laurent gol", "Dorsales", "Copa caja zapatos", "Héctor Castro manco", "Tanda penaltis", "Árbitros negro", "Gerardo Bedoya rojas", "Gol de Oro", "Silbato", "Espinilleras"]
    tema = random.choice(temas)
    return generar_texto_gemini(f"CM. Curiosidad fútbol: {tema}. Breve y viral. ¿Sabías esto?"), None

# ================= MAIN =================

def planificador_semanal():
    dia = datetime.now().weekday()
    if dia == 0: return "Resumen Semanal", estrategia_lunes_resumen()
    elif dia == 1: return "Martes Europeo", estrategia_martes_miercoles()
    elif dia == 2: return "Miércoles Europeo", estrategia_martes_miercoles()
    elif dia == 3: return "Jueves Otros", estrategia_jueves_otros()
    elif dia == 4: return "Viernes Previa", estrategia_viernes_previa()
    elif dia == 5: return "Sábado Internacional", estrategia_sabado_internacional()
    elif dia == 6: return "Domingo Retro", estrategia_domingo_retro()

if __name__ == "__main__":
    print("--- 🤖 FULLFUTBOL AUTO-BOT V6 (Con Envío de Fotos) 🤖 ---")
    
    titulo, resultado = planificador_semanal()
    texto, rutas_archivos = resultado
    
    guardar_post(titulo, texto, rutas_archivos)
    enviar_a_telegram(titulo, texto, rutas_archivos)