import pytest
import models
from fastapi import status

def test_flujo_completo_practica(client, db):
    # 1. Crear Coordinador, Tutor y Estudiante
    import auth
    admin = models.Usuario(nombre="Admin", correo="admin@test.com", password_hash=auth.hash_password("pass"), rol="coordinador")
    tutor = models.Usuario(nombre="Tutor", correo="tutor@test.com", password_hash=auth.hash_password("pass"), rol="tutor", programa_academico="Sistemas")
    est = models.Usuario(nombre="Est", correo="est@test.com", password_hash=auth.hash_password("pass"), rol="estudiante", programa_academico="Sistemas")
    db.add_all([admin, tutor, est])
    db.commit()

    # Login Admin
    res_login = client.post("/api/v1/auth/token", data={"username": "admin@test.com", "password": "pass"})
    token = res_login.json()["access_token"]

    # 2. Crear Empresa
    res_emp = client.post("/api/v1/empresas/", json={"nombre": "Empresa Test", "nit": "900.123.456-1", "direccion": "Calle 1"}, headers={"Authorization": f"Bearer {token}"})
    emp_id = res_emp.json()["id"]

    # 3. Crear Práctica
    res_prac = client.post("/api/v1/practicas/", json={
        "estudiante_id": est.id,
        "tutor_id": tutor.id,
        "empresa_id": emp_id,
        "horas_totales_requeridas": 100
    }, headers={"Authorization": f"Bearer {token}"})
    assert res_prac.status_code == 201
    prac_id = res_prac.json()["id"]

    # 4. Estudiante registra seguimiento (Login Estudiante)
    res_log_est = client.post("/api/v1/auth/token", data={"username": "est@test.com", "password": "pass"})
    token_est = res_log_est.json()["access_token"]
    
    res_seg = client.post("/api/v1/seguimientos/", json={
        "practica_id": prac_id,
        "descripcion": "Actividad de prueba con mas de quince caracteres",
        "horas_realizadas": 8.0
    }, headers={"Authorization": f"Bearer {token_est}"})
    assert res_seg.status_code == 201
    seg_id = res_seg.json()["id"]

    # 5. Tutor valida seguimiento (Login Tutor)
    res_log_tut = client.post("/api/v1/auth/token", data={"username": "tutor@test.com", "password": "pass"})
    token_tut = res_log_tut.json()["access_token"]

    res_val = client.patch(f"/api/v1/seguimientos/{seg_id}/validar", json={
        "estado": "aprobado",
        "observaciones": "Buen trabajo"
    }, headers={"Authorization": f"Bearer {token_tut}"})
    assert res_val.status_code == 200
    assert res_val.json()["estado"] == "aprobado"
    
    # 6. Verificar horas acumuladas en la práctica
    res_check = client.get(f"/api/v1/practicas/{prac_id}", headers={"Authorization": f"Bearer {token}"})
    assert res_check.status_code == 200
    # En este test, el tutor valida el seguimiento. 
    # Según crud.py, la validación del tutor suma horas si es el revisor final o coordinador.
    # En este flujo, el tutor aprueba. Verifiquemos si crud.py suma en este caso.
    assert res_check.json()["horas_acumuladas"] == 8.0

    # 7. Generar reporte PDF (coordinador y estudiante)
    res_pdf_admin = client.get(
        f"/api/v1/practicas/{prac_id}/reporte-pdf",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_pdf_admin.status_code == 200
    assert res_pdf_admin.headers["content-type"] == "application/pdf"
    assert res_pdf_admin.content[:4] == b"%PDF"

    res_pdf_est = client.get(
        f"/api/v1/practicas/{prac_id}/reporte-pdf",
        headers={"Authorization": f"Bearer {token_est}"},
    )
    assert res_pdf_est.status_code == 200
    assert res_pdf_est.content[:4] == b"%PDF"

    # 8. Evidencia: estudiante sube, tutor y coordinador pueden ver
    import io
    pdf_bytes = b"%PDF-1.4 test evidencia"
    res_ev = client.post(
        f"/api/v1/seguimientos/{seg_id}/subir-evidencia",
        files={"archivo": ("evidencia.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers={"Authorization": f"Bearer {token_est}"},
    )
    assert res_ev.status_code == 200

    res_ver_est = client.get(
        f"/api/v1/seguimientos/{seg_id}/evidencia",
        headers={"Authorization": f"Bearer {token_est}"},
    )
    assert res_ver_est.status_code == 200
    assert res_ver_est.content == pdf_bytes

    res_ver_tut = client.get(
        f"/api/v1/seguimientos/{seg_id}/evidencia",
        headers={"Authorization": f"Bearer {token_tut}"},
    )
    assert res_ver_tut.status_code == 200

def test_analiticas_coordinador(client, db):
    # 1. Crear Coordinador, Tutor, Estudiante y Práctica
    import auth
    admin = models.Usuario(nombre="Admin3", correo="admin3@test.com", password_hash=auth.hash_password("pass"), rol="coordinador")
    tutor = models.Usuario(nombre="Tutor3", correo="tutor3@test.com", password_hash=auth.hash_password("pass"), rol="tutor", programa_academico="Sistemas")
    est = models.Usuario(nombre="Est3", correo="est3@test.com", password_hash=auth.hash_password("pass"), rol="estudiante", programa_academico="Sistemas")
    db.add_all([admin, tutor, est])
    db.commit()

    # Crear Empresa
    empresa = models.Empresa(nombre="Empresa Test 3", nit="900.123.456-3", direccion="Calle 3")
    db.add(empresa)
    db.commit()

    # Crear Práctica
    practica = models.Practica(
        estudiante_id=est.id,
        tutor_id=tutor.id,
        empresa_id=empresa.id,
        horas_totales_requeridas=100,
        horas_acumuladas=15.0,
        estado="activa"
    )
    db.add(practica)
    db.commit()

    # Crear un seguimiento aprobado para el tutor
    seguimiento = models.Seguimiento(
        practica_id=practica.id,
        descripcion="Seguimiento analitica de prueba",
        horas_realizadas=15.0,
        estado=models.StatusEnum.aprobado,
        validado_tutor=True
    )
    db.add(seguimiento)
    db.commit()

    # Login Coordinador
    res_login = client.post("/api/v1/auth/token", data={"username": "admin3@test.com", "password": "pass"})
    token = res_login.json()["access_token"]
    
    # 2. Consultar el nuevo endpoint de analíticas
    res_an = client.get(
        "/api/v1/coordinador/analiticas",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_an.status_code == 200
    data = res_an.json()
    assert "comparativa_programas" in data
    assert "podio_practicantes" in data
    assert "desempeno_tutores" in data
    
    # Verificar comparativa de programas
    assert len(data["comparativa_programas"]) > 0
    assert data["comparativa_programas"][0]["programa"] == "Sistemas"
    assert data["comparativa_programas"][0]["total_horas_acumuladas"] == 15.0
    
    # Verificar que el podio contenga a los estudiantes con horas registradas
    assert len(data["podio_practicantes"]) > 0
    assert data["podio_practicantes"][0]["nombre"] == "Est3"
    assert data["podio_practicantes"][0]["horas_acumuladas"] == 15.0

    # Verificar desempeño de tutores
    assert len(data["desempeno_tutores"]) > 0
    assert data["desempeno_tutores"][0]["nombre"] == "Tutor3"
    assert data["desempeno_tutores"][0]["seguimientos_validados"] == 1

def test_calificaciones_reales(client, db):
    import auth
    # 1. Crear Coordinador, Tutor, Supervisor y Estudiante
    admin = models.Usuario(nombre="Admin4", correo="admin4@test.com", password_hash=auth.hash_password("pass"), rol="coordinador")
    tutor = models.Usuario(nombre="Tutor4", correo="tutor4@test.com", password_hash=auth.hash_password("pass"), rol="tutor", programa_academico="Sistemas")
    supervisor = models.Usuario(nombre="Supervisor4", correo="super4@test.com", password_hash=auth.hash_password("pass"), rol="supervisor")
    est = models.Usuario(nombre="Est4", correo="est4@test.com", password_hash=auth.hash_password("pass"), rol="estudiante", programa_academico="Sistemas")
    db.add_all([admin, tutor, supervisor, est])
    db.commit()

    # Crear Empresa
    empresa = models.Empresa(nombre="Empresa Test 4", nit="900.123.456-4", direccion="Calle 4")
    db.add(empresa)
    db.commit()

    # Crear Práctica
    practica = models.Practica(
        estudiante_id=est.id,
        tutor_id=tutor.id,
        supervisor_id=supervisor.id,
        empresa_id=empresa.id,
        horas_totales_requeridas=100,
        horas_acumuladas=0.0,
        estado="activa"
    )
    db.add(practica)
    db.commit()

    # Login Supervisor
    res_log_sup = client.post("/api/v1/auth/token", data={"username": "super4@test.com", "password": "pass"})
    token_sup = res_log_sup.json()["access_token"]

    # Login Tutor
    res_log_tut = client.post("/api/v1/auth/token", data={"username": "tutor4@test.com", "password": "pass"})
    token_tut = res_log_tut.json()["access_token"]

    # 1. Estudiante crea un seguimiento
    res_log_est = client.post("/api/v1/auth/token", data={"username": "est4@test.com", "password": "pass"})
    token_est = res_log_est.json()["access_token"]
    res_seg = client.post("/api/v1/seguimientos/", json={
        "practica_id": practica.id,
        "descripcion": "Actividad de prueba larga calificacion",
        "horas_realizadas": 8.0
    }, headers={"Authorization": f"Bearer {token_est}"})
    assert res_seg.status_code == 201
    seg_id = res_seg.json()["id"]

    # 2. Supervisor aprueba con calificacion 4.5
    res_val_sup = client.patch(f"/api/v1/seguimientos/{seg_id}/validar", json={
        "estado": "aprobado",
        "calificacion_supervisor": 4.5,
        "observaciones": "Buen trabajo del practicante"
    }, headers={"Authorization": f"Bearer {token_sup}"})
    assert res_val_sup.status_code == 200
    assert res_val_sup.json()["calificacion_supervisor"] == 4.5

    # 3. Tutor aprueba con calificacion 3.5
    res_val_tut = client.patch(f"/api/v1/seguimientos/{seg_id}/validar", json={
        "estado": "aprobado",
        "calificacion_tutor": 3.5,
        "observaciones": "Comentarios del tutor"
    }, headers={"Authorization": f"Bearer {token_tut}"})
    assert res_val_tut.status_code == 200
    assert res_val_tut.json()["calificacion_tutor"] == 3.5
    assert res_val_tut.json()["estado"] == "aprobado"

    # 4. Verificar promedio en la práctica (debería ser (4.5 + 3.5) / 2 = 4.0)
    res_prac = client.get(f"/api/v1/practicas/{practica.id}", headers={"Authorization": f"Bearer {token_tut}"})
    assert res_prac.status_code == 200
    assert res_prac.json()["calificacion"] == 4.0
