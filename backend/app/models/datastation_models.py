"""
datastation_models.py — vraag-inbox en audittrail van het datastation.

Conform de KIK-V-datastationeisen: binnengekomen gevalideerde vragen worden
hier vastgelegd, het berekende antwoord wordt door de zorgaanbieder beoordeeld
(accorderen of handmatig overschrijven) en pas daarna verzonden. Elke handeling
wordt in een audittrail vastgelegd. Het zaaknummer is de id van de vraag.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base, GUID


# Statuswaarden (als simpele strings — geen enum-migratie nodig)
STATUS_TE_BEOORDELEN = "TE_BEOORDELEN"   # vraag binnen, antwoord berekend, wacht op oordeel
STATUS_VERZONDEN     = "VERZONDEN"       # geaccordeerd/overschreven, antwoord vrijgegeven
STATUS_AFGEWEZEN     = "AFGEWEZEN"       # zorgaanbieder beantwoordt deze vraag niet
STATUS_FOUT          = "FOUT"            # kon niet berekend worden


class DatastationVraag(Base):
    """Een binnengekomen gevalideerde vraag (zaaknummer = id)."""
    __tablename__ = "datastation_vragen"

    id                 = Column(GUID(), primary_key=True, default=uuid.uuid4)
    sparql             = Column(Text, nullable=False)
    uitwisselprofiel   = Column(String(255), nullable=True)
    indicator_code     = Column(String(64), nullable=True)
    afnemer            = Column(String(255), nullable=True)   # wie stelt de vraag (ketenpartij)
    zorgaanbieder      = Column(String(255), nullable=True)   # voor wie is de vraag bestemd

    status             = Column(String(24), nullable=False, default=STATUS_TE_BEOORDELEN, index=True)
    berekende_waarde   = Column(Float, nullable=True)         # wat het datastation uitrekende
    definitieve_waarde = Column(Float, nullable=True)         # na accorderen/overschrijven
    handmatig          = Column(Boolean, nullable=False, default=False)
    toelichting        = Column(Text, nullable=True)
    backend            = Column(String(24), nullable=True)    # fuseki / rdflib

    ontvangen_op       = Column(DateTime(timezone=True), server_default=func.now())
    beoordeeld_op      = Column(DateTime(timezone=True), nullable=True)
    beoordeeld_door    = Column(String(255), nullable=True)

    audit = relationship("DatastationAudit", back_populates="vraag",
                         cascade="all, delete-orphan", order_by="DatastationAudit.op")

    def as_dict(self) -> dict:
        return {
            "zaaknummer": str(self.id),
            "query_id": str(self.id),
            "sparql": self.sparql,
            "uitwisselprofiel": self.uitwisselprofiel,
            "indicator_code": self.indicator_code,
            "afnemer": self.afnemer,
            "zorgaanbieder": self.zorgaanbieder,
            "status": self.status,
            "berekende_waarde": self.berekende_waarde,
            "definitieve_waarde": self.definitieve_waarde,
            "handmatig": self.handmatig,
            "toelichting": self.toelichting,
            "backend": self.backend,
            "ontvangen_op": self.ontvangen_op.isoformat() if self.ontvangen_op else None,
            "beoordeeld_op": self.beoordeeld_op.isoformat() if self.beoordeeld_op else None,
            "beoordeeld_door": self.beoordeeld_door,
        }


class DatastationAudit(Base):
    """Onveranderlijke logregel: elke handeling op een vraag."""
    __tablename__ = "datastation_audit"

    id       = Column(GUID(), primary_key=True, default=uuid.uuid4)
    vraag_id = Column(GUID(), ForeignKey("datastation_vragen.id", ondelete="CASCADE"),
                      nullable=False, index=True)
    actie    = Column(String(32), nullable=False)   # ONTVANGEN/BEREKEND/GEACCORDEERD/OVERSCHREVEN/AFGEWEZEN/OPGEHAALD
    details  = Column(Text, nullable=True)
    door     = Column(String(255), nullable=True)
    op       = Column(DateTime(timezone=True), server_default=func.now())

    vraag = relationship("DatastationVraag", back_populates="audit")

    def as_dict(self) -> dict:
        return {"actie": self.actie, "details": self.details, "door": self.door,
                "op": self.op.isoformat() if self.op else None}
