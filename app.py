from flask import Flask, render_template_string, request, session, redirect, url_for
import json
import os
import random
from datetime import timedelta
import secrets

app = Flask(__name__)
# Generar una clave secreta fuerte para la sesión
app.secret_key = secrets.token_hex(16)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

# Directorio para archivos JSON de categorías
CATEGORIES_DIR = 'categorias'

# --- FUNCIÓN DE UTILIDAD: Generar color brillante/encendido aleatorio (SÓLIDO) ---
def generate_random_pastel_color():
    """
    Genera un color hexadecimal brillante/encendido aleatorio (sólido),
    que contrasta bien con el texto blanco. (Cambiado de pastel a brillante)
    """
    # Inicializa los canales RGB con valores bajos (oscuros, 0 a 150)
    r = random.randint(0, 150)
    g = random.randint(0, 150)
    b = random.randint(0, 150)

    # Elige uno de los canales para forzarlo a ser alto (brillante, 200 a 255)
    choice = random.choice(['r', 'g', 'b'])

    if choice == 'r':
        r = random.randint(200, 255)
    elif choice == 'g':
        g = random.randint(200, 255)
    else: # choice == 'b'
        b = random.randint(200, 255)

    return f'#{r:02x}{g:02x}{b:02x}'


def load_categories():
    """Carga todas las categorías desde los archivos JSON"""
    categories = {}
    if not os.path.exists(CATEGORIES_DIR):
        os.makedirs(CATEGORIES_DIR)
        return categories
    
    for filename in os.listdir(CATEGORIES_DIR):
        if filename.endswith('.json'):
            try:
                with open(os.path.join(CATEGORIES_DIR, filename), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    categories[data['categoria']] = data
            except Exception as e:
                print(f"Error cargando {filename}: {e}")
    return categories

def select_word_and_hints(categories_data, selected_categories):
    """Selecciona una palabra aleatoria y sus pistas de las categorías seleccionadas"""
    available_words = []
    
    for cat_name in selected_categories:
        if cat_name in categories_data:
            cat = categories_data[cat_name]
            for word_data in cat.get('palabras', []):
                available_words.append({
                    'categoria': cat_name,
                    'palabra': word_data['palabra'],
                    'pistas': word_data.get('pistas', [])
                })
    
    if not available_words:
        return None
    
    return random.choice(available_words)

# --- PLANTILLAS HTML ---

# Estilos y estructura base
MAIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Juego del Underconver - Royer Blackberry</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            padding: 10px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 600px;
            width: 100%;
        }
        h1 { color: #667eea; text-align: center; margin-bottom: 30px; font-size: 2.5em; }
        h2 { color: #764ba2; margin-bottom: 20px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; color: #333; font-weight: 600; }
        input[type="number"], input[type="text"], select { 
            width: 100%; padding: 12px; border: 2px solid #e0e0e0;
            border-radius: 8px; font-size: 16px; transition: border-color 0.3s;
        }
        input[type="number"]:focus, input[type="text"]:focus, select:focus { outline: none; border-color: #667eea; }
        
        /* ESTILOS DE CHECKBOX MODERNOS Y GRANDES */
        .checkbox-group {
            background: #f8f9fa; padding: 15px; border-radius: 8px;
            min-height: 300px; 
            max-height: 400px; /* Reducido un poco para consistencia */
            overflow-y: auto;
        }
        .checkbox-item { 
            margin-bottom: 12px; 
            display: flex; 
            align-items: center;
        }
        .checkbox-item input[type="checkbox"] { 
            width: 22px; 
            height: 22px;
            min-width: 22px; 
            margin-right: 15px; 
            cursor: pointer;
            border: 2px solid #667eea;
            appearance: none; 
            border-radius: 6px; /* Más suave */
            position: relative;
        }
        .checkbox-item input[type="checkbox"]:checked {
            background-color: #667eea;
            border-color: #667eea;
        }
        .checkbox-item input[type="checkbox"]:checked::before {
            content: '✓';
            display: block;
            color: white;
            font-size: 18px; /* Tamaño del check */
            line-height: 1;
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-weight: bold;
        }
        .checkbox-item label { 
            margin-bottom: 0; 
            line-height: 1.2;
            cursor: pointer;
            font-weight: 400; /* Menos negrita en el texto del elemento */
        }
        /* FIN ESTILOS CHECKBOX */

        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; border: none; padding: 15px 30px; font-size: 18px;
            border-radius: 8px; cursor: pointer; width: 100%;
            transition: transform 0.2s; font-weight: 600;
        }
        button:hover { transform: translateY(-2px); }
        button:active { transform: translateY(0); }
        /* ESTILO DE LA TARJETA DEL JUGADOR - USA COLOR SÓLIDO */
        .player-card {
            background: #667eea; /* Color por defecto, será sobreescrito por inline style */
            color: white; padding: 10px; border-radius: 15px;
            text-align: center; margin-bottom: 20px;
            transition: background 0.5s ease-in-out; 
        }
        .player-card h2 { color: white; margin-bottom: 15px; }
        
        .word-display {
            padding: 20px;
            border-radius: 10px; 
            font-weight: bold; 
            margin: 20px 0;
            cursor: pointer;
            user-select: none;
            transition: color 0.1s ease-out, background 0.1s ease-out, font-size 0.1s ease-out, max-height 0.3s ease-out; 
            
            min-height: 220px; 
            overflow: hidden; 
            font-size: 2em; 
        }
        .impostor-display-final {
            background: #ff6b6b;
            font-size: 1.5em;
            cursor: default;
        }

        .hint-box {
            background: #fff3cd; border: 2px solid #ffc107; padding: 15px;
            border-radius: 8px; margin-top: 15px; text-align: left;
        }
        .hint-box p { color: #856404; margin: 5px 0; }
        .category-badge {
            background: #764ba2; color: white; padding: 5px 15px;
            border-radius: 20px; display: inline-block; margin-bottom: 10px;
        }
        .btn-secondary { 
            background: #6c757d; 
            margin-top: 10px; 
            background: linear-gradient(135deg, #6c757d 0%, #495057 100%);
        }
        .warning {
            background: #fff3cd; border-left: 4px solid #ffc107;
            padding: 15px; margin-bottom: 20px; border-radius: 4px;
        }
        .info {
            background: #d1ecf1; border-left: 4px solid #0c5460;
            padding: 15px; margin-bottom: 20px; border-radius: 4px; color: #0c5460;
        }
    </style>
</head>
<body>
    <div class="container">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
'''

# Template de Configuración (MODIFICADO para Diseño Moderno)
SETUP_TEMPLATE = MAIN_TEMPLATE.replace('{% block content %}{% endblock %}', '''
        <h1>🎭 Configuración de Ronda</h1>
        
        {% if error %}
        <div class="warning">
            <strong>⚠️ {{ error }}</strong>
        </div>
        {% endif %}
        
        <form method="POST" action="{{ url_for('setup') }}">
            <div class="form-group">
                <label for="player_names">Nombres de jugadores (Separados por coma):</label>
                <input type="text" id="player_names" name="player_names" 
                       placeholder="Ej: Ana, Carlos, Diego, Eva" required>
            </div>
            
            <div class="form-group">
                <label for="num_impostors">Número de impostores:</label>
                <select id="num_impostors" name="num_impostors">
                    <option value="1">1 impostor</option>
                    <option value="2">2 impostores</option>
                    <option value="3">3 impostores</option>
                </select>
            </div>
            
            <div class="form-group">
                <label>🌐 Selecciona las Categorías:</label>
                {% if categories %}
                <div class="checkbox-group">
                    {% for cat_name in categories.keys() %}
                    <div class="checkbox-item">
                        <input type="checkbox" id="cat_{{ loop.index }}" name="selected_categories" value="{{ cat_name }}" checked>
                        <label for="cat_{{ loop.index }}" style="display: inline;">
                            {{ cat_name }} ({{ categories[cat_name].palabras|length }} palabras)
                        </label>
                    </div>
                    {% endfor %}
                </div>
                {% else %}
                <div class="warning">
                    No hay categorías disponibles. Por favor, agrega archivos JSON en la carpeta 'categorias'.
                </div>
                {% endif %}
            </div>
            
            <div class="form-group">
                <label>Opciones Adicionales:</label>
                <div class="checkbox-item">
                    <input type="checkbox" id="hints_enabled" name="hints_enabled" checked>
                    <label for="hints_enabled" style="display: inline;">Activar pistas (Solo visibles para el impostor)</label>
                </div>
            </div>
            
            <button type="submit">🚀 Iniciar Juego</button>
        </form><br/>Royer Blackberry - <a href="https://github.com/RBlackby/undercover-game" target="_blank">Repositorio del Juego Undercover</a> - 2025
'''
)

# Template de Vista de Jugador
PLAYER_VIEW_TEMPLATE = MAIN_TEMPLATE.replace('{% block content %}{% endblock %}', '''
        <script>
            // Función para revelar u ocultar la información (palabra o rol)
            function revealInfo(isPressed, isImpostor) {
                const card = document.getElementById('secret-info-display');
                const hintBox = document.getElementById('impostor-hint-box'); // Nuevo
                
                if (card) {
                    if (isPressed) {
                        // REVELAR
                        card.style.color = card.getAttribute('data-revealed-color'); 
                        
                        if (isImpostor) {
                            // Si es impostor: cambia fondo a rojo y quita el límite de altura
                            card.style.background = '#ff6b6b'; 
                            card.style.fontSize = '1.5em'; 
                            card.style.maxHeight = '500px'; 
                            if (hintBox) {
                                hintBox.style.display = 'block'; // Muestra la pista
                            }
                        } else {
                            // Civil
                            card.style.background = 'white';
                            card.style.fontSize = '2em'; 
                        }
                    } else {
                        // OCULTAR
                        setTimeout(() => {
                            card.style.color = card.getAttribute('data-hidden-color');
                            
                            // Ambas tarjetas deben volver al estado visual de camuflaje
                            card.style.background = 'white';
                            card.style.fontSize = '2em'; 
                            
                            if (isImpostor) {
                                // Restablece la altura máxima y oculta la pista
                                card.style.maxHeight = '140px'; 
                                if (hintBox) {
                                    hintBox.style.display = 'none'; // Oculta la pista
                                }
                            }
                        }, 50); 
                    }
                }
            }
        </script>
        <style>
            /* Estilo para asegurar el camuflaje del contenido */
            .word-display {
                padding: 20px;
                border-radius: 10px; 
                font-weight: bold; 
                margin: 20px 0;
                cursor: pointer;
                user-select: none;
                transition: color 0.1s ease-out, background 0.1s ease-out, font-size 0.1s ease-out, max-height 0.3s ease-out; 
                
                max-height: 140px; 
                overflow: hidden; 
                font-size: 2em; 
            }
            
            /* Asegurarse de que la pista inicie oculta para el camuflaje */
            .hint-box.hidden {
                display: none;
            }
        </style>
        
        <h1>Juego del Impostor</h1>
        
        {# SE INYECTA EL ESTILO DE COLOR SÓLIDO Y BRILLANTE #}
        <div class="player-card" style="{{ player_card_style }}">
            {# MUESTRA EL NOMBRE REAL Y EL NÚMERO DE TURNO #}
            <h2>{{ current_player_name }} ({{ current_player }}/{{ total_players }})</h2>
            
            
            
            
            {# ========================================================= #}
            {# Lógica de Visualización (Civil o Impostor) - OCULTOS Y UNIFICADOS #}
            {# ========================================================= #}
            
            {% if is_impostor %}
                <div class="word-display"
                     id="secret-info-display"
                     data-hidden-color="white"       {# Oculto: Color blanco (igual al fondo) #}
                     data-revealed-color="white"     {# Revelado: Color blanco (sobre fondo rojo) #}
                     onmousedown="revealInfo(true, true)" 
                     onmouseup="revealInfo(false, true)" 
                     ontouchstart="revealInfo(true, true)" 
                     ontouchend="revealInfo(false, true)"
                     style="color: white; background: white;"> {# Inicia OCULTO como CIVIL #}
                    
                    {# Contenido del impostor #}
                    ERES EL IMPOSTOR
                    <p style="margin-top: 15px; font-weight: normal; font-size: 0.8em; color: inherit;">Los demás tienen una palabra secreta.</p>
                    <p style="font-top: 5px; font-weight: normal; font-size: 0.8em; color: inherit;"><strong>Intenta pasar desapercibido.</strong></p>

                    {# PISTA DE APOYO: AHORA ENVUELTA EN UNA CAPA OCULTA POR DEFECTO #}
                    {% if single_hint %} 
                    <div id="impostor-hint-box" 
                         class="hint-box hidden" {# <-- INICIA OCULTA #}
                         style="margin-top: 20px; background: rgba(255, 255, 255, 0.8);"> 
                        <strong style="color: #856404;">💡 Pista de apoyo:</strong>
                        <div style="margin-top: 10px;">
                            <span style="background: white; color: #856404; padding: 8px 15px; border-radius: 20px; font-weight: 600;">{{ single_hint }}</span>
                        </div>
                    </div>
                    {% endif %}
                    
                </div>
                
            {% else %}
                <div class="word-display" 
                     id="secret-info-display"
                     data-hidden-color="white"       {# Oculto: Color blanco (igual al fondo) #}
                     data-revealed-color="#667eea"   {# Revelado: Color azul (sobre fondo blanco) #}
                     onmousedown="revealInfo(true, false)" 
                     onmouseup="revealInfo(false, false)" 
                     ontouchstart="revealInfo(true, false)" 
                     ontouchend="revealInfo(false, false)"
                     style="color: white; background: white;"> {# Oculta el texto estableciendo su color igual al fondo #}
                    {{ palabra }}
                </div>
            {% endif %}

            <p style="margin-top: 15px;">**¡Mantén presionado sobre la caja para revelar tu rol/palabra!**</p>
            
        </div>
        
        <form method="POST" action="{{ url_for('next_player') }}">
            {% if current_player < total_players %}
            <button type="submit">Siguiente Jugador →</button>
            {% else %}
            <button type="submit">Comenzar a Jugar</button>
            {% endif %}
        </form>
        
        <form method="POST" action="{{ url_for('reset') }}" style="margin-top: 10px;">
            <button type="submit" class="btn-secondary">Cancelar y Volver al Inicio</button>
        </form><br/>Royer Blackberry - <a href="https://github.com/RBlackby/undercover-game">Repositorio del Juego Undercover</a> - 2025
'''
)


# Template de Juego Completo (MODIFICADO para Diseño Moderno)
GAME_COMPLETE_TEMPLATE = MAIN_TEMPLATE.replace('{% block content %}{% endblock %}', '''
    <script>
        // 1. Variable global para almacenar el ID del intervalo del temporizador
        let countdownInterval;

        // Función para mostrar la información del impostor y ocultar el botón
        function mostrarImpostores() {
            // DETENER EL TEMPORIZADOR AQUI
            if (countdownInterval) {
                clearInterval(countdownInterval);
                const display = document.getElementById('countdown');
                // Si el tiempo no había terminado, muestra un mensaje de detención
                if (display && display.textContent.includes(":")) { 
                    display.textContent = "00:00 - ¡DETENIDO!";
                }
            }

            const infoDiv = document.getElementById('impostor-info');
            const btn = document.getElementById('mostrar-btn');
            
            if (infoDiv) {
                // Se usa scrollHeight para la animación de revelación
                infoDiv.style.maxHeight = infoDiv.scrollHeight + "px"; 
                infoDiv.style.opacity = '1';
            }
            if (btn) {
                btn.style.display = 'none'; // Oculta el botón después de presionar
            }
        }
        
        // FUNCIÓN DE CUENTA REGRESIVA
        function iniciarCuentaRegresiva(duracion, display) {
            let timer = duracion, minutos, segundos;
            
            // 2. Almacenar el intervalo en la variable global
            countdownInterval = setInterval(function () { 
                minutos = parseInt(timer / 60, 10);
                segundos = parseInt(timer % 60, 10);

                minutos = minutos < 10 ? "0" + minutos : minutos;
                segundos = segundos < 10 ? "0" + segundos : segundos;

                display.textContent = minutos + ":" + segundos;

                if (--timer < 0) {
                    clearInterval(countdownInterval); // Limpia la variable global al terminar
                    display.textContent = "¡Tiempo terminado!";
                    // Opcional: habilitar el botón de 'Mostrar Impostores' si estaba deshabilitado
                }
            }, 1000);
        }

        // --- PUNTO CLAVE: UNIFICAR LA INICIALIZACIÓN ---
        document.addEventListener('DOMContentLoaded', function() {
            // Inicializar la cuenta regresiva de 3 minutos (180 segundos)
            const tresMinutos = 60 * 3;
            const display = document.getElementById('countdown');
            if (display) {
                iniciarCuentaRegresiva(tresMinutos, display);
            }
        });
    </script>
    <style>
    

        /* --- ESTILO DE TEMPORIZADOR AÑADIDO/AJUSTADO --- */
        #countdown-container {
            text-align: center;
            margin: 30px auto;
            padding: 20px;
            border-radius: 15px;
            background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
            color: white;
            box-shadow: 0 8px 25px rgba(0,0,0,0.2);
        }
        #countdown-container h3 {
            color: #ffe3e3;
            margin-bottom: 10px;
            font-size: 0.8em;
        }
        #countdown {
    font-size: 2em;
    font-weight: 900;
    letter-spacing: 0px;
    display: block;
    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
}
        /* -------------------------------------- */
       /* Estilo para las tarjetas de resultado */
            .result-card {
                background: #f7f9fc;
                padding: 25px;
                border-radius: 12px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.08);
                margin-bottom: 20px;
                text-align: center;
                border-left: 5px solid #667eea; /* Color primario */
            }
            .result-card h3 {
                color: #764ba2;
                margin-bottom: 15px;
                font-size: 1.6em;
            }
            .result-card strong {
                font-weight: 700;
                color: #333;
            }
            /* Estilo específico para la información secreta (Impostor/Palabra) */
            #impostor-info {
                background: #ffe3e3; /* Fondo más suave para la revelación */
                border-left-color: #ff6b6b; /* Rojo para Impostor */
                transition: max-height 0.5s ease-in-out, opacity 0.5s ease-in-out; 
                max-height: 0; /* Inicia oculto */
                opacity: 0;
                overflow: hidden;
            }
            #impostor-info h3 {
                color: #ff6b6b; /* Título rojo */
            }
            .word-of-the-game {
                font-size: 2.5em;
                font-weight: bold;
                color: #667eea;
                margin-top: 10px;
                display: block;
                padding: 10px;
                border-radius: 8px;
                background: #e9ecef;
            }
            .player-list {
                font-size: 1.2em;
                margin-top: 10px;
                line-height: 1.6;
            }
            .start-player-info {
                background: #d1ecf1;
                border: 1px solid #bee5eb;
                color: #0c5460;
                padding: 15px;
                border-radius: 10px;
                font-size: 1.2em;
                font-weight: 600;
                margin-bottom: 20px;
                text-align: center;
            }
            .start-player-info span {
                color: #764ba2;
                font-size: 1.4em;
                font-weight: bold;
                display: block;
                margin-top: 5px;
            }
    </style>

    <h1>🎉 ¡A jugar!</h1>

    {# --- CONTENEDOR DEL TEMPORIZADOR --- #}
    <div id="countdown-container">
        <h3>Tiempo de Discusión</h3>
        <span id="countdown">03:00</span>
    </div>
    {# ------------------------------------ #}
    
    <div class="result-card">
        <p><strong>Total de jugadores:</strong> {{ total_players }}</p>
        <p><strong>Número de Impostores:</strong> {{ num_impostors }}</p>
    </div>

    {# Información del jugador inicial destacada #}
    <div class="start-player-info">
        Inicia el juego: 
        <span>{{ jugador_inicial }}</span>
    </div>

    {# Botón para revelar la información secreta #}
    <button id="mostrar-btn" onclick="mostrarImpostores()" style="margin-top: 10px; margin-bottom: 20px;">
        Mostrar Impostor{{ "es" if num_impostors > 1 else "" }} y Palabra Secreta
    </button>

   {# La información secreta del juego: OCULTA POR DEFECTO #}
        <div id="impostor-info" class="result-card"> 
            
            <h3>Terminó el juego</h3>

            {# Impostor(es) #}
            <h4>🎭 Impostor{{ "es" if num_impostors > 1 else "" }}</h4>
            <div class="player-list">
                {{ impostor_names }}
            </div>
            
            <hr style="margin: 20px 0; border: 0; border-top: 1px solid #ccc;"/>

            {# Palabra Secreta #}
            <h4>Categoría:</h4>  {{ categoria }}
            <span class="word-of-the-game">
                {{ palabra }} 
            </span>

        </div>
    
    {# Sección de Reglas - Mantiene el estilo "warning" #}
    <div class="warning" style="margin-top: 20px;">
        <h3>📜 Reglas Rápidas:</h3>
        <ul style="margin-left: 20px; margin-top: 10px;">
            <li>Discutan quién creen que es el impostor.</li>
            <li>Si la mayoría vota correctamente al impostor, ganan los civiles.</li>
            <li>Si votan a un civil o no logran identificar al impostor, gana el impostor.</li>
        </ul>
    </div>
    
    <form method="POST" action="{{ url_for('reset') }}">
        <button type="submit">🔁 Nuevo Juego</button>
    </form><br/>Royer Blackberry - <a href="https://github.com/RBlackby/undercover-game" target="_blank">Repositorio del Juego Undercover</a> - 2025
'''
)

# --- RUTAS DE FLASK ---

@app.route('/')
def index():
    session.clear()
    return redirect(url_for('setup'))

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    categories = load_categories()
    
    if request.method == 'POST':
        try:
            player_names_raw = request.form.get('player_names', '')
            
            # Limpiar y obtener nombres
            player_names = [name.strip() for name in player_names_raw.split(',') if name.strip()]
            num_players = len(player_names)
            
            # Obtener y validar el número de impostores
            num_impostors = int(request.form.get('num_impostors', 1))
            selected_categories = request.form.getlist('selected_categories')
            hints_enabled = 'hints_enabled' in request.form
            
            # Validaciones
            if num_players < 3 or num_players > 20:
                error = "Debes ingresar entre 3 y 20 nombres de jugadores."
                return render_template_string(SETUP_TEMPLATE, categories=categories, error=error)
            
            if not selected_categories:
                error = "Debes seleccionar al menos una categoría"
                return render_template_string(SETUP_TEMPLATE, categories=categories, error=error)

            # Ajustar y validar número de impostores (asegura al menos 1 civil)
            num_impostors = max(1, min(num_impostors, num_players - 1))
            
            # Seleccionar palabra y pistas
            word_data = select_word_and_hints(categories, selected_categories)
            if not word_data:
                error = "No hay palabras disponibles en las categorías seleccionadas"
                return render_template_string(SETUP_TEMPLATE, categories=categories, error=error)
            
            # Seleccionar impostores aleatoriamente (índices basados en 0)
            impostor_indices = random.sample(range(0, num_players), num_impostors)
            
            # Inicializar el diccionario de colores
            session['player_colors'] = {} 
            
            # Guardar en sesión
            session['player_names'] = player_names
            session['num_players'] = num_players
            session['current_player_index'] = 0 # Usamos índice base 0
            session['palabra'] = word_data['palabra']
            session['categoria'] = word_data['categoria']
            session['pistas'] = word_data['pistas']
            session['hints_enabled'] = hints_enabled
            session['impostor_indices'] = impostor_indices # Guardamos índices
            session['num_impostors'] = num_impostors
            
            return redirect(url_for('show_player'))
            
        except Exception as e:
            error = f"Error al configurar el juego: {str(e)}"
            return render_template_string(SETUP_TEMPLATE, categories=categories, error=error)
    
    return render_template_string(SETUP_TEMPLATE, categories=categories, error=None)

@app.route('/player')
def show_player():
    if 'num_players' not in session:
        return redirect(url_for('setup'))
    
    current_index = session.get('current_player_index', 0)
    total = session.get('num_players', 0)
    player_names = session.get('player_names', [])
    
    if current_index >= total:
        return redirect(url_for('game_complete'))
    
    # Obtener el nombre del jugador y su número (base 1)
    current_player_name = player_names[current_index]
    current_player_number = current_index + 1
    
    # LÓGICA DE COLOR ALEATORIO POR JUGADOR
    player_colors = session.get('player_colors', {})
    
    # Asignar un color si el jugador aún no tiene uno (usando la función de color BRILLANTE)
    if current_player_name not in player_colors:
        player_colors[current_player_name] = generate_random_pastel_color()
        session['player_colors'] = player_colors # Guardar el diccionario actualizado
    
    # Crear el estilo CSS en línea para la tarjeta (color sólido)
    color = player_colors[current_player_name]
    player_card_style = f"background: {color};" 
    
    # Comprobar si es impostor (usando el índice base 0)
    is_impostor = current_index in session.get('impostor_indices', [])
    hints_enabled = session.get('hints_enabled', False)
    hints_list = session.get('pistas', [])
    
    # Lógica de Pista Única
    single_hint = None
    if is_impostor and hints_enabled and hints_list:
        single_hint = random.choice(hints_list)

    return render_template_string(PLAYER_VIEW_TEMPLATE,
                                 current_player=current_player_number, # Número de turno
                                 current_player_name=current_player_name, # Nombre real
                                 total_players=total,
                                 palabra=session.get('palabra', ''),
                                 categoria=session.get('categoria', ''),
                                 single_hint=single_hint, 
                                 is_impostor=is_impostor,
                                 player_card_style=player_card_style) # <-- PASAR EL ESTILO

@app.route('/next', methods=['POST'])
def next_player():
    if 'current_player_index' in session:
        session['current_player_index'] += 1
    return redirect(url_for('show_player'))

# ... (código anterior)

@app.route('/complete')
def game_complete():
    if 'num_players' not in session or 'impostor_indices' not in session:
        return redirect(url_for('setup'))
    
    # Recalcular los nombres de los impostores para la pantalla final
    player_names = session.get('player_names', [])
    impostor_indices = session.get('impostor_indices', [])
    
    # Asegurarse de que los índices sean válidos
    impostor_names = [
        player_names[i] for i in impostor_indices if i < len(player_names)
    ]
    
    # Obtener la palabra secreta
    palabra_secreta = session.get('palabra', 'N/A')

    # --- NUEVA LÓGICA: SELECCIONAR JUGADOR INICIAL ALEATORIO ---
    jugador_inicial = "Nadie (Error)"
    if player_names:
        jugador_inicial = random.choice(player_names)
    # --- FIN NUEVA LÓGICA ---

    return render_template_string(GAME_COMPLETE_TEMPLATE,
                                 total_players=session.get('num_players', 0),
                                 num_impostors=session.get('num_impostors', 1),
                                 categoria=session.get('categoria', 'N/A'),
                                 palabra=palabra_secreta, 
                                 impostor_names=", ".join(impostor_names),
                                 # --- PASAR NUEVA VARIABLE ---
                                 jugador_inicial=jugador_inicial) 

@app.route('/reset', methods=['POST'])
# ... (código posterior)

@app.route('/reset', methods=['POST'])
def reset():
    session.clear()
    return redirect(url_for('setup'))

if __name__ == '__main__':
    # Asegúrate de tener la carpeta 'categorias' con archivos JSON
    app.run(debug=True, port=5000)