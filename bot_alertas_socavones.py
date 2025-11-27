import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Configuración de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Estados para las conversaciones
CALCULANDO_RIESGO, REPORTANDO = range(2)

# Datos del bot
numeros_emergencia = {
    'proteccion_civil': '555-123-4567',
    'bomberos': '555-123-4568', 
    'locatel': '555-565-8111',
    'sismos': '555-123-4569',
    'emergencias_general': '911'
}

informacion_socavones = """
🔍 **INFORMACIÓN SOBRE SOCAVONES - CDMX**

*¿Qué son los socavones?*
Son hundimientos bruscos del suelo causados por la erosión interna del subsuelo.

*🔴 SEÑALES DE PELIGRO:*
• Grietas en el suelo o paredes
• Hundimientos leves del pavimento  
• Charcos que no se secan sin lluvia
• Sonidos huecos al caminar
• Postes o árboles inclinados

*📍 ZONAS DE ALTO RIESGO EN CDMX:*
• Iztapalapa
• Gustavo A. Madero
• Tláhuac
• Xochimilco

*📞 NÚMEROS IMPORTANTES:*
• Protección Civil: 555-123-4567
• Locatel: 555-565-8111
• Emergencias: 911
"""

# Función para calcular riesgo de socavones
def calcular_riesgo_socavones(respuestas):
    """
    Calcula el nivel de riesgo basado en las respuestas del usuario
    Usa lógica booleana simple y ponderación
    """
    puntaje = 0
    
    # Pregunta 1: Grietas visibles (alto riesgo)
    if respuestas[0].lower() in ['sí', 'si', 's', 'yes', 'y']:
        puntaje += 4
    
    # Pregunta 2: Fugras de agua (riesgo medio-alto)
    if respuestas[1].lower() in ['sí', 'si', 's', 'yes', 'y']:
        puntaje += 3
    
    # Pregunta 3: Hundimiento visible (alto riesgo)
    if respuestas[2].lower() in ['sí', 'si', 's', 'yes', 'y']:
        puntaje += 4
    
    # Pregunta 4: Lluvias recientes (riesgo bajo)
    if respuestas[3].lower() in ['sí', 'si', 's', 'yes', 'y']:
        puntaje += 1
    
    # Clasificación del riesgo
    if puntaje >= 7:
        return {
            "nivel": "🔴 ALTO RIESGO",
            "mensaje": "PELIGRO INMINENTE - Evacue el área y contacte a Protección Civil inmediatamente",
            "acciones": [
                "• Aléjese del área inmediatamente",
                "• Llame a Protección Civil: 555-123-4567", 
                "• Alerte a sus vecinos",
                "• No permita el paso de personas o vehículos"
            ]
        }
    elif puntaje >= 4:
        return {
            "nivel": "🟡 RIESGO MEDIO", 
            "mensaje": "ZONA DE PRECAUCIÓN - Monitoree constantemente y reporte cambios",
            "acciones": [
                "• Evite transitar por la zona afectada",
                "• Reporte a las autoridades locales",
                "• Tome fotografías de seguimiento",
                "• Esté alerta a nuevas grietas o hundimientos"
            ]
        }
    else:
        return {
            "nivel": "🟢 RIESGO BAJO",
            "mensaje": "SITUACIÓN ESTABLE - Manténgase informado y alerta",
            "acciones": [
                "• Continúe con la observación regular",
                "• Conozca los números de emergencia",
                "• Reporte cualquier cambio sospechoso",
                "• Comparta información con sus vecinos"
            ]
        }

# ========== COMANDOS DEL BOT ==========

async def comando_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /start"""
    teclado_principal = [
        ['📊 Calcular Riesgo', '📞 Números Emergencia'],
        ['📝 Reportar Socavón', 'ℹ️ Info Socavones'],
        ['🆘 Ayuda Inmediata']
    ]
    marcador_teclado = ReplyKeyboardMarkup(teclado_principal, resize_keyboard=True)
    
    mensaje_bienvenida = """
🚨 **BOT DE ALERTA DE SOCAVONES - CDMX** 🚨

*¡Bienvenido/a!* Este bot te ayuda a:

📊 *Calcular Riesgo* - Evalúa el nivel de peligro en tu zona
📞 *Emergencias* - Muestra números de contacto importantes  
📝 *Reportar* - Registra socavones o señales de peligro
ℹ️ *Información* - Aprende sobre prevención de socavones
🆘 *Ayuda* - Guía de acción rápida en emergencias

*Selecciona una opción del menú:*
"""
    
    await update.message.reply_text(
        mensaje_bienvenida,
        reply_markup=marcador_teclado,
        parse_mode='Markdown'
    )

async def iniciar_calculo_riesgo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el proceso de cálculo de riesgo"""
    preguntas_riesgo = [
        "¿Ha notado GRIETAS en el suelo o paredes? (sí/no)",
        "¿Ha observado FUGAS DE AGUA en tuberías o calles? (sí/no)", 
        "¿El suelo se ha HUNDIDO visiblemente? (sí/no)",
        "¿Ha llovido FUERTEMENTE en los últimos 3 días? (sí/no)"
    ]
    
    # Guardar estado de la conversación
    context.user_data['preguntas_riesgo'] = preguntas_riesgo
    context.user_data['respuestas_riesgo'] = []
    context.user_data['pregunta_actual'] = 0
    
    await update.message.reply_text(
        "📊 **EVALUACIÓN DE RIESGO DE SOCAVONES**\n\n"
        "Responda las siguientes 4 preguntas con SÍ o NO:\n\n"
        f"*Pregunta 1:* {preguntas_riesgo[0]}"
    )
    
    return CALCULANDO_RIESGO

async def procesar_respuesta_riesgo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa cada respuesta del cálculo de riesgo"""
    respuesta_usuario = update.message.text
    preguntas = context.user_data['preguntas_riesgo']
    respuestas = context.user_data['respuestas_riesgo']
    num_pregunta = context.user_data['pregunta_actual']
    
    # Validar respuesta
    if respuesta_usuario.lower() not in ['sí', 'si', 's', 'no', 'n', 'yes', 'y']:
        await update.message.reply_text("⚠️ Por favor responda con SÍ o NO")
        return CALCULANDO_RIESGO
    
    respuestas.append(respuesta_usuario)
    num_pregunta += 1
    
    if num_pregunta < len(preguntas):
        # Siguiente pregunta
        context.user_data['pregunta_actual'] = num_pregunta
        context.user_data['respuestas_riesgo'] = respuestas
        await update.message.reply_text(f"*Pregunta {num_pregunta + 1}:* {preguntas[num_pregunta]}")
        return CALCULANDO_RIESGO
    else:
        # Todas las preguntas respondidas - calcular resultado
        resultado = calcular_riesgo_socavones(respuestas)
        
        mensaje_resultado = f"""
📊 **RESULTADO DE LA EVALUACIÓN**

*Nivel de Riesgo:* {resultado['nivel']}
*Diagnóstico:* {resultado['mensaje']}

*📋 ACCIONES RECOMENDADAS:*
"""
        for accion in resultado['acciones']:
            mensaje_resultado += f"{accion}\n"
        
        await update.message.reply_text(mensaje_resultado)
        
        # Si es alto riesgo, mostrar números de emergencia automáticamente
        if "ALTO" in resultado['nivel']:
            await mostrar_numeros_emergencia(update, context)
        
        return ConversationHandler.END

async def mostrar_numeros_emergencia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra los números de emergencia"""
    mensaje_emergencia = """
🚨 **NÚMEROS DE EMERGENCIA - CDMX** 🚨

*📞 CONTACTOS IMPORTANTES:*
"""
    
    for servicio, numero in numeros_emergencia.items():
        nombre_formateado = servicio.replace('_', ' ').title()
        mensaje_emergencia += f"• *{nombre_formateado}:* `{numero}`\n"
    
    mensaje_emergencia += "\n💡 *Consejo:* Guarde estos números en su teléfono"
    
    await update.message.reply_text(mensaje_emergencia, parse_mode='Markdown')

async def iniciar_reporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el proceso de reporte de socavón"""
    instrucciones_reporte = """
📝 **REPORTE DE SOCAVÓN O SEÑAL DE PELIGRO**

Por favor envíe la siguiente información en UN solo mensaje:

*📍 UBICACIÓN:*
- Calle, número, colonia
- Punto de referencia

*📏 DESCRIPCIÓN:*
- Tamaño aproximado
- Profundidad (si es visible)  
- Estado actual

*Ejemplo de reporte completo:*
\"Av. Central #123, Col. Centro, frente al mercado. Socavón de aproximadamente 1 metro de diámetro, profundidad desconocida. Hay grietas alrededor y el área está acordonada.\"

*⚠️ IMPORTANTE:* Manténgase a una distancia segura al reportar
"""
    
    await update.message.reply_text(instrucciones_reporte, parse_mode='Markdown')
    return REPORTANDO

async def procesar_reporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa el reporte del usuario"""
    reporte = update.message.text
    
    # Registrar el reporte (en un sistema real, guardar en base de datos)
    logger.info(f"📋 NUEVO REPORTE RECIBIDO: {reporte}")
    
    mensaje_confirmacion = f"""
✅ **REPORTE REGISTRADO EXITOSAMENTE**

*Su reporte ha sido recibido:*
\"{reporte}\"

*📞 Contacte también directamente a:*
• Protección Civil: `555-123-4567`
• Emergencias: `911`

*🛡️ Recuerde:*
- Manténgase a distancia segura
- Alerte a vecinos
- No intente cubrir el socavón
"""
    
    await update.message.reply_text(mensaje_confirmacion, parse_mode='Markdown')
    return ConversationHandler.END

async def mostrar_informacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra información educativa sobre socavones"""
    await update.message.reply_text(informacion_socavones, parse_mode='Markdown')

async def mostrar_ayuda_inmediata(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra guía de acción rápida"""
    guia_emergencia = """
🆘 **ACCIÓN INMEDIATA - SOCAVÓN DETECTADO**

*🚨 QUÉ HACER AHORA:*

1. ✅ *ALÉJESE* - Mínimo 50 metros del área
2. ✅ *BLOQUEE* - Impida el paso de personas y vehículos  
3. ✅ *LLAME* - Contacte Protección Civil: `555-123-4567`
4. ✅ *ALERTE* - Advierte a vecinos y transeúntes

*📋 PASOS SIGUIENTES:*
5. *REPORTE* - Use este bot para registro oficial
6. *DOCUMENTE* - Tome fotos desde distancia segura
7. *COORDINE* - Espere instrucciones de autoridades

*❌ QUÉ NO HACER:*
• ❌ No se acerque al borde
• ❌ No deje que niños se aproximen
• ❌ No intente cubrirlo usted mismo
• ❌ No ignore señales de advertencia

*📞 EMERGENCIAS: 911*
"""
    
    await update.message.reply_text(guia_emergencia, parse_mode='Markdown')

async def cancelar_operacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela cualquier operación en curso"""
    await update.message.reply_text(
        '🛑 Operación cancelada.\n\n'
        'Use el menú para seleccionar otra opción.'
    )
    return ConversationHandler.END

async def manejar_mensaje_general(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los mensajes del menú principal"""
    texto = update.message.text
    
    if texto == '📊 Calcular Riesgo':
        return await iniciar_calculo_riesgo(update, context)
    elif texto == '📞 Números Emergencia':
        return await mostrar_numeros_emergencia(update, context)
    elif texto == '📝 Reportar Socavón':
        return await iniciar_reporte(update, context)
    elif texto == 'ℹ️ Info Socavones':
        return await mostrar_informacion(update, context)
    elif texto == '🆘 Ayuda Inmediata':
        return await mostrar_ayuda_inmediata(update, context)
    else:
        await update.message.reply_text(
            'ℹ️ Por favor use los botones del menú para interactuar con el bot.'
        )

def main():
    """Función principal para iniciar el bot"""
    
    # Obtener el token desde variable de entorno
    token_bot = os.getenv('BOT_TOKEN')
    
    if not token_bot:
        logger.error("❌ No se encontró BOT_TOKEN en las variables de entorno")
        logger.info("💡 Asegúrate de configurar la variable BOT_TOKEN en Render.com")
        return
    
    # Crear la aplicación del bot
    aplicacion = Application.builder().token(token_bot).build()
    
    # Configurar manejadores de conversación para cálculo de riesgo
    conversacion_riesgo = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Text(['📊 Calcular Riesgo']), iniciar_calculo_riesgo)
        ],
        states={
            CALCULANDO_RIESGO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_respuesta_riesgo)
            ]
        },
        fallbacks=[CommandHandler('cancelar', cancelar_operacion)]
    )
    
    # Configurar manejadores de conversación para reportes
    conversacion_reporte = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Text(['📝 Reportar Socavón']), iniciar_reporte)
        ],
        states={
            REPORTANDO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_reporte)
            ]
        },
        fallbacks=[CommandHandler('cancelar', cancelar_operacion)]
    )
    
    # Registrar todos los manejadores
    aplicacion.add_handler(CommandHandler("start", comando_inicio))
    aplicacion.add_handler(CommandHandler("inicio", comando_inicio))
    aplicacion.add_handler(conversacion_riesgo)
    aplicacion.add_handler(conversacion_reporte)
    aplicacion.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje_general))
    
    # Iniciar el bot
    logger.info("🤖 Bot de Alertas de Socavones iniciado correctamente")
    logger.info("📡 Escuchando mensajes...")
    aplicacion.run_polling()

if __name__ == '__main__':
    main()