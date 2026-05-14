import pytest
import models
from fastapi import status

def test_crear_usuario(client, db):
    # Creamos un coordinador directamente en la DB para autorizar la petición
    import auth
    admin = models.Usuario(
        nombre="Admin Test",
        correo="admin@test.com",
        password_hash=auth.hash_password("adminpass"),
        rol="coordinador"
    )
    db.add(admin)
    db.commit()

    # Login como admin
    login_res = client.post(
        "/api/v1/auth/token",
        data={"username": "admin@test.com", "password": "adminpass"}
    )
    token = login_res.json()["access_token"]

    # Intentamos crear el usuario con el token del admin
    response = client.post(
        "/api/v1/usuarios/",
        json={
            "nombre": "Usuario Test",
            "correo": "test@example.com",
            "password": "password123",
            "rol": "estudiante",
            "programa_academico": "Ingeniería"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["correo"] == "test@example.com"

def test_login_exitoso(client, db):
    # Creamos el usuario directamente en la DB para el test de login
    import auth
    user = models.Usuario(
        nombre="Login Test",
        correo="login@example.com",
        password_hash=auth.hash_password("secretpassword"),
        rol="estudiante"
    )
    db.add(user)
    db.commit()
    
    # Intentamos login
    response = client.post(
        "/api/v1/auth/token",
        data={
            "username": "login@example.com",
            "password": "secretpassword"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_fallido(client):
    response = client.post(
        "/api/v1/auth/token",
        data={
            "username": "wrong@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
