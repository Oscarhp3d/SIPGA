import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from datetime import datetime, timezone, timedelta
from pydantic import ValidationError
from schemas import (
    UsuarioCreate,
    EmpresaBase,
    PracticaBase,
    SeguimientoBase
)

def test_usuario_create():
    print("Testing UsuarioCreate...")
    try:
        UsuarioCreate(nombre="A", correo="invalid", password="short")
        print("FAIL: UsuarioCreate allowed invalid data")
    except ValidationError as e:
        print("PASS: UsuarioCreate validations working. Errors caught:")
        for err in e.errors():
            print(f"  - {err['loc'][0]}: {err['msg']}")

def test_empresa_base():
    print("\nTesting EmpresaBase...")
    try:
        EmpresaBase(nombre="A", nit="123", direccion="123")
        print("FAIL: EmpresaBase allowed invalid data")
    except ValidationError as e:
        print("PASS: EmpresaBase validations working. Errors caught:")
        for err in e.errors():
            print(f"  - {err['loc'][0]}: {err['msg']}")

def test_practica_fechas():
    print("\nTesting PracticaBase dates...")
    try:
        # fecha_fin < fecha_inicio
        PracticaBase(
            estudiante_id="123",
            empresa_id=1,
            fecha_inicio=datetime(2026, 5, 1, tzinfo=timezone.utc),
            fecha_fin=datetime(2026, 4, 1, tzinfo=timezone.utc)
        )
        print("FAIL: PracticaBase allowed fecha_fin < fecha_inicio")
    except ValidationError as e:
        print("PASS: PracticaBase date validation working. Error caught:")
        for err in e.errors():
            print(f"  - {err['msg']}")

def test_seguimiento_fecha():
    print("\nTesting SeguimientoBase dates...")
    now = datetime.now(timezone.utc)
    
    # Test future date
    future_date = now + timedelta(days=1)
    try:
        SeguimientoBase(
            practica_id="123",
            descripcion="Descripción de prueba lo suficientemente larga",
            horas_realizadas=5,
            fecha_actividad=future_date
        )
        print("FAIL: SeguimientoBase allowed future date")
    except ValidationError as e:
        print("PASS: SeguimientoBase future date validation working. Error caught:")
        for err in e.errors():
            print(f"  - {err['msg']}")
            
    # Test past year
    past_year_date = now.replace(year=now.year - 1)
    try:
        SeguimientoBase(
            practica_id="123",
            descripcion="Descripción de prueba lo suficientemente larga",
            horas_realizadas=5,
            fecha_actividad=past_year_date
        )
        print("FAIL: SeguimientoBase allowed past year date")
    except ValidationError as e:
        print("PASS: SeguimientoBase past year validation working. Error caught:")
        for err in e.errors():
            print(f"  - {err['msg']}")

if __name__ == "__main__":
    test_usuario_create()
    test_empresa_base()
    test_practica_fechas()
    test_seguimiento_fecha()
