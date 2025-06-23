from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import re
from datetime import datetime

from database import get_db
from app.models.user import User, Funcionario, Cliente

router = APIRouter(prefix="/users", tags=["Usuários"])

# Schemas Pydantic para User
class UserBase(BaseModel):
    name: str
    email: str
    password_hash: str

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password_hash: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    user_type: str
    
    class Config:
        from_attributes = True

# Schemas Pydantic para Funcionario
class FuncionarioBase(BaseModel):
    name: str
    email: str
    password_hash: str
    role: str

class FuncionarioCreate(FuncionarioBase):
    pass

class FuncionarioUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password_hash: Optional[str] = None
    role: Optional[str] = None

class FuncionarioResponse(UserResponse):
    role: str
    
    class Config:
        from_attributes = True

# Schemas Pydantic para Cliente
class ClienteBase(BaseModel):
    name: str
    email: str
    password_hash: str
    customer_type: Optional[str] = None
    address: Optional[str] = None

class ClienteCreate(ClienteBase):
    pass

class ClienteUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password_hash: Optional[str] = None
    customer_type: Optional[str] = None
    address: Optional[str] = None

class ClienteResponse(UserResponse):
    customer_type: Optional[str] = None
    address: Optional[str] = None
    
    class Config:
        from_attributes = True

# Funções auxiliares
def validar_email(email: str) -> bool:
    """Valida formato de email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validar_senha(senha: str) -> bool:
    """Valida se a senha tem pelo menos 6 caracteres"""
    return len(senha) >= 6

def hash_senha(senha: str) -> str:
    """Simula hash de senha (em produção, use bcrypt ou similar)"""
    # Aqui você deve implementar um hash real como bcrypt
    # Por enquanto, apenas simula
    return f"hashed_{senha}"

# Operações CRUD para User (genérico)
@router.get("/", response_model=List[UserResponse], summary="Listar todos os usuários")
def listar_usuarios(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Lista todos os usuários cadastrados no sistema.
    
    - **skip**: Número de registros para pular (para paginação)
    - **limit**: Número máximo de registros a retornar
    """
    usuarios = db.query(User).offset(skip).limit(limit).all()
    return usuarios

@router.get("/{user_id}", response_model=UserResponse, summary="Buscar usuário por ID")
def buscar_usuario(user_id: int, db: Session = Depends(get_db)):
    """
    Busca um usuário específico pelo ID.
    
    - **user_id**: ID único do usuário
    """
    usuario = db.query(User).filter(User.id == user_id).first()
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    return usuario

@router.get("/email/{email}", response_model=UserResponse, summary="Buscar usuário por email")
def buscar_usuario_por_email(email: str, db: Session = Depends(get_db)):
    """
    Busca um usuário pelo email.
    
    - **email**: Email do usuário
    """
    usuario = db.query(User).filter(User.email == email).first()
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    return usuario

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Criar novo usuário")
def criar_usuario(usuario: UserCreate, db: Session = Depends(get_db)):
    """
    Cria um novo usuário no sistema.
    
    - **usuario**: Dados do usuário a ser criado
    """
    # Validações
    if not validar_email(usuario.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email inválido"
        )
    
    if not validar_senha(usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha deve ter pelo menos 6 caracteres"
        )
    
    # Verifica se já existe usuário com este email
    usuario_existente = db.query(User).filter(User.email == usuario.email).first()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe um usuário cadastrado com este email"
        )
    
    # Hash da senha
    senha_hash = hash_senha(usuario.password_hash)
    
    # Cria novo usuário
    db_usuario = User(
        name=usuario.name,
        email=usuario.email,
        password_hash=senha_hash
    )
    
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    
    return db_usuario

@router.put("/{user_id}", response_model=UserResponse, summary="Atualizar usuário")
def atualizar_usuario(user_id: int, usuario_update: UserUpdate, db: Session = Depends(get_db)):
    """
    Atualiza os dados de um usuário existente.
    
    - **user_id**: ID do usuário a ser atualizado
    - **usuario_update**: Dados a serem atualizados
    """
    # Busca o usuário
    db_usuario = db.query(User).filter(User.id == user_id).first()
    if db_usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Validações
    if usuario_update.email:
        if not validar_email(usuario_update.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email inválido"
            )
        
        # Verifica se já existe outro usuário com este email
        usuario_existente = db.query(User).filter(
            User.email == usuario_update.email,
            User.id != user_id
        ).first()
        if usuario_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe outro usuário cadastrado com este email"
            )
    
    if usuario_update.password_hash and not validar_senha(usuario_update.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha deve ter pelo menos 6 caracteres"
        )
    
    # Atualiza os campos fornecidos
    update_data = usuario_update.model_dump(exclude_unset=True)
    
    if "password_hash" in update_data:
        update_data["password_hash"] = hash_senha(update_data["password_hash"])
    
    for field, value in update_data.items():
        setattr(db_usuario, field, value)
    
    db.commit()
    db.refresh(db_usuario)
    
    return db_usuario

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Deletar usuário")
def deletar_usuario(user_id: int, db: Session = Depends(get_db)):
    """
    Remove um usuário do sistema.
    
    - **user_id**: ID do usuário a ser removido
    """
    # Busca o usuário
    db_usuario = db.query(User).filter(User.id == user_id).first()
    if db_usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Remove o usuário
    db.delete(db_usuario)
    db.commit()
    
    return None

# Operações CRUD para Funcionario
@router.get("/funcionarios/", response_model=List[FuncionarioResponse], summary="Listar todos os funcionários")
def listar_funcionarios(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Lista todos os funcionários cadastrados no sistema.
    
    - **skip**: Número de registros para pular (para paginação)
    - **limit**: Número máximo de registros a retornar
    """
    funcionarios = db.query(Funcionario).offset(skip).limit(limit).all()
    return funcionarios

@router.get("/funcionarios/{funcionario_id}", response_model=FuncionarioResponse, summary="Buscar funcionário por ID")
def buscar_funcionario(funcionario_id: int, db: Session = Depends(get_db)):
    """
    Busca um funcionário específico pelo ID.
    
    - **funcionario_id**: ID único do funcionário
    """
    funcionario = db.query(Funcionario).filter(Funcionario.id == funcionario_id).first()
    if funcionario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funcionário não encontrado"
        )
    return funcionario

@router.get("/funcionarios/role/{role}", response_model=List[FuncionarioResponse], summary="Buscar funcionários por cargo")
def buscar_funcionarios_por_cargo(role: str, db: Session = Depends(get_db)):
    """
    Busca funcionários por cargo.
    
    - **role**: Cargo dos funcionários
    """
    funcionarios = db.query(Funcionario).filter(Funcionario.role.ilike(f"%{role}%")).all()
    return funcionarios

@router.post("/funcionarios/", response_model=FuncionarioResponse, status_code=status.HTTP_201_CREATED, summary="Criar novo funcionário")
def criar_funcionario(funcionario: FuncionarioCreate, db: Session = Depends(get_db)):
    """
    Cria um novo funcionário no sistema.
    
    - **funcionario**: Dados do funcionário a ser criado
    """
    # Validações
    if not validar_email(funcionario.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email inválido"
        )
    
    if not validar_senha(funcionario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha deve ter pelo menos 6 caracteres"
        )
    
    # Verifica se já existe usuário com este email
    usuario_existente = db.query(User).filter(User.email == funcionario.email).first()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe um usuário cadastrado com este email"
        )
    
    # Hash da senha
    senha_hash = hash_senha(funcionario.password_hash)
    
    # Cria novo funcionário
    db_funcionario = Funcionario(
        name=funcionario.name,
        email=funcionario.email,
        password_hash=senha_hash,
        role=funcionario.role
    )
    
    db.add(db_funcionario)
    db.commit()
    db.refresh(db_funcionario)
    
    return db_funcionario

@router.put("/funcionarios/{funcionario_id}", response_model=FuncionarioResponse, summary="Atualizar funcionário")
def atualizar_funcionario(funcionario_id: int, funcionario_update: FuncionarioUpdate, db: Session = Depends(get_db)):
    """
    Atualiza os dados de um funcionário existente.
    
    - **funcionario_id**: ID do funcionário a ser atualizado
    - **funcionario_update**: Dados a serem atualizados
    """
    # Busca o funcionário
    db_funcionario = db.query(Funcionario).filter(Funcionario.id == funcionario_id).first()
    if db_funcionario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funcionário não encontrado"
        )
    
    # Validações
    if funcionario_update.email:
        if not validar_email(funcionario_update.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email inválido"
            )
        
        # Verifica se já existe outro usuário com este email
        usuario_existente = db.query(User).filter(
            User.email == funcionario_update.email,
            User.id != funcionario_id
        ).first()
        if usuario_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe outro usuário cadastrado com este email"
            )
    
    if funcionario_update.password_hash and not validar_senha(funcionario_update.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha deve ter pelo menos 6 caracteres"
        )
    
    # Atualiza os campos fornecidos
    update_data = funcionario_update.model_dump(exclude_unset=True)
    
    if "password_hash" in update_data:
        update_data["password_hash"] = hash_senha(update_data["password_hash"])
    
    for field, value in update_data.items():
        setattr(db_funcionario, field, value)
    
    db.commit()
    db.refresh(db_funcionario)
    
    return db_funcionario

@router.delete("/funcionarios/{funcionario_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Deletar funcionário")
def deletar_funcionario(funcionario_id: int, db: Session = Depends(get_db)):
    """
    Remove um funcionário do sistema.
    
    - **funcionario_id**: ID do funcionário a ser removido
    """
    # Busca o funcionário
    db_funcionario = db.query(Funcionario).filter(Funcionario.id == funcionario_id).first()
    if db_funcionario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funcionário não encontrado"
        )
    
    # Remove o funcionário
    db.delete(db_funcionario)
    db.commit()
    
    return None

# Operações CRUD para Cliente
@router.get("/clientes/", response_model=List[ClienteResponse], summary="Listar todos os clientes")
def listar_clientes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Lista todos os clientes cadastrados no sistema.
    
    - **skip**: Número de registros para pular (para paginação)
    - **limit**: Número máximo de registros a retornar
    """
    clientes = db.query(Cliente).offset(skip).limit(limit).all()
    return clientes

@router.get("/clientes/{cliente_id}", response_model=ClienteResponse, summary="Buscar cliente por ID")
def buscar_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """
    Busca um cliente específico pelo ID.
    
    - **cliente_id**: ID único do cliente
    """
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    return cliente

@router.get("/clientes/type/{customer_type}", response_model=List[ClienteResponse], summary="Buscar clientes por tipo")
def buscar_clientes_por_tipo(customer_type: str, db: Session = Depends(get_db)):
    """
    Busca clientes por tipo.
    
    - **customer_type**: Tipo do cliente (individual, corporate, etc.)
    """
    clientes = db.query(Cliente).filter(Cliente.customer_type == customer_type).all()
    return clientes

@router.post("/clientes/", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED, summary="Criar novo cliente")
def criar_cliente(cliente: ClienteCreate, db: Session = Depends(get_db)):
    """
    Cria um novo cliente no sistema.
    
    - **cliente**: Dados do cliente a ser criado
    """
    # Validações
    if not validar_email(cliente.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email inválido"
        )
    
    if not validar_senha(cliente.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha deve ter pelo menos 6 caracteres"
        )
    
    # Verifica se já existe usuário com este email
    usuario_existente = db.query(User).filter(User.email == cliente.email).first()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe um usuário cadastrado com este email"
        )
    
    # Hash da senha
    senha_hash = hash_senha(cliente.password_hash)
    
    # Cria novo cliente
    db_cliente = Cliente(
        name=cliente.name,
        email=cliente.email,
        password_hash=senha_hash,
        customer_type=cliente.customer_type,
        address=cliente.address
    )
    
    db.add(db_cliente)
    db.commit()
    db.refresh(db_cliente)
    
    return db_cliente

@router.put("/clientes/{cliente_id}", response_model=ClienteResponse, summary="Atualizar cliente")
def atualizar_cliente(cliente_id: int, cliente_update: ClienteUpdate, db: Session = Depends(get_db)):
    """
    Atualiza os dados de um cliente existente.
    
    - **cliente_id**: ID do cliente a ser atualizado
    - **cliente_update**: Dados a serem atualizados
    """
    # Busca o cliente
    db_cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if db_cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    # Validações
    if cliente_update.email:
        if not validar_email(cliente_update.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email inválido"
            )
        
        # Verifica se já existe outro usuário com este email
        usuario_existente = db.query(User).filter(
            User.email == cliente_update.email,
            User.id != cliente_id
        ).first()
        if usuario_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe outro usuário cadastrado com este email"
            )
    
    if cliente_update.password_hash and not validar_senha(cliente_update.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha deve ter pelo menos 6 caracteres"
        )
    
    # Atualiza os campos fornecidos
    update_data = cliente_update.model_dump(exclude_unset=True)
    
    if "password_hash" in update_data:
        update_data["password_hash"] = hash_senha(update_data["password_hash"])
    
    for field, value in update_data.items():
        setattr(db_cliente, field, value)
    
    db.commit()
    db.refresh(db_cliente)
    
    return db_cliente

@router.delete("/clientes/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Deletar cliente")
def deletar_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """
    Remove um cliente do sistema.
    
    - **cliente_id**: ID do cliente a ser removido
    """
    # Busca o cliente
    db_cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if db_cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    # Remove o cliente
    db.delete(db_cliente)
    db.commit()
    
    return None 