from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO

def generar_pdf_practica(estudiante_nombre, empresa, total_horas, seguimientos):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    # Encabezado profesional
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, "SIPRA - REPORTE OFICIAL DE PRÁCTICAS")
    
    c.setFont("Helvetica", 12)
    c.drawString(100, 720, f"Estudiante: {estudiante_nombre}")
    c.drawString(100, 700, f"Empresa: {empresa}")
    c.drawString(100, 680, f"Total de Horas Reportadas: {total_horas}")
    
    c.line(100, 670, 500, 670)
    
    # Listado de actividades
    y = 650
    c.drawString(100, y, "Detalle de Actividades:")
    y -= 20
    c.setFont("Helvetica", 10)
    
    for seg in seguimientos:
        texto = f"- {seg.fecha_actividad.strftime('%d/%m/%Y')}: {seg.descripcion} ({seg.horas_realizadas} hrs)"
        c.drawString(100, y, texto)
        y -= 15
        if y < 50: # Control de página simple
            c.showPage()
            y = 750

    c.save()
    buffer.seek(0)
    return buffer