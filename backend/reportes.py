from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
from datetime import datetime

def generar_pdf_practica(estudiante_nombre: str, empresa: str, seguimientos: list):
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
    p.drawString(50, height - 130, f"FECHA DE REPORTE: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    p.line(50, height - 140, 550, height - 140)


    y = height - 165
    p.drawString(50, y, "Fecha")
    p.drawString(120, y, "Descripción Actividad")
    p.drawString(450, y, "Horas")
    y -= 20

    p.setFont("Helvetica", 9)
    total_horas = 0
    for s in seguimientos:
        if y < 100: 
            p.showPage()
            y = height - 50
        
        p.drawString(50, y, str(s.fecha_actividad.date()))
        desc = (s.descripcion[:65] + '..') if len(s.descripcion) > 65 else s.descripcion
        p.drawString(120, y, desc)
        p.drawString(450, y, f"{s.horas_realizadas}h")
        total_horas += s.horas_realizadas
        y -= 20


    p.line(50, y, 550, y)
    y -= 20
    p.setFont("Helvetica-Bold", 10)
    p.drawString(350, y, f"TOTAL HORAS VALIDADAS: {total_horas}h")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer
