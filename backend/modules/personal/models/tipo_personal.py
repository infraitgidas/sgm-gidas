from extension import db
from modules.shared.models.audit_mixin import AuditMixin
from modules.personal.services.tipo_personal_compatibilidad import compatible_con_personal


class TipoPersonal(db.Model, AuditMixin):
    __tablename__ = 'tipo_personal'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    
    personal = db.relationship('Personal', back_populates='tipo_personal', lazy="dynamic")

    
    def serialize(self):
        return {**self.to_dict(), "compatible_con_personal": compatible_con_personal(self.nombre)}
    
   
