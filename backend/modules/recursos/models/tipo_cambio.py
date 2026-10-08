"""Observaciones oficiales de cotización, independientes de los movimientos."""

from datetime import datetime, timezone

from extension import db


class TipoCambio(db.Model):
    __tablename__ = "tipo_cambio"

    id = db.Column(db.Integer, primary_key=True)
    moneda_origen = db.Column(db.String(3), nullable=False, default="USD")
    moneda_destino = db.Column(db.String(3), nullable=False, default="ARS")
    fecha_cotizacion = db.Column(db.Date, nullable=False)
    valor = db.Column(db.Numeric(18, 6, asdecimal=True), nullable=False)
    serie_bcra = db.Column(db.Integer, nullable=False)
    fuente = db.Column(db.String(32), nullable=False, default="BCRA")
    fecha_obtencion = db.Column(db.DateTime(timezone=True), nullable=False,
                               default=lambda: datetime.now(timezone.utc))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False,
                           default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint("moneda_origen", "moneda_destino", "fecha_cotizacion", "serie_bcra",
                            name="uq_tipo_cambio_observacion"),
        db.CheckConstraint("valor > 0", name="ck_tipo_cambio_valor_positivo"),
        db.Index("ix_tipo_cambio_vigente", "moneda_origen", "moneda_destino",
                 "serie_bcra", "fecha_cotizacion"),
    )

    def serialize(self):
        return {"id": self.id, "fecha_cotizacion": self.fecha_cotizacion.isoformat(),
                "valor": str(self.valor), "serie_bcra": self.serie_bcra, "fuente": self.fuente,
                "moneda_origen": self.moneda_origen, "moneda_destino": self.moneda_destino}
