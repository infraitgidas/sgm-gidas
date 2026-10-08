"""Modelo del movimiento financiero que reemplazará a la erogación histórica."""

from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import validates

from extension import db
from modules.shared.exceptions import ValidationError
from modules.shared.models.audit_mixin import AuditMixin


def validar_monto_financiero(value) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ValidationError("Ingrese un monto mayor que cero.")
    try:
        monto = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValidationError("Ingrese un monto numérico válido.") from None
    if not monto.is_finite() or monto <= 0 or monto.as_tuple().exponent < -2:
        raise ValidationError("Ingrese un monto positivo con hasta dos decimales.")
    if monto >= Decimal("10000000000000000"):
        raise ValidationError("El monto excede el máximo permitido.")
    return monto


class CategoriaErogacion(db.Model, AuditMixin):
    __tablename__ = "categoria_erogacion"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    codigo = db.Column(db.String(20), nullable=False, unique=True)
    nombre = db.Column(db.String(100), nullable=False)
    movimientos = db.relationship("MovimientoFinanciero", back_populates="categoria_erogacion")

    def serialize(self):
        return self.to_dict()


class MovimientoFinanciero(db.Model, AuditMixin):
    __tablename__ = "movimiento_financiero"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    grupo_utn_id = db.Column(db.Integer, db.ForeignKey("grupo_utn.id"), nullable=False)
    numero_movimiento = db.Column(db.Integer, nullable=False)
    fecha = db.Column(db.Date, default=date.today, nullable=False)
    tipo_movimiento = db.Column(db.String(7), nullable=False)
    monto = db.Column(db.Numeric(18, 2, asdecimal=True), nullable=False)
    moneda = db.Column(db.String(3), nullable=False, default="ARS")
    tipo_cambio_id = db.Column(db.Integer, db.ForeignKey("tipo_cambio.id"), nullable=True)
    tipo_cambio_aplicado = db.Column(db.Numeric(18, 6, asdecimal=True), nullable=True)
    monto_equivalente_ars = db.Column(db.Numeric(24, 2, asdecimal=True), nullable=True)
    fuente_financiamiento_id = db.Column(
        db.Integer, db.ForeignKey("fuente_financiamiento.id"), nullable=False
    )
    categoria_erogacion_id = db.Column(
        db.Integer, db.ForeignKey("categoria_erogacion.id"), nullable=True
    )
    equipamiento_id = db.Column(
        db.Integer, db.ForeignKey("equipamiento_grupo.id"), nullable=True
    )

    grupo_utn = db.relationship("GrupoInvestigacionUtn")
    fuente_financiamiento = db.relationship("FuenteFinanciamiento")
    categoria_erogacion = db.relationship("CategoriaErogacion", back_populates="movimientos")
    equipamiento = db.relationship("Equipamiento")
    tipo_cambio = db.relationship("TipoCambio")

    __table_args__ = (
        db.UniqueConstraint(
            "grupo_utn_id", "numero_movimiento", name="uq_movimiento_numero_grupo"
        ),
        db.UniqueConstraint("equipamiento_id", name="uq_movimiento_equipamiento"),
        db.CheckConstraint(
            "tipo_movimiento IN ('INGRESO', 'EGRESO')", name="ck_movimiento_tipo"
        ),
        db.CheckConstraint("monto > 0", name="ck_movimiento_monto_positivo"),
        db.CheckConstraint("moneda IN ('ARS', 'USD')", name="ck_movimiento_moneda"),
        db.CheckConstraint(
            "(moneda = 'ARS' AND tipo_cambio_id IS NULL AND tipo_cambio_aplicado IS NULL) OR "
            "(moneda = 'USD' AND tipo_cambio_id IS NOT NULL AND tipo_cambio_aplicado IS NOT NULL "
            "AND tipo_cambio_aplicado > 0 AND monto_equivalente_ars IS NOT NULL "
            "AND monto_equivalente_ars > 0)",
            name="ck_movimiento_tipo_cambio",
        ),
        db.CheckConstraint("numero_movimiento > 0", name="ck_movimiento_numero_positivo"),
        db.CheckConstraint(
            "fuente_financiamiento_id IS NOT NULL AND "
            "((tipo_movimiento = 'INGRESO' AND categoria_erogacion_id IS NULL "
            "AND equipamiento_id IS NULL) OR "
            "(tipo_movimiento = 'EGRESO' AND categoria_erogacion_id IS NOT NULL))",
            name="ck_movimiento_relacion_tipo",
        ),
    )

    @validates("tipo_movimiento")
    def validar_tipo_movimiento(self, _key, value):
        if value not in {"INGRESO", "EGRESO"}:
            raise ValidationError("Seleccione ingreso o egreso.")
        return value

    @validates("moneda")
    def validar_moneda(self, _key, value):
        if value not in {"ARS", "USD"}:
            raise ValidationError("Seleccione una moneda válida.")
        return value

    @validates("monto")
    def validar_monto(self, _key, value):
        return validar_monto_financiero(value)

    @validates("numero_movimiento")
    def validar_numero_movimiento(self, _key, value):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValidationError("El número de movimiento debe ser positivo.")
        return value

    def serialize(self):
        data = self.to_dict()
        data["monto"] = str(self.monto)
        data["tipo_cambio_aplicado"] = str(self.tipo_cambio_aplicado) if self.tipo_cambio_aplicado is not None else None
        data["monto_equivalente_ars"] = str(self.monto_equivalente_ars) if self.monto_equivalente_ars is not None else None
        data["tipo_cambio"] = self.tipo_cambio.serialize() if self.tipo_cambio else None
        data["grupo"] = (
            {"id": self.grupo_utn.id, "nombre": self.grupo_utn.nombre_sigla_grupo}
            if self.grupo_utn else None
        )
        data["fuente"] = (
            {"id": self.fuente_financiamiento.id, "nombre": self.fuente_financiamiento.nombre}
            if self.fuente_financiamiento else None
        )
        data["categoria_erogacion"] = (
            {
                "id": self.categoria_erogacion.id,
                "codigo": self.categoria_erogacion.codigo,
                "nombre": self.categoria_erogacion.nombre,
            }
            if self.categoria_erogacion else None
        )
        data["equipamiento"] = (
            {"id": self.equipamiento.id, "denominacion": self.equipamiento.denominacion}
            if self.equipamiento else None
        )
        return data


class MovimientoMemoriaVersion(db.Model, AuditMixin):
    """Foto inmutable de un movimiento al versionar una memoria."""

    __tablename__ = "movimiento_memoria_version"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    memoria_version_id = db.Column(
        db.Integer, db.ForeignKey("memoria_version.id"), nullable=False
    )
    movimiento_id = db.Column(
        db.Integer, db.ForeignKey("movimiento_financiero.id"), nullable=False
    )
    numero_movimiento = db.Column(db.Integer, nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    tipo_movimiento = db.Column(db.String(7), nullable=False)
    monto = db.Column(db.Numeric(18, 2, asdecimal=True), nullable=False)
    moneda = db.Column(db.String(3), nullable=False)
    tipo_cambio_aplicado = db.Column(db.Numeric(18, 6, asdecimal=True), nullable=True)
    monto_equivalente_ars = db.Column(db.Numeric(24, 2, asdecimal=True), nullable=True)
    fecha_cotizacion = db.Column(db.Date, nullable=True)
    serie_bcra = db.Column(db.Integer, nullable=True)
    fuente_financiamiento_id = db.Column(db.Integer, nullable=True)
    fuente_financiamiento_nombre = db.Column(db.String(255), nullable=True)
    categoria_erogacion_id = db.Column(db.Integer, nullable=True)
    categoria_erogacion_codigo = db.Column(db.String(20), nullable=True)
    categoria_erogacion_nombre = db.Column(db.String(100), nullable=True)
    equipamiento_id = db.Column(db.Integer, nullable=True)
    equipamiento_denominacion = db.Column(db.Text, nullable=True)
    grupo_utn_id = db.Column(db.Integer, nullable=False)
    grupo_utn_nombre = db.Column(db.String(255), nullable=True)

    __table_args__ = (
        db.UniqueConstraint(
            "memoria_version_id", "movimiento_id",
            name="uq_movimiento_memoria_version",
        ),
    )

    def serialize(self):
        data = self.to_dict()
        data["monto"] = str(self.monto)
        data["tipo_cambio_aplicado"] = str(self.tipo_cambio_aplicado) if self.tipo_cambio_aplicado is not None else None
        data["monto_equivalente_ars"] = str(self.monto_equivalente_ars) if self.monto_equivalente_ars is not None else None
        return data
