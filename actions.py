from typing import Any, Text, Dict, List
import requests
import json
import re

# Simulación de las clases de Rasa para desarrollo sin instalación completa
class Action:
    def name(self) -> Text:
        return "action_default"
    
    def run(self, dispatcher, tracker, domain) -> List[Dict[Text, Any]]:
        return []

class ActionExecutionRejection(Exception):
    pass

# Configuración de la API
DJANGO_API_URL = "http://localhost:8000/api"

# Funciones auxiliares
def extract_coordinates_from_text(text: str) -> Dict[str, float]:
    """Extrae coordenadas de un texto usando regex"""
    # Buscar patrones como: -34.6217, -58.3725 o lat: -34.6217 lon: -58.3725
    coord_pattern = r'(-?\d+\.?\d*)[,\s]+(-?\d+\.?\d*)'
    match = re.search(coord_pattern, text)
    
    if match:
        lat, lon = float(match.group(1)), float(match.group(2))
        # Validar rangos aproximados para Buenos Aires
        if -35 <= lat <= -34 and -59 <= lon <= -57:
            return {"lat": lat, "lon": lon}
    
    return {}

def extract_location_from_entities(entities: List[Dict]) -> Dict[str, Any]:
    """Extrae información de ubicación de las entidades detectadas"""
    location_data = {}
    
    for entity in entities:
        if entity["entity"] == "ubicacion":
            location_data["location_name"] = entity["value"]
        elif entity["entity"] == "latitud":
            try:
                location_data["lat"] = float(entity["value"])
            except ValueError:
                pass
        elif entity["entity"] == "longitud":
            try:
                location_data["lon"] = float(entity["value"])
            except ValueError:
                pass
        elif entity["entity"] == "direccion":
            location_data["address"] = entity["value"]
    
    return location_data


class ActionConsultarRiesgo(Action):
    """Acción para consultar el nivel de riesgo en una ubicación"""
    
    def name(self) -> Text:
        return "action_consultar_riesgo"
    
    def run(self, dispatcher, tracker, domain) -> List[Dict[Text, Any]]:
        try:
            # Obtener entidades de ubicación
            entities = tracker.latest_message.get('entities', [])
            location_data = extract_location_from_entities(entities)
            
            # Si no hay coordenadas directas, intentar extraer del texto
            if 'lat' not in location_data or 'lon' not in location_data:
                text = tracker.latest_message.get('text', '')
                coords = extract_coordinates_from_text(text)
                location_data.update(coords)
            
            # Coordenadas por defecto (centro de Buenos Aires) si no se proporciona ubicación
            lat = location_data.get('lat', -34.6118)
            lon = location_data.get('lon', -58.3960)
            
            # Llamar a la API de Django
            response = requests.get(
                f"{DJANGO_API_URL}/geo/risk/",
                params={"lat": lat, "lon": lon},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                risk_info = data.get('risk_assessment', {})
                level = risk_info.get('level', 'desconocido')
                description = risk_info.get('description', 'No se pudo evaluar el riesgo')
                
                message = f"📍 Evaluación de riesgo para tu ubicación:\n\n"
                message += f"🚨 Nivel: {level.upper()}\n"
                message += f"📝 {description}\n"
                
                if risk_info.get('recent_reports_count', 0) > 0:
                    message += f"\n⚠️ Hay {risk_info['recent_reports_count']} reportes recientes en el área"
                
                dispatcher.utter_message(text=message)
                
                # Sugerir refugios si el riesgo es alto
                if level in ['high', 'critical']:
                    dispatcher.utter_message(text="Dado el nivel de riesgo elevado, ¿te gustaría que busque refugios cercanos?")
            else:
                dispatcher.utter_message(text="Lo siento, no pude acceder a la información de riesgo en este momento. Intenta más tarde.")
                
        except requests.RequestException:
            dispatcher.utter_message(text="No pude conectarme al servidor. Por favor, verifica tu conexión e intenta nuevamente.")
        except Exception as e:
            dispatcher.utter_message(text="Ocurrió un error inesperado. Por favor, intenta nuevamente.")
        
        return []


class ActionBuscarRefugio(Action):
    """Acción para buscar refugios cercanos"""
    
    def name(self) -> Text:
        return "action_buscar_refugio"
    
    def run(self, dispatcher, tracker, domain) -> List[Dict[Text, Any]]:
        try:
            # Obtener entidades de ubicación
            entities = tracker.latest_message.get('entities', [])
            location_data = extract_location_from_entities(entities)
            
            # Si no hay coordenadas directas, intentar extraer del texto
            if 'lat' not in location_data or 'lon' not in location_data:
                text = tracker.latest_message.get('text', '')
                coords = extract_coordinates_from_text(text)
                location_data.update(coords)
            
            # Coordenadas por defecto (centro de Buenos Aires) si no se proporciona ubicación
            lat = location_data.get('lat', -34.6118)
            lon = location_data.get('lon', -58.3960)
            
            # Llamar a la API de Django
            response = requests.get(
                f"{DJANGO_API_URL}/geo/nearby/",
                params={"lat": lat, "lon": lon, "type": "shelter", "radius": 5},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                shelter_results = None
                for result in results:
                    if result.get('type') == 'shelters':
                        shelter_results = result
                        break
                
                if shelter_results and shelter_results.get('count', 0) > 0:
                    shelters = shelter_results['data'][:3]  # Mostrar máximo 3 refugios
                    
                    message = f"🏠 Encontré {shelter_results['count']} refugios cercanos:\n\n"
                    
                    for i, shelter in enumerate(shelters, 1):
                        availability = shelter.get('availability_percentage', 0)
                        status = "🟢 Disponible" if shelter.get('is_available', False) else "🔴 Lleno"
                        
                        message += f"{i}. **{shelter.get('name', 'Refugio')}**\n"
                        message += f"   📍 {shelter.get('address', 'Dirección no disponible')}\n"
                        message += f"   👥 Capacidad: {shelter.get('capacity', 0)} personas\n"
                        message += f"   📊 {status} ({availability:.0f}% disponible)\n"
                        
                        if shelter.get('contact_phone'):
                            message += f"   📞 {shelter['contact_phone']}\n"
                        
                        if shelter.get('distance'):
                            message += f"   📏 {shelter['distance']:.1f} km de distancia\n"
                        
                        message += "\n"
                    
                    dispatcher.utter_message(text=message)
                else:
                    dispatcher.utter_message(text="No encontré refugios disponibles en un radio de 5km. Te recomiendo contactar a los servicios de emergencia: 911")
                    
            else:
                dispatcher.utter_message(text="No pude acceder a la información de refugios. Contacta a emergencias: 911")
                
        except requests.RequestException:
            dispatcher.utter_message(text="No pude conectarme al servidor. En caso de emergencia, llama al 911.")
        except Exception as e:
            dispatcher.utter_message(text="Ocurrió un error. En caso de emergencia inmediata, llama al 911.")
        
        return []


class ActionReportarEmergencia(Action):
    """Acción para reportar una emergencia"""
    
    def name(self) -> Text:
        return "action_reportar_emergencia"
    
    def run(self, dispatcher, tracker, domain) -> List[Dict[Text, Any]]:
        try:
            # Obtener información del mensaje
            entities = tracker.latest_message.get('entities', [])
            text = tracker.latest_message.get('text', '')
            
            location_data = extract_location_from_entities(entities)
            
            # Extraer tipo de evento
            event_type = "other"  # por defecto
            for entity in entities:
                if entity["entity"] == "tipo_evento":
                    event_value = entity["value"].lower()
                    if "inundación" in event_value or "agua" in event_value:
                        event_type = "flood"
                    elif "contaminación" in event_value:
                        event_type = "contamination"
                    elif "infraestructura" in event_value or "falla" in event_value:
                        event_type = "infrastructure"
                    elif "sequía" in event_value:
                        event_type = "drought"
                    break
            
            # Si no hay coordenadas directas, intentar extraer del texto
            if 'lat' not in location_data or 'lon' not in location_data:
                coords = extract_coordinates_from_text(text)
                location_data.update(coords)
            
            # Coordenadas por defecto si no se proporciona ubicación específica
            lat = location_data.get('lat', -34.6118)
            lon = location_data.get('lon', -58.3960)
            
            # Preparar datos del reporte
            report_data = {
                'event_type': event_type,
                'severity': 'medium',  # por defecto
                'latitude': lat,
                'longitude': lon,
                'address': location_data.get('address', ''),
                'description': text,
                'reporter_name': '',  # El chatbot no maneja nombres por privacidad
                'reporter_phone': '',
                'reporter_email': ''
            }
            
            # Enviar reporte a la API
            response = requests.post(
                f"{DJANGO_API_URL}/report/",
                json=report_data,
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            
            if response.status_code == 201:
                data = response.json()
                message = "✅ Tu reporte de emergencia ha sido registrado exitosamente.\n\n"
                message += f"📋 ID del reporte: {data.get('id', 'N/A')}\n"
                message += "🚨 Las autoridades competentes han sido notificadas.\n\n"
                message += "Si es una emergencia inmediata que requiere atención médica o de bomberos, llama al 911."
                
                dispatcher.utter_message(text=message)
                
                # Preguntar si necesita información adicional
                dispatcher.utter_message(text="¿Necesitas información sobre refugios cercanos o evaluación de riesgo en tu zona?")
            else:
                dispatcher.utter_message(text="Hubo un problema al procesar tu reporte. Por favor, contacta directamente a los servicios de emergencia: 911")
                
        except requests.RequestException:
            dispatcher.utter_message(text="No pude enviar el reporte debido a problemas de conexión. Para emergencias inmediatas, llama al 911.")
        except Exception as e:
            dispatcher.utter_message(text="Ocurrió un error procesando el reporte. Si es una emergencia, llama inmediatamente al 911.")
        
        return []


class ActionDefaultFallback(Action):
    """Acción por defecto cuando no se entiende el mensaje"""
    
    def name(self) -> Text:
        return "action_default_fallback"
    
    def run(self, dispatcher, tracker, domain) -> List[Dict[Text, Any]]:
        message = "Lo siento, no entendí tu mensaje. Puedo ayudarte con:\n\n"
        message += "🔍 Consultar riesgo de inundación en tu zona\n"
        message += "🏠 Buscar refugios cercanos\n"
        message += "📢 Reportar emergencias hídricas\n\n"
        message += "¿En qué te puedo ayudar?"
        
        dispatcher.utter_message(text=message)
        return []


# Para uso sin Rasa completo, podemos simular una respuesta
def simulate_rasa_response(message: str, user_id: str = "user") -> Dict[str, Any]:
    """Simula una respuesta de Rasa para testing"""
    message_lower = message.lower()
    
    if "riesgo" in message_lower or "peligro" in message_lower:
        return {
            "recipient_id": user_id,
            "text": "📍 Evaluación de riesgo para tu ubicación:\n\n🚨 Nivel: MEDIO\n📝 Zona con riesgo moderado de anegamiento por lluvias intensas\n\n✅ Puedes consultar refugios cercanos si lo necesitas."
        }
    elif "refugio" in message_lower or "refugios" in message_lower:
        return {
            "recipient_id": user_id,
            "text": "🏠 Encontré 3 refugios cercanos:\n\n1. **Centro Comunal San Telmo**\n   📍 Defensa 755, San Telmo, CABA\n   👥 Capacidad: 150 personas\n   📊 🟢 Disponible (77% disponible)\n   📞 +54-11-4300-4000\n\n2. **Escuela Nº 15 Puerto Madero**\n   📍 Juana Manso 895, Puerto Madero, CABA\n   👥 Capacidad: 100 personas\n   📊 🟢 Disponible (85% disponible)\n   📞 +54-11-4300-4002"
        }
    elif "emergencia" in message_lower or "reportar" in message_lower:
        return {
            "recipient_id": user_id,
            "text": "✅ Tu reporte de emergencia ha sido registrado exitosamente.\n\n📋 ID del reporte: 1001\n🚨 Las autoridades competentes han sido notificadas.\n\nSi es una emergencia inmediata que requiere atención médica o de bomberos, llama al 911."
        }
    else:
        return {
            "recipient_id": user_id,
            "text": "¡Hola! Soy HydroAssist, tu asistente para emergencias hídricas. Puedo ayudarte con:\n\n🔍 Consultar riesgo de inundación\n🏠 Buscar refugios cercanos\n📢 Reportar emergencias\n\n¿En qué puedo asistirte?"
        }