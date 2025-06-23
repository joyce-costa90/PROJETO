from sqlalchemy import Column, Integer, String, Boolean, Float
from database import Base

class Empresa(Base):
    __tablename__ = "empresa"
    __allow_unmapped__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)
    cnpj = Column(String(14), nullable=False)
    razao_social = Column(String(128), nullable=False)
    nome_fantasia = Column(String(128), nullable=True)
    numero_contato = Column(String(11), nullable=True)
    email_contato = Column(String(64), nullable=True)
    website = Column(String(128), nullable=True)