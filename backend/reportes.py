from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
from datetime import datetime

def generar_pdf_practica(estudiante_nombre: str, empresa: str, tutor_nombre: str, seguimientos: list):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter


    p.setFont("Helvetica-Bold", 14)
    p.drawCentredString(width/2, height - 50, "CORPORACION UNIVERSITARIA RAFAEL NUÑEZ")
    p.setFont("Helvetica", 12)
    p.drawCentredString(width/2, height - 70, "SIPGA: Sistema de Información para el Seguimiento de Prácticas")
    
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, height - 100, f"ESTUDIANTE: {estudiante_nombre}")
    p.drawString(50, height - 115, f"EMPRESA: {empresa}")
    p.drawString(300, height - 100, f"TUTOR: {tutor_nombre}")
    p.drawString(300, height - 115, f"FECHA REPORTE: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    p.line(50, height - 130, 550, height - 130)


    y = height - 155
    p.drawString(50, y, "Fecha")
    p.drawString(120, y, "Descripción Actividad")
    p.drawString(410, y, "Horas")
    p.drawString(460, y, "Estado")
    y -= 20

    p.setFont("Helvetica", 9)
    total_horas = 0
    for s in seguimientos:
        if y < 100: 
            p.showPage()
            y = height - 50
            p.setFont("Helvetica", 9)
        
        # Manejo seguro de fecha
        fecha_str = "—"
        if s.fecha_actividad:
            fecha_str = str(s.fecha_actividad.date()) if hasattr(s.fecha_actividad, 'date') else str(s.fecha_actividad)[:10]
        p.drawString(50, y, fecha_str)
        
        # Manejo seguro de descripción
        desc_raw = s.descripcion if s.descripcion else "Sin descripción"
        desc = (desc_raw[:55] + '..') if len(desc_raw) > 55 else desc_raw
        p.drawString(120, y, desc)
        
        # Manejo de horas
        p.drawString(410, y, f"{s.horas_realizadas or 0}h")
        
        # Manejo estético de estado (Sin guiones y simplificado)
        estado_raw = str(s.estado if s.estado else "borrador")
        # Eliminar prefijos de Enum, quitar guiones, y tomar solo la primera palabra clave
        estado_limpio = estado_raw.replace('StatusEnum.', '').split('_')[0].upper()
        p.drawString(460, y, estado_limpio)
        
        # Lógica de suma basada en el estado real
        if any(x in estado_raw.upper() for x in ["APROBADO", "VALIDADO"]):
            total_horas += (s.horas_realizadas or 0)
            
        y -= 20


    p.line(50, y, 550, y)
    y -= 20
    p.setFont("Helvetica-Bold", 10)
    p.drawString(350, y, f"TOTAL HORAS APROBADAS: {total_horas}h")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer
