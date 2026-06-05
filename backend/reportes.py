from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
from datetime import datetime


def _estado_label(estado) -> str:
    if estado is None:
        return "—"
    valor = getattr(estado, "value", estado)
    return str(valor).replace("StatusEnum.", "").replace("_", " ").upper()


def _fecha_label(fecha) -> str:
    if fecha is None:
        return "—"
    if hasattr(fecha, "date"):
        return str(fecha.date())
    texto = str(fecha)
    return texto.split("T")[0].split(" ")[0]


def _dibujar_encabezado_tabla(p, y: float) -> float:
    p.setFont("Helvetica-Bold", 9)
    p.drawString(50, y, "Fecha")
    p.drawString(120, y, "Descripción Actividad")
    p.drawString(410, y, "Horas")
    p.drawString(460, y, "Estado")
    return y - 20


def generar_pdf_practica(
    estudiante_nombre: str,
    empresa: str,
    tutor_nombre: str,
    seguimientos: list,
    horas_acumuladas: float = 0.0,
    horas_requeridas: int = 0,
    programa: str = "",
    supervisor_nombre: str = "Sin asignar",
):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    def nueva_pagina_con_tabla(y_inicial: float) -> float:
        p.showPage()
        p.setFont("Helvetica-Bold", 10)
        p.drawString(50, height - 50, "SIPGA — Reporte de Seguimientos (continuación)")
        return _dibujar_encabezado_tabla(p, height - 75)

    p.setFont("Helvetica-Bold", 14)
    p.drawCentredString(width / 2, height - 50, "CORPORACION UNIVERSITARIA RAFAEL NUÑEZ")
    p.setFont("Helvetica", 12)
    p.drawCentredString(
        width / 2,
        height - 70,
        "SIPGA: Sistema de Información para el Seguimiento de Prácticas",
    )

    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, height - 100, f"ESTUDIANTE: {estudiante_nombre or 'Desconocido'}")
    p.drawString(50, height - 115, f"EMPRESA: {empresa or 'Sin asignar'}")
    p.drawString(50, height - 130, f"SUPERVISOR: {supervisor_nombre or 'Sin asignar'}")
    p.drawString(300, height - 100, f"TUTOR: {tutor_nombre or 'Sin asignar'}")
    p.drawString(
        300,
        height - 115,
        f"FECHA REPORTE: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    )
    if programa:
        p.drawString(300, height - 130, f"PROGRAMA: {programa}")
    linea_y = height - 145
    p.line(50, linea_y, 550, linea_y)

    y = linea_y - 25
    y = _dibujar_encabezado_tabla(p, y)
    p.setFont("Helvetica", 9)
    total_horas_aprobadas = 0.0
    seguimientos_ordenados = sorted(
        seguimientos,
        key=lambda s: s.fecha_actividad or datetime.min,
    )

    if not seguimientos_ordenados:
        p.drawString(50, y, "Sin seguimientos registrados para esta práctica.")
        y -= 30
    else:
        for s in seguimientos_ordenados:
            if y < 100:
                y = nueva_pagina_con_tabla(y)

            fecha_str = _fecha_label(s.fecha_actividad)
            descripcion = (s.descripcion or "").strip() or "—"
            desc = (descripcion[:55] + "..") if len(descripcion) > 55 else descripcion
            horas = float(s.horas_realizadas or 0)
            estado_str = _estado_label(s.estado)

            p.drawString(50, y, fecha_str)
            p.drawString(120, y, desc)
            p.drawString(410, y, f"{horas:g}h")
            p.drawString(460, y, estado_str)

            if "APROBADO" in estado_str or "VALIDADO" in estado_str:
                total_horas_aprobadas += horas

            y -= 20

    p.line(50, y, 550, y)
    y -= 20
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y, f"HORAS APROBADAS EN REPORTE: {total_horas_aprobadas:g}h")
    y -= 15
    total_oficial = float(horas_acumuladas or total_horas_aprobadas)
    p.drawString(50, y, f"HORAS ACUMULADAS (SISTEMA): {total_oficial:g}h")
    if horas_requeridas:
        y -= 15
        p.drawString(50, y, f"HORAS REQUERIDAS: {horas_requeridas}h")

    p.save()
    buffer.seek(0)
    return buffer


def generar_certificado_pdf(
    estudiante_nombre: str,
    estudiante_correo: str,
    programa: str,
    empresa: str,
    tutor_nombre: str,
    horas_acumuladas: float,
    calificacion: float,
    codigo_seguridad: str,
    url_verificacion: str,
    supervisor_nombre: str = "Supervisor de Empresa",
) -> BytesIO:
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics import renderPDF
    from reportlab.lib.colors import HexColor
    
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # 1. Dibujar Marco Estético de Diploma
    p.setStrokeColor(HexColor("#0d1b2e")) # Color azul oscuro institucional
    p.setLineWidth(3)
    p.rect(30, 30, width - 60, height - 60)
    
    p.setStrokeColor(HexColor("#d97706")) # Borde interno dorado
    p.setLineWidth(1)
    p.rect(35, 35, width - 70, height - 70)
    
    # 2. Encabezado Institucional
    p.setFont("Helvetica-Bold", 18)
    p.setFillColor(HexColor("#0d1b2e"))
    p.drawCentredString(width / 2, height - 100, "CORPORACIÓN UNIVERSITARIA RAFAEL NÚÑEZ")
    
    p.setFont("Helvetica", 10)
    p.setFillColor(HexColor("#64748b"))
    p.drawCentredString(width / 2, height - 120, "DEPARTAMENTO DE PRÁCTICAS ACADÉMICAS Y PROYECCIÓN SOCIAL")
    
    # Línea divisoria
    p.setStrokeColor(HexColor("#cbd5e1"))
    p.setLineWidth(1)
    p.line(100, height - 140, width - 100, height - 140)
    
    # 3. Título del Certificado
    p.setFont("Helvetica-Bold", 16)
    p.setFillColor(HexColor("#1e293b"))
    p.drawCentredString(width / 2, height - 180, "CERTIFICADO DE FINALIZACIÓN DE PRÁCTICA")
    
    p.setFont("Helvetica-Oblique", 11)
    p.setFillColor(HexColor("#475569"))
    p.drawCentredString(width / 2, height - 200, "Hace constar oficialmente que:")
    
    # 4. Nombre del Estudiante (Grande)
    p.setFont("Helvetica-Bold", 20)
    p.setFillColor(HexColor("#0f172a"))
    p.drawCentredString(width / 2, height - 240, estudiante_nombre.upper())
    
    # 5. Cuerpo del Texto
    p.setFont("Helvetica", 11)
    p.setFillColor(HexColor("#334155"))
    
    texto_linea1 = f"Identificado(a) con correo electrónico {estudiante_correo}, adscrito(a) al programa"
    texto_linea2 = f"académico de {programa or 'Programa General'}, ha completado satisfactoriamente"
    texto_linea3 = f"sus prácticas profesionales en la organización o empresa cooperante:"
    
    p.drawCentredString(width / 2, height - 280, texto_linea1)
    p.drawCentredString(width / 2, height - 298, texto_linea2)
    p.drawCentredString(width / 2, height - 316, texto_linea3)
    
    # Nombre de la Empresa (Destacado)
    p.setFont("Helvetica-Bold", 13)
    p.setFillColor(HexColor("#1d4ed8"))
    p.drawCentredString(width / 2, height - 350, empresa.upper())
    
    # Detalles técnicos
    p.setFont("Helvetica", 11)
    p.setFillColor(HexColor("#334155"))
    texto_linea4 = f"cumpliendo exitosamente un total de {horas_acumuladas:g} horas reglamentarias bajo"
    texto_linea5 = f"la tutoría del docente {tutor_nombre or 'Sin asignar'} y la supervisión en empresa de"
    texto_linea6 = f"{supervisor_nombre or 'Sin asignar'}, obteniendo una Calificación Final de:"
    
    p.drawCentredString(width / 2, height - 385, texto_linea4)
    p.drawCentredString(width / 2, height - 403, texto_linea5)
    p.drawCentredString(width / 2, height - 421, texto_linea6)
    
    # Calificación (Grande)
    p.setFont("Helvetica-Bold", 16)
    p.setFillColor(HexColor("#16a34a"))
    p.drawCentredString(width / 2, height - 455, f"{calificacion:.2f} / 5.00")
    
    # Fecha de expedición
    hoy = datetime.now()
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    fecha_exp = f"Dado en la ciudad de Cartagena de Indias, a los {hoy.day} días del mes de {meses[hoy.month - 1]} de {hoy.year}."
    p.setFont("Helvetica-Oblique", 9)
    p.setFillColor(HexColor("#64748b"))
    p.drawCentredString(width / 2, height - 500, fecha_exp)
    
    # 6. Código de Seguridad e Información de QR
    p.setFont("Helvetica-Bold", 9)
    p.setFillColor(HexColor("#0f172a"))
    p.drawString(60, 150, "CÓDIGO DE VALIDACIÓN:")
    p.setFont("Helvetica", 9)
    p.setFillColor(HexColor("#475569"))
    p.drawString(60, 135, codigo_seguridad)
    p.setFont("Helvetica-Oblique", 8)
    p.drawString(60, 120, "Este documento está firmado digitalmente")
    p.drawString(60, 110, "y puede ser verificado escaneando el QR.")
    
    # 7. QR Code Widget
    try:
        qr_code = QrCodeWidget(value=url_verificacion)
        bounds = qr_code.getBounds()
        qr_w = bounds[2] - bounds[0]
        qr_h = bounds[3] - bounds[1]
        d = Drawing(80, 80, transform=[80./qr_w, 0, 0, 80./qr_h, 0, 0])
        d.add(qr_code)
        renderPDF.draw(d, p, width - 140, 90)
    except Exception as e:
        pass
        
    # 8. Firmas (Tres Firmas)
    p.setStrokeColor(HexColor("#94a3b8"))
    p.setLineWidth(1)
    p.line(60, 220, 180, 220)
    p.line(width/2 - 60, 220, width/2 + 60, 220)
    p.line(width - 180, 220, width - 60, 220)
    
    p.setFont("Helvetica-Bold", 8)
    p.setFillColor(HexColor("#1e293b"))
    p.drawCentredString(120, 208, "COORDINADOR DE PRÁCTICAS")
    p.drawCentredString(width/2, 208, "SUPERVISOR DE EMPRESA")
    p.drawCentredString(width - 120, 208, "TUTOR ACADÉMICO")
    
    p.setFont("Helvetica", 7.5)
    p.setFillColor(HexColor("#64748b"))
    p.drawCentredString(120, 196, "Corporación Univ. Rafael Núñez")
    p.drawCentredString(width/2, 196, "Representante Cooperante")
    p.drawCentredString(width - 120, 196, "Docente Evaluador")
    
    p.save()
    buffer.seek(0)
    return buffer
