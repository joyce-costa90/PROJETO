from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
import re

from database import get_db
from app.models.empresa import Empresa

router = APIRouter(prefix="/empresas", tags=["Empresas"])

# Schemas Pydantic
class EmpresaBase(BaseModel):
    cnpj: str
    razao_social: str
    nome_fantasia: str | None = None
    numero_contato: str | None = None
    email_contato: str | None = None
    website: str | None = None

class EmpresaCreate(EmpresaBase):
    pass

class EmpresaUpdate(BaseModel):
    cnpj: str | None = None
    razao_social: str | None = None
    nome_fantasia: str | None = None
    numero_contato: str | None = None
    email_contato: str | None = None
    website: str | None = None

class EmpresaResponse(EmpresaBase):
    id: int
    
    class Config:
        from_attributes = True

# Funções auxiliares
def validar_cnpj(cnpj: str) -> bool:
    """Valida se o CNPJ está no formato correto"""
    # Remove caracteres não numéricos
    cnpj = re.sub(r'[^0-9]', '', cnpj)
    
    # Verifica se tem 14 dígitos
    if len(cnpj) != 14:
        return False
    
    # Verifica se não são todos dígitos iguais
    if cnpj == cnpj[0] * 14:
        return False
    
    return True

def validar_email(email: str) -> bool:
    """Valida formato de email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validar_telefone(telefone: str) -> bool:
    """Valida formato de telefone brasileiro"""
    # Remove caracteres não numéricos
    telefone = re.sub(r'[^0-9]', '', telefone)
    
    # Verifica se tem 10 ou 11 dígitos (com DDD)
    return len(telefone) in [10, 11]

# Operações CRUD
@router.get("/", response_model=List[EmpresaResponse], summary="Listar todas as empresas")
def listar_empresas(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Lista todas as empresas cadastradas no sistema.
    
    - **skip**: Número de registros para pular (para paginação)
    - **limit**: Número máximo de registros a retornar
    """
    empresas = db.query(Empresa).offset(skip).limit(limit).all()
    return empresas

@router.get("/{empresa_id}", response_model=EmpresaResponse, summary="Buscar empresa por ID")
def buscar_empresa(empresa_id: int, db: Session = Depends(get_db)):
    """
    Busca uma empresa específica pelo ID.
    
    - **empresa_id**: ID único da empresa
    """
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if empresa is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa não encontrada"
        )
    return empresa

@router.get("/cnpj/{cnpj}", response_model=EmpresaResponse, summary="Buscar empresa por CNPJ")
def buscar_empresa_por_cnpj(cnpj: str, db: Session = Depends(get_db)):
    """
    Busca uma empresa pelo CNPJ.
    
    - **cnpj**: CNPJ da empresa (apenas números)
    """
    # Remove caracteres não numéricos
    cnpj_limpo = re.sub(r'[^0-9]', '', cnpj)
    
    empresa = db.query(Empresa).filter(Empresa.cnpj == cnpj_limpo).first()
    if empresa is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa não encontrada"
        )
    return empresa

@router.post("/", response_model=EmpresaResponse, status_code=status.HTTP_201_CREATED, summary="Criar nova empresa")
def criar_empresa(empresa: EmpresaCreate, db: Session = Depends(get_db)):
    """
    Cria uma nova empresa no sistema.
    
    - **empresa**: Dados da empresa a ser criada
    """
    # Validações
    if not validar_cnpj(empresa.cnpj):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CNPJ inválido"
        )
    
    if empresa.email_contato and not validar_email(empresa.email_contato):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email inválido"
        )
    
    if empresa.numero_contato and not validar_telefone(empresa.numero_contato):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Número de telefone inválido"
        )
    
    # Remove caracteres não numéricos do CNPJ
    cnpj_limpo = re.sub(r'[^0-9]', '', empresa.cnpj)
    
    # Verifica se já existe empresa com este CNPJ
    empresa_existente = db.query(Empresa).filter(Empresa.cnpj == cnpj_limpo).first()
    if empresa_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe uma empresa cadastrada com este CNPJ"
        )
    
    # Cria nova empresa
    db_empresa = Empresa(
        cnpj=cnpj_limpo,
        razao_social=empresa.razao_social,
        nome_fantasia=empresa.nome_fantasia,
        numero_contato=empresa.numero_contato,
        email_contato=empresa.email_contato,
        website=empresa.website
    )
    
    db.add(db_empresa)
    db.commit()
    db.refresh(db_empresa)
    
    return db_empresa

@router.put("/{empresa_id}", response_model=EmpresaResponse, summary="Atualizar empresa")
def atualizar_empresa(empresa_id: int, empresa_update: EmpresaUpdate, db: Session = Depends(get_db)):
    """
    Atualiza os dados de uma empresa existente.
    
    - **empresa_id**: ID da empresa a ser atualizada
    - **empresa_update**: Dados a serem atualizados
    """
    # Busca a empresa
    db_empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if db_empresa is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa não encontrada"
        )
    
    # Validações
    if empresa_update.cnpj:
        if not validar_cnpj(empresa_update.cnpj):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CNPJ inválido"
            )
        
        cnpj_limpo = re.sub(r'[^0-9]', '', empresa_update.cnpj)
        
        # Verifica se já existe outra empresa com este CNPJ
        empresa_existente = db.query(Empresa).filter(
            Empresa.cnpj == cnpj_limpo,
            Empresa.id != empresa_id
        ).first()
        if empresa_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe outra empresa cadastrada com este CNPJ"
            )
    
    if empresa_update.email_contato and not validar_email(empresa_update.email_contato):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email inválido"
        )
    
    if empresa_update.numero_contato and not validar_telefone(empresa_update.numero_contato):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Número de telefone inválido"
        )
    
    # Atualiza os campos fornecidos
    update_data = empresa_update.model_dump(exclude_unset=True)
    
    if "cnpj" in update_data:
        update_data["cnpj"] = re.sub(r'[^0-9]', '', update_data["cnpj"])
    
    for field, value in update_data.items():
        setattr(db_empresa, field, value)
    
    db.commit()
    db.refresh(db_empresa)
    
    return db_empresa

@router.delete("/{empresa_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Deletar empresa")
def deletar_empresa(empresa_id: int, db: Session = Depends(get_db)):
    """
    Remove uma empresa do sistema.
    
    - **empresa_id**: ID da empresa a ser removida
    """
    # Busca a empresa
    db_empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if db_empresa is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa não encontrada"
        )
    
    # Remove a empresa
    db.delete(db_empresa)
    db.commit()
    
    return None
