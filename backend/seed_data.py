import sys
import os

# Añadir el directorio actual al path para importar módulos locales
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
import auth
from datetime import datetime, timedelta
import random

def seed():
    db = SessionLocal()
    try:
        print("--- Iniciando Seeding del Proyecto SIPGA ---")

        # 1. Crear Empresas
        empresas_data = [
            {"nombre": "Tecnologías del Caribe S.A.S", "nit": "900.123.456-1", "direccion": "Manga, Calle 24 #12-45"},
            {"nombre": "Logística Marítima Cartagena", "nit": "800.555.777-2", "direccion": "Socorro, Av. Pedro de Heredia"},
            {"nombre": "Software Solutions Unicartagena", "nit": "901.999.000-3", "direccion": "Centro Histórico"},
        ]
        
        db_empresas = []
        for emp in empresas_data:
            existente = db.query(models.Empresa).filter(models.Empresa.nombre == emp["nombre"]).first()
            if not existente:
                nueva = models.Empresa(**emp)
                db.add(nueva)
                db_empresas.append(nueva)
                print(f"Empresa creada: {emp['nombre']}")
            else:
                db_empresas.append(existente)

        db.commit()

        # 2. Crear Usuarios (Roles: coordinador, tutor, supervisor, estudiante)
        password = auth.hash_password("admin123")
        
        usuarios_data = [
            {"nombre": "Admin Coordinador", "correo": "admin@sipga.edu.co", "rol": models.UserRole.coordinador, "programa": "Ingeniería de Sistemas"},
            {"nombre": "Dr. Julio Benitez", "correo": "jbenitez@sipga.edu.co", "rol": models.UserRole.tutor, "programa": "Ingeniería de Sistemas"},
            {"nombre": "Ing. Maria Ruiz", "correo": "mruiz@sipga.edu.co", "rol": models.UserRole.tutor, "programa": "Administración de Empresas"},
            {"nombre": "Carlos Supervisor", "correo": "carlos@empresa.com", "rol": models.UserRole.supervisor, "programa": None},
            {"nombre": "Estudiante Prueba", "correo": "estudiante@sipga.edu.co", "rol": models.UserRole.estudiante, "programa": "Ingeniería de Sistemas"},
            {"nombre": "Oscar Guerrero", "correo": "oscar@sipga.edu.co", "rol": models.UserRole.estudiante, "programa": "Ingeniería de Sistemas"},
        ]

        db_usuarios = {}
        for user in usuarios_data:
            existente = db.query(models.Usuario).filter(models.Usuario.correo == user["correo"]).first()
            if existente:
                existente.password_hash = password
                existente.rol = user["rol"]
                existente.nombre = user["nombre"]
                existente.programa_academico = user["programa"]
                db_usuarios[user["correo"]] = existente
                print(f"Usuario actualizado: {user['nombre']}")
            else:
                nuevo = models.Usuario(
                    nombre=user["nombre"],
                    correo=user["correo"],
                    password_hash=password,
                    rol=user["rol"],
                    programa_academico=user["programa"]
                )
                db.add(nuevo)
                db_usuarios[user["correo"]] = nuevo
                print(f"Usuario creado: {user['nombre']} ({user['rol']})")

        db.commit()

        # 3. Crear Asignación de Tutor a Programa
        tutor_is = db_usuarios["jbenitez@sipga.edu.co"]
        asig_existente = db.query(models.AsignacionTutor).filter(
            models.AsignacionTutor.tutor_id == tutor_is.id,
            models.AsignacionTutor.programa_academico == "Ingeniería de Sistemas"
        ).first()
        
        if not asig_existente:
            asig = models.AsignacionTutor(
                tutor_id=tutor_is.id,
                programa_academico="Ingeniería de Sistemas",
                activa=True
            )
            db.add(asig)
            print("Asignación de tutor a programa creada.")

        # 4. Crear Prácticas
        est1 = db_usuarios["estudiante@sipga.edu.co"]
        est2 = db_usuarios["oscar@sipga.edu.co"]
        tutor = db_usuarios["jbenitez@sipga.edu.co"]
        supervisor = db_usuarios["carlos@empresa.com"]
        empresa = db_empresas[0]

        practicas_data = [
            {"estudiante_id": est1.id, "tutor_id": tutor.id, "emp_id": empresa.id, "horas": 320},
            {"estudiante_id": est2.id, "tutor_id": tutor.id, "emp_id": empresa.id, "horas": 320},
        ]

        db_practicas = []
        for p in practicas_data:
            existente = db.query(models.Practica).filter(models.Practica.estudiante_id == p["estudiante_id"]).first()
            if not existente:
                nueva = models.Practica(
                    estudiante_id=p["estudiante_id"],
                    tutor_id=p["tutor_id"],
                    supervisor_id=supervisor.id,
                    empresa_id=p["emp_id"],
                    horas_totales_requeridas=p["horas"],
                    fecha_inicio=datetime.now() - timedelta(days=30),
                    fecha_fin=datetime.now() + timedelta(days=60),
                    estado="activa"
                )
                db.add(nueva)
                db_practicas.append(nueva)
                print(f"Práctica creada para estudiante ID: {p['estudiante_id']}")
            else:
                db_practicas.append(existente)
        
        db.commit()

        # 5. Crear Seguimientos (Logs de Horas)
        descripciones = [
            "Análisis de requisitos del sistema",
            "Diseño de la base de datos relacional",
            "Implementación de endpoints de autenticación",
            "Corrección de errores en el frontend",
            "Pruebas de integración con la API",
            "Documentación técnica de la arquitectura"
        ]

        for p in db_practicas:
            # Crear 5 seguimientos para cada práctica
            for i in range(5):
                fecha = datetime.now() - timedelta(days=random.randint(1, 20))
                existente = db.query(models.Seguimiento).filter(
                    models.Seguimiento.practica_id == p.id,
                    models.Seguimiento.fecha_actividad == fecha
                ).first()
                
                if not existente:
                    horas = random.choice([4.0, 6.0, 8.0])
                    estado = random.choice([models.StatusEnum.aprobado, models.StatusEnum.enviado])
                    
                    seg = models.Seguimiento(
                        practica_id=p.id,
                        descripcion=random.choice(descripciones),
                        horas_realizadas=horas,
                        fecha_actividad=fecha,
                        estado=estado,
                        validado_tutor=(estado == models.StatusEnum.aprobado)
                    )
                    db.add(seg)
                    
                    # Si está aprobado, sumar a la práctica
                    if estado == models.StatusEnum.aprobado:
                        p.horas_acumuladas = (p.horas_acumuladas or 0) + horas
            
            print(f"Seguimientos creados para práctica {p.id}")

        db.commit()
        print("--- Seeding completado exitosamente ---")

    except Exception as e:
        db.rollback()
        print(f"Error durante el seeding: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
