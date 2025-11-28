# HydroAssist Chatbot

Sistema de asistencia virtual para emergencias hídricas basado en Rasa. Cubre los municipios de La Plata, Berisso y Ensenada.

## Requisitos

- Python 3.10

## Instalación

```bash
# Clonar repositorio
git clone https://github.com/pabloSalva/chatbot.git
cd chatbot

# Crear y activar entorno virtual
python3.10 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Entrenar modelo
rasa train
```

## Ejecutar

### Testing rápido (terminal)

```bash
rasa shell --debug
```

### Modo producción (con Django)

**Terminal 1 - Rasa Server:**
```bash
rasa run --enable-api --cors "*" --port 5005
```

**Terminal 2 - Action Server:**
```bash
rasa run actions --port 5055
```

Ambos servidores deben estar corriendo simultáneamente.

## Integración con Django

El sistema completo requiere 4 terminales:

```bash
# Terminal 1: Django Backend
cd ../backend
python manage.py runserver

# Terminal 2: Rasa Server
cd chatbot
rasa run --enable-api --cors "*" --port 5005

# Terminal 3: Action Server
cd chatbot
rasa run actions --port 5055

# Terminal 4: Frontend (opcional)
cd ../frontend
npm start
```

**Flujo de comunicación:**
```
Frontend → Django (8000) → Rasa (5005) → Action Server (5055) → Django API
```

## Archivos Principales

- `actions.py` - Custom actions que consultan Django API
- `domain.yml` - Intenciones, entidades, slots y respuestas
- `data/nlu.yml` - Ejemplos de entrenamiento
- `data/rules.yml` - Reglas de conversación
- `endpoints.yml` - Configuración de action server

## Re-entrenar

Después de modificar archivos de entrenamiento:

```bash
rasa train
```

## Troubleshooting

| Error | Solución |
|-------|----------|
| No model trained | `rasa train` |
| Action server not running | `rasa run actions --port 5055` |
| Connection to Django refused | Verificar Django en puerto 8000 |

