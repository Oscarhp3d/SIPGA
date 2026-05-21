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
    p.drawString(300, height - 100, f"TUTOR: {tutor_nombre or 'Sin asignar'}")
    p.drawString(
        300,
        height - 115,
        f"FECHA REPORTE: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    )
    if programa:
        p.drawString(50, height - 130, f"PROGRAMA: {programa}")
        linea_y = height - 145
    else:
        linea_y = height - 130
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

            if estado_str == "APROBADO":
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
