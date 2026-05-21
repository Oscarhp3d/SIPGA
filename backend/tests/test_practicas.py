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
