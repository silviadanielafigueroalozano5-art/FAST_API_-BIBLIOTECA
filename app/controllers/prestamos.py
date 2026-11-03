"""CONTROLLER - Lógica de negocio de Préstamos (Fase 5).

El ESTADO se CALCULA, no se guarda:
- devuelto -> fecha_devolucion tiene valor
- vencido  -> sin devolver y fecha_limite < hoy
- activo   -> sin devolver y fecha_limite >= hoy

Reglas al crear (validadas también en el schema):
- fecha_prestamo no puede ser futura.
- dias entre 1 y 30 (por defecto 14); fecha_limite = prestamo + dias.
- libro y socio deben existir; socio ACTIVO.
- libro con ejemplares libres (ejemplares - préstamos sin devolver).
- socio sin 3 préstamos activos simultáneos.
- socio sin multas pendientes.

Reglas al devolver:
- no se puede devolver dos veces.
- multa = días de retraso (devolución - límite) × TASA_MULTA_DIARIA.
"""
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.controllers.socios import obtener_socio
from app.core.config import get_settings
from app.core.exceptions import (
    Conflicto,
    NoEncontrado,
    ReglaNegocio,
)
from app.models.autor import Libro
from app.models.prestamo import Prestamo

# Límites de la fase 5
DIAS_PRESTAMO_DEFAULT = 14  # R8: días por defecto si el cliente no envía 'dias'
# Tasa de multa (R10): 0,50 por día de retraso
TASA_MULTA_DIARIA = Decimal(get_settings().tasa_multa_diaria)


# ---------- CÁLCULO DE ESTADO Y MULTA ----------


def estado_de(prestamo: Prestamo, hoy: date | None = None) -> str:
    """Estado CALCULADO a partir de las fechas (no hay columna 'devuelto')."""
    hoy = hoy or date.today()
    if prestamo.fecha_devolucion is not None:
        return "devuelto"
    return "vencido" if prestamo.fecha_limite < hoy else "activo"


def calcular_multa(prestamo: Prestamo) -> Decimal:
    """Multa = días de retraso × tasa diaria (0 si no hay retraso)."""
    if prestamo.fecha_devolucion is None:
        return Decimal("0")
    retraso = (prestamo.fecha_devolucion - prestamo.fecha_limite).days
    return TASA_MULTA_DIARIA * retraso if retraso > 0 else Decimal("0")


def multas_pendientes(db: Session, socio_id: int) -> Decimal:
    """Multa PENDIENTE del socio:
    - columnas `multa` de préstamos devueltos con `multa_pagada=False`
      (devoluciones con retraso aún sin pagar),
    - más los días de retraso de préstamos VENCIDOS sin devolver.
    """
    hoy = date.today()
    devueltas = db.scalar(
        select(func.coalesce(func.sum(Prestamo.multa), 0)).where(
            Prestamo.socio_id == socio_id,
            Prestamo.fecha_devolucion.is_not(None),
            Prestamo.multa_pagada.is_(False),
        )
    )
    vencidos = db.scalars(
        select(Prestamo).where(
            Prestamo.socio_id == socio_id,
            Prestamo.fecha_devolucion.is_(None),
            Prestamo.fecha_limite < hoy,
        )
    ).all()
    total = Decimal(devueltas) + sum((hoy - p.fecha_limite).days for p in vencidos) * TASA_MULTA_DIARIA
    return max(total, Decimal("0"))


def ejemplares_disponibles(db: Session, libro: Libro) -> int:
    """Campo calculado: ejemplares - préstamos sin devolver."""
    prestamos_sin_devolver = db.scalar(
        select(func.count(Prestamo.id)).where(
            Prestamo.libro_id == libro.id, Prestamo.fecha_devolucion.is_(None)
        )
    )
    return libro.ejemplares - prestamos_sin_devolver


# ---------- CREAR / CONSULTAR ----------


def crear_prestamo(
    db: Session, datos, registrado_por_id: int | None = None
) -> Prestamo:
    """Reglas R1-R8 comprobadas en ESTE ORDEN (tabla de la fase 5).

    R8: fecha_limite = fecha_prestamo + dias (se calcula, no se valida).
    """
    # R1: el socio existe -> 404
    socio = obtener_socio(db, datos.socio_id)
    # R2: el libro existe -> 404
    libro = db.get(Libro, datos.libro_id)
    if not libro:
        raise NoEncontrado(f"No existe el libro con id={datos.libro_id}")
    # R3: el socio está activo -> 422 "El socio no está activo"
    if not socio.activo:
        raise ReglaNegocio("El socio no está activo")
    # R4: el socio no tiene préstamos vencidos
    #     -> 422 "El socio tiene préstamos vencidos"
    hoy = date.today()
    vencidos = db.scalar(
        select(func.count(Prestamo.id)).where(
            Prestamo.socio_id == socio.id,
            Prestamo.fecha_devolucion.is_(None),
            Prestamo.fecha_limite < hoy,
        )
    )
    if vencidos:
        raise ReglaNegocio("El socio tiene préstamos vencidos")
    if multas_pendientes(db, socio.id) > 0:
        raise ReglaNegocio("El socio tiene multas pendientes")
    # R5: menos de 3 préstamos sin devolver -> 422 "Máximo de 3 préstamos"
    sin_devolver = db.scalar(
        select(func.count(Prestamo.id)).where(
            Prestamo.socio_id == socio.id, Prestamo.fecha_devolucion.is_(None)
        )
    )
    if sin_devolver >= 3:
        raise ReglaNegocio("Máximo de 3 préstamos")
    # R6: no tiene YA ese mismo libro sin devolver -> 409
    duplicado = db.scalar(
        select(Prestamo.id).where(
            Prestamo.socio_id == socio.id,
            Prestamo.libro_id == datos.libro_id,
            Prestamo.fecha_devolucion.is_(None),
        )
    )
    if duplicado:
        raise Conflicto(
            f"El socio ya tiene este libro prestado (préstamo id={duplicado})"
        )
    # R7: el libro tiene ejemplares disponibles
    #     -> 422 "No hay ejemplares disponibles"
    if ejemplares_disponibles(db, libro) <= 0:
        raise ReglaNegocio("No hay ejemplares disponibles")

    # R8: fecha_limite = fecha_prestamo + dias (por defecto HOY)
    dias = getattr(datos, "dias", DIAS_PRESTAMO_DEFAULT)
    fecha_prestamo = datos.fecha_prestamo or date.today()
    prestamo = Prestamo(
        **datos.model_dump(exclude={"dias", "fecha_prestamo"}),
        fecha_prestamo=fecha_prestamo,
        fecha_limite=fecha_prestamo + timedelta(days=dias),
        registrado_por_id=registrado_por_id,
    )
    db.add(prestamo)
    db.commit()
    db.refresh(prestamo)
    return prestamo


def listar_prestamos(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    estado: str | None = None,
    socio_id: int | None = None,
    libro_id: int | None = None,
    propio_socio_id: int | None = None,
) -> tuple[list[Prestamo], int]:
    """Filtros combinables: ?estado=activo|vencido|devuelto, ?socio_id=, ?libro_id="""
    consulta = select(Prestamo)
    hoy = date.today()
    if estado == "devuelto":
        consulta = consulta.where(Prestamo.fecha_devolucion.is_not(None))
    elif estado == "activo":
        consulta = consulta.where(
            Prestamo.fecha_devolucion.is_(None), Prestamo.fecha_limite >= hoy
        )
    elif estado == "vencido":
        consulta = consulta.where(
            Prestamo.fecha_devolucion.is_(None), Prestamo.fecha_limite < hoy
        )
    elif estado is not None:
        raise ReglaNegocio(
            f"Estado '{estado}' no válido. Usa: activo, vencido o devuelto"
        )
    if socio_id:
        consulta = consulta.where(Prestamo.socio_id == socio_id)
    if libro_id:
        consulta = consulta.where(Prestamo.libro_id == libro_id)
    if propio_socio_id is not None:
        consulta = consulta.where(Prestamo.socio_id == propio_socio_id)
    total = db.scalar(
        select(func.count()).select_from(consulta.order_by(None).subquery())
    ) or 0
    consulta = consulta.order_by(Prestamo.fecha_prestamo.desc())
    items = list(db.scalars(consulta.offset(skip).limit(limit)).all())
    return items, total


def obtener_prestamo(db: Session, prestamo_id: int) -> Prestamo:
    prestamo = db.get(Prestamo, prestamo_id)
    if not prestamo:
        raise NoEncontrado(f"Préstamo con id={prestamo_id} no encontrado")
    return prestamo


# ---------- DEVOLUCIÓN ----------


def devolver_prestamo(
    db: Session, prestamo_id: int, fecha_devolucion: date | None = None
) -> Prestamo:
    """Reglas R9-R10 (tabla de la fase 5):

    - 404 si el préstamo no existe (lo valida obtener_prestamo).
    - R9a: no devuelto antes -> 409.
    - R9b: la fecha de devolución no puede ser anterior al préstamo -> 422.
    - R10: multa = días de retraso (devolución - fecha_limite) × 0,50.
    """
    prestamo = obtener_prestamo(db, prestamo_id)
    # R9a: ya devuelto -> 409
    if prestamo.fecha_devolucion is not None:
        raise Conflicto("Este préstamo ya fue devuelto")
    # Si no llega fecha en el body, se usa hoy
    fecha = fecha_devolucion or date.today()
    # R9b: la fecha no puede ser anterior al préstamo -> 422
    if fecha < prestamo.fecha_prestamo:
        raise ReglaNegocio(
            "La fecha de devolución no puede ser anterior a la del préstamo"
        )

    prestamo.fecha_devolucion = fecha
    # R10: multa = días de retraso × 0,50
    prestamo.multa = calcular_multa(prestamo)
    # Si hay multa queda PENDIENTE de pago (False); sin multa, pagada
    prestamo.multa_pagada = not (prestamo.multa > 0)
    db.commit()
    db.refresh(prestamo)
    return prestamo


def pagar_multa(db: Session, prestamo_id: int) -> Prestamo:
    prestamo = obtener_prestamo(db, prestamo_id)
    if prestamo.multa <= 0:
        raise Conflicto("Este préstamo no tiene una multa pendiente")
    if prestamo.multa_pagada:
        raise Conflicto("La multa de este préstamo ya fue pagada")
    prestamo.multa_pagada = True
    db.commit()
    db.refresh(prestamo)
    return prestamo
