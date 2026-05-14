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
    res_emp = client.post("/api/v1/empresas/", json={"nombre": "Empresa Test", "nit": "123", "direccion": "Calle 1"}, headers={"Authorization": f"Bearer {token}"})
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
    # Nota: En la lógica actual, el supervisor es quien suele sumar horas si está configurado, 
    # pero vamos a verificar según la implementación de crud.py
    # En crud.py, validar_seguimiento suma horas si el revisor es supervisor o coordinador.
