from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from app.config import settings


# ─── CONFIGURACIÓN DEL SERVICIO DE EMAIL ─────────────────────────────────────────────
conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)


# ─── FUNCIONES PARA ENVIAR EMAILS ────────────────────────────
async def enviar_email(destinatario: EmailStr, asunto: str, cuerpo_html: str):
    mensaje = MessageSchema(
        subject=asunto,
        recipients=[destinatario],
        body=cuerpo_html,
        subtype=MessageType.html,
    )
    fm = FastMail(conf)
    await fm.send_message(mensaje)


# ─── PLANTILLAS DE EMAIL ────────────────────────────

def plantilla_base(titulo: str, contenido: str) -> str:
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #f9fafb; padding: 20px;">
        <div style="background: #b91c1c; padding: 24px; border-radius: 12px 12px 0 0; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 24px;">SIGEU</h1>
            <p style="color: #fecaca; margin: 4px 0 0; font-size: 13px;">Sistema de Gestión de Espacios Universitarios</p>
        </div>
        <div style="background: white; padding: 32px; border-radius: 0 0 12px 12px; border: 1px solid #e5e7eb;">
            <h2 style="color: #1f2937; margin-top: 0;">{titulo}</h2>
            {contenido}
        </div>
        <p style="text-align: center; color: #9ca3af; font-size: 12px; margin-top: 16px;">
            Este es un correo automático, por favor no respondas a este mensaje.
        </p>
    </div>
    """

def email_reserva_creada(nombre: str, reservation_number: str, espacio: str, fecha: str, hora_inicio: str, hora_fin: str) -> str:
    contenido = f"""
        <p>Hola <strong>{nombre}</strong>,</p>
        <p>Tu reserva ha sido registrada exitosamente con los siguientes detalles:</p>
        <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
            <tr><td style="padding: 8px 0; color: #6b7280;">N° de reserva:</td><td style="padding: 8px 0; font-weight: bold;">#{reservation_number}</td></tr>
            <tr><td style="padding: 8px 0; color: #6b7280;">Espacio:</td><td style="padding: 8px 0; font-weight: bold;">{espacio}</td></tr>
            <tr><td style="padding: 8px 0; color: #6b7280;">Fecha:</td><td style="padding: 8px 0; font-weight: bold;">{fecha}</td></tr>
            <tr><td style="padding: 8px 0; color: #6b7280;">Horario:</td><td style="padding: 8px 0; font-weight: bold;">{hora_inicio} - {hora_fin}</td></tr>
        </table>
        <p>Tu reserva está en estado <strong style="color: #d97706;">Pendiente</strong> hasta la fecha del evento.</p>
        <p>Gracias por usar SIGEU.</p>
    """
    return plantilla_base("✅ Reserva confirmada", contenido)

def email_reserva_cancelada(nombre: str, reservation_number: str, espacio: str, fecha: str) -> str:
    contenido = f"""
        <p>Hola <strong>{nombre}</strong>,</p>
        <p>Tu reserva ha sido <strong style="color: #dc2626;">cancelada</strong>:</p>
        <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
            <tr><td style="padding: 8px 0; color: #6b7280;">N° de reserva:</td><td style="padding: 8px 0; font-weight: bold;">#{reservation_number}</td></tr>
            <tr><td style="padding: 8px 0; color: #6b7280;">Espacio:</td><td style="padding: 8px 0; font-weight: bold;">{espacio}</td></tr>
            <tr><td style="padding: 8px 0; color: #6b7280;">Fecha:</td><td style="padding: 8px 0; font-weight: bold;">{fecha}</td></tr>
        </table>
        <p>Si esto fue un error o necesitas hacer una nueva reserva, ingresa a la plataforma SIGEU.</p>
    """
    return plantilla_base("❌ Reserva cancelada", contenido)

def email_recordatorio(nombre: str, reservation_number: str, espacio: str, fecha: str, hora_inicio: str) -> str:
    contenido = f"""
        <p>Hola <strong>{nombre}</strong>,</p>
        <p>Este es un recordatorio de tu próxima reserva:</p>
        <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
            <tr><td style="padding: 8px 0; color: #6b7280;">N° de reserva:</td><td style="padding: 8px 0; font-weight: bold;">#{reservation_number}</td></tr>
            <tr><td style="padding: 8px 0; color: #6b7280;">Espacio:</td><td style="padding: 8px 0; font-weight: bold;">{espacio}</td></tr>
            <tr><td style="padding: 8px 0; color: #6b7280;">Fecha:</td><td style="padding: 8px 0; font-weight: bold;">{fecha}</td></tr>
            <tr><td style="padding: 8px 0; color: #6b7280;">Hora de inicio:</td><td style="padding: 8px 0; font-weight: bold;">{hora_inicio}</td></tr>
        </table>
        <p>¡No olvides asistir a tiempo!</p>
    """
    return plantilla_base("⏰ Recordatorio de reserva", contenido)

def email_recuperacion(nombre: str, codigo: str) -> str:
    contenido = f"""
        <p>Hola <strong>{nombre}</strong>,</p>
        <p>Recibimos una solicitud para restablecer tu contraseña. Usa el siguiente código de verificación:</p>
        <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
            <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #b91c1c;">{codigo}</span>
        </div>
        <p>Este código es válido por <strong>15 minutos</strong>.</p>
        <p>Si no solicitaste este cambio, puedes ignorar este correo.</p>
    """
    return plantilla_base("🔑 Recuperación de contraseña", contenido)