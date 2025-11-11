"""
HydroAssist Chatbot Server
Servidor simple para el chatbot sin dependencias completas de Rasa
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
sys.path.append(os.path.dirname(__file__))

from actions import simulate_rasa_response

app = Flask(__name__)
CORS(app)  # Permitir peticiones desde Django backend

# ============================================================================
# NUEVO ENDPOINT PRINCIPAL PARA DJANGO
# ============================================================================

@app.route('/chat', methods=['POST'])
def chat_endpoint():
    """
    Endpoint principal para recibir mensajes de Django Backend
    
    Formato de entrada (desde Django):
    {
        "message": "Necesito un refugio",
        "user_location": {"lat": -34.6037, "lng": -58.3816},
        "nearby_shelters": [...],
        "risk_zones": [...],
        "emergency_level": "normal"
    }
    
    Formato de salida (para Django):
    {
        "message": "Encontré 3 refugios cercanos...",
        "intent": "find_shelter", 
        "confidence": 0.95,
        "response": "Encontré 3 refugios cercanos..."  # para compatibilidad
    }
    """
    try:
        data = request.json
        if not data:
            return jsonify({
                "error": "No data provided"
            }), 400
            
        message = data.get('message', '')
        user_location = data.get('user_location')
        nearby_shelters = data.get('nearby_shelters', [])
        risk_zones = data.get('risk_zones', [])
        emergency_level = data.get('emergency_level', 'normal')
        
        if not message:
            return jsonify({
                "error": "Message is required"
            }), 400
        
        # Procesar con contexto enriquecido de Django
        response = process_chat_with_context(
            message=message,
            user_location=user_location,
            nearby_shelters=nearby_shelters,
            risk_zones=risk_zones,
            emergency_level=emergency_level
        )
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({
            "message": "Lo siento, ocurrió un error procesando tu mensaje.",
            "intent": "error",
            "confidence": 1.0,
            "error": str(e)
        }), 500


def process_chat_with_context(message, user_location=None, nearby_shelters=None, 
                             risk_zones=None, emergency_level='normal'):
    """
    Procesa el mensaje del chat con contexto enriquecido de Django
    """
    message_lower = message.lower()
    
    # Análisis de intención
    intent = "general"
    confidence = 0.8
    
    # Detección de intenciones
    if any(word in message_lower for word in ["refugio", "albergue", "shelter"]):
        intent = "find_shelter"
        confidence = 0.95
    elif any(word in message_lower for word in ["emergencia", "reportar", "ayuda urgente"]):
        intent = "report_emergency"
        confidence = 0.9
    elif any(word in message_lower for word in ["riesgo", "peligro", "zona peligrosa"]):
        intent = "check_risk"
        confidence = 0.9
    elif any(word in message_lower for word in ["ubicación", "donde estoy", "mi ubicación"]):
        intent = "share_location"
        confidence = 0.9
    elif any(word in message_lower for word in ["hola", "buenos", "buenas", "hi"]):
        intent = "greet"
        confidence = 0.95
    elif any(word in message_lower for word in ["adiós", "chau", "gracias", "bye"]):
        intent = "goodbye"
        confidence = 0.95
    
    # Generar respuesta basada en intención y contexto
    response_text = generate_response_with_context(
        intent, message, user_location, nearby_shelters, risk_zones, emergency_level
    )
    
    return {
        "message": response_text,
        "response": response_text,  # Para compatibilidad con frontend
        "intent": intent,
        "confidence": confidence
    }


def generate_response_with_context(intent, original_message, user_location, 
                                 nearby_shelters, risk_zones, emergency_level):
    """
    Genera respuestas contextuales basadas en datos de Django
    """
    
    if intent == "find_shelter":
        if nearby_shelters and len(nearby_shelters) > 0:
            shelter_count = len(nearby_shelters)
            if shelter_count == 1:
                shelter = nearby_shelters[0]
                return f"Encontré 1 refugio disponible: {shelter['name']} a {shelter['distance']} km de tu ubicación. Tiene capacidad para {shelter['capacity']} personas y actualmente tiene {shelter['available_capacity']} lugares disponibles."
            else:
                closest = min(nearby_shelters, key=lambda x: x['distance'])
                return f"Encontré {shelter_count} refugios cercanos. El más cercano es {closest['name']} a {closest['distance']} km. Te he marcado todos los refugios disponibles en el mapa."
        else:
            return "No encontré refugios en tu área inmediata. Te recomiendo contactar a las autoridades locales o buscar en un radio más amplio. ¿Puedes compartir tu ubicación exacta?"
    
    elif intent == "report_emergency":
        if emergency_level == "high":
            return "He registrado tu reporte de emergencia con ALTA PRIORIDAD debido a la actividad reciente en tu zona. Las autoridades han sido notificadas inmediatamente. Mantente en un lugar seguro y sigue las instrucciones oficiales."
        else:
            return "He registrado tu reporte de emergencia. Las autoridades competentes han sido notificadas y recibirás seguimiento. Mientras tanto, si la situación empeora, no dudes en contactar servicios de emergencia (911)."
    
    elif intent == "check_risk":
        if risk_zones and len(risk_zones) > 0:
            high_risk = [z for z in risk_zones if z.get('risk_level') == 'high']
            if high_risk:
                return f"⚠️ ATENCIÓN: Detecté {len(high_risk)} zona(s) de ALTO RIESGO en tu área. Te recomiendo evitar estas zonas y considerar refugios alternativos. ¿Necesitas que te ayude a encontrar una ruta segura?"
            else:
                return f"Tu zona presenta riesgo moderado. Mantente alerta a las condiciones meteorológicas y ten un plan de evacuación preparado. Hay {len(risk_zones)} zona(s) de riesgo identificadas en el área."
        else:
            return "No detecto zonas de riesgo inmediato en tu ubicación actual. Sin embargo, las condiciones pueden cambiar rápidamente. Mantente informado a través de canales oficiales."
    
    elif intent == "share_location":
        if user_location:
            return f"He recibido tu ubicación: {user_location['lat']:.4f}, {user_location['lng']:.4f}. Con esta información puedo ayudarte mejor a encontrar refugios cercanos y evaluar riesgos en tu zona. ¿En qué más puedo asistirte?"
        else:
            return "Para darte la mejor asistencia, necesito tu ubicación. ¿Puedes compartirla usando el botón 'Compartir Ubicación' en el mapa?"
    
    elif intent == "greet":
        location_msg = f" en tu ubicación actual" if user_location else ""
        return f"¡Hola! Soy Hydro, tu asistente para emergencias hídricas. Estoy aquí para ayudarte a encontrar refugios, evaluar riesgos y reportar emergencias{location_msg}. ¿En qué puedo asistirte hoy?"
    
    elif intent == "goodbye":
        return "Gracias por usar HydroAssist. Recuerda que estoy disponible 24/7 para cualquier emergencia hídrica. ¡Mantente seguro y no dudes en volver si necesitas ayuda!"
    
    else:  # intent == "general"
        return "Entiendo tu consulta. Puedo ayudarte con: 🏠 Encontrar refugios cercanos, ⚠️ Evaluar riesgos en tu zona, 🚨 Reportar emergencias, 📍 Analizar tu ubicación. ¿Con cuál te gustaría empezar?"


# ============================================================================
# ENDPOINTS HEREDADOS (Para compatibilidad y testing)
# ============================================================================

@app.route('/webhooks/rest/webhook', methods=['POST'])
def webhook():
    """Endpoint principal para recibir mensajes del frontend"""
    try:
        data = request.json
        message = data.get('message', '')
        sender = data.get('sender', 'user')
        
        # Simular respuesta del chatbot
        response = simulate_rasa_response(message, sender)
        
        return jsonify([response])
    
    except Exception as e:
        return jsonify([{
            "recipient_id": "user",
            "text": "Lo siento, ocurrió un error procesando tu mensaje. Por favor intenta nuevamente."
        }]), 500

@app.route('/model/parse', methods=['POST'])
def parse():
    """Endpoint para analizar intenciones (para testing)"""
    try:
        data = request.json
        text = data.get('text', '')
        
        # Análisis básico de intenciones
        intent = "greet"
        confidence = 0.8
        
        text_lower = text.lower()
        if "riesgo" in text_lower or "peligro" in text_lower:
            intent = "consultar_riesgo"
        elif "refugio" in text_lower:
            intent = "buscar_refugio"
        elif "emergencia" in text_lower or "reportar" in text_lower:
            intent = "reportar_emergencia"
        elif "hola" in text_lower or "buenos" in text_lower:
            intent = "greet"
        elif "adiós" in text_lower or "chau" in text_lower:
            intent = "goodbye"
        
        return jsonify({
            "intent": {
                "name": intent,
                "confidence": confidence
            },
            "entities": [],
            "text": text
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "message": "HydroAssist Chatbot is running"})

@app.route('/', methods=['GET'])
def root():
    """Información básica del servidor"""
    return jsonify({
        "name": "HydroAssist Chatbot Server",
        "version": "2.0.0",
        "description": "Servidor de chatbot para gestión de emergencias hídricas",
        "architecture": "Django Backend → Flask Chatbot",
        "main_endpoint": "/chat",
        "endpoints": {
            "chat": "/chat (PRINCIPAL - recibe de Django)",
            "webhook": "/webhooks/rest/webhook (Legacy)",
            "parse": "/model/parse (Testing)",
            "health": "/health"
        },
        "communication_flow": [
            "1. Frontend React → Django Backend",
            "2. Django Backend → Flask Chatbot (/chat)",
            "3. Flask Chatbot → Django Backend",
            "4. Django Backend → Frontend React"
        ]
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # Cambiado de 5005 a 5000
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    print(f"🤖 Iniciando HydroAssist Chatbot Server en puerto {port}")
    print("🏗️ NUEVA ARQUITECTURA: Django Backend → Flask Chatbot")
    print("")
    print("💬 Endpoints disponibles:")
    print("   🎯 POST /chat - PRINCIPAL: Recibe mensajes de Django")
    print("   📡 POST /webhooks/rest/webhook - Legacy: Mensajes directos")
    print("   🧠 POST /model/parse - Testing: Analizar intenciones")
    print("   ❤️  GET /health - Health check")
    print("")
    print("🔗 Comunicación:")
    print(f"   Django Backend → http://localhost:{port}/chat")
    print(f"   Frontend → Django → Flask (esta instancia)")
    
    app.run(host='0.0.0.0', port=port, debug=debug)