from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

from database import get_db
from app.models.borrow import Borrow
from app.models.book import Book, BookCopy
from app.models.user import User, Funcionario, Cliente

router = APIRouter(prefix="/borrows", tags=["Empréstimos"])

# Schemas Pydantic para Borrow
class BorrowBase(BaseModel):
    book_copy_id: int
    borrower_id: int
    lender_id: int
    due_date: datetime

class BorrowCreate(BorrowBase):
    pass

class BorrowUpdate(BaseModel):
    due_date: Optional[datetime] = None

class BorrowResponse(BorrowBase):
    id: int
    borrow_date: datetime
    return_date: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Schema para resposta detalhada com informações do livro e usuários
class BorrowDetailResponse(BaseModel):
    id: int
    book_copy_id: int
    borrower_id: int
    lender_id: int
    borrow_date: datetime
    due_date: datetime
    return_date: Optional[datetime] = None
    
    # Informações do livro
    book_title: str
    book_author: str
    copy_number: int
    book_condition: Optional[str] = None
    
    # Informações dos usuários
    borrower_name: str
    borrower_email: str
    lender_name: str
    lender_email: str
    
    class Config:
        from_attributes = True

# Schema para devolução
class ReturnBookRequest(BaseModel):
    return_date: Optional[datetime] = None

# Schema para empréstimo com validações
class CreateBorrowRequest(BaseModel):
    book_copy_id: int
    borrower_id: int
    lender_id: int
    due_date: datetime

# Funções auxiliares
def verificar_disponibilidade_copia(db: Session, book_copy_id: int) -> BookCopy:
    """Verifica se uma cópia está disponível para empréstimo"""
    copia = db.query(BookCopy).filter(BookCopy.id == book_copy_id).first()
    if not copia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cópia do livro não encontrada"
        )
    
    if not copia.is_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cópia não está disponível para empréstimo"
        )
    
    return copia

def verificar_emprestimos_ativos(db: Session, borrower_id: int) -> List[Borrow]:
    """Verifica empréstimos ativos de um usuário"""
    return db.query(Borrow).filter(
        and_(
            Borrow.borrower_id == borrower_id,
            Borrow.return_date.is_(None)
        )
    ).all()

def verificar_atrasos(db: Session, borrower_id: int) -> List[Borrow]:
    """Verifica empréstimos em atraso de um usuário"""
    hoje = datetime.now()
    return db.query(Borrow).filter(
        and_(
            Borrow.borrower_id == borrower_id,
            Borrow.return_date.is_(None),
            Borrow.due_date < hoje
        )
    ).all()

def verificar_limite_emprestimos(db: Session, borrower_id: int, max_emprestimos: int = 3) -> bool:
    """Verifica se o usuário não excedeu o limite de empréstimos"""
    emprestimos_ativos = verificar_emprestimos_ativos(db, borrower_id)
    return len(emprestimos_ativos) < max_emprestimos

def verificar_funcionario(db: Session, user_id: int) -> bool:
    """Verifica se o usuário é um funcionário"""
    funcionario = db.query(Funcionario).filter(Funcionario.id == user_id).first()
    return funcionario is not None

# Operações CRUD para Borrow
@router.get("/", response_model=List[BorrowResponse], summary="Listar todos os empréstimos")
def listar_emprestimos(
    skip: int = 0, 
    limit: int = 100, 
    ativo: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    Lista todos os empréstimos cadastrados no sistema.
    
    - **skip**: Número de registros para pular (para paginação)
    - **limit**: Número máximo de registros a retornar
    - **ativo**: Filtrar por empréstimos ativos (True) ou devolvidos (False)
    """
    query = db.query(Borrow)
    
    if ativo is not None:
        if ativo:
            query = query.filter(Borrow.return_date.is_(None))
        else:
            query = query.filter(Borrow.return_date.is_not(None))
    
    emprestimos = query.offset(skip).limit(limit).all()
    return emprestimos

@router.get("/{borrow_id}", response_model=BorrowDetailResponse, summary="Buscar empréstimo por ID")
def buscar_emprestimo(borrow_id: int, db: Session = Depends(get_db)):
    """
    Busca um empréstimo específico pelo ID com informações detalhadas.
    
    - **borrow_id**: ID único do empréstimo
    """
    emprestimo = db.query(Borrow).filter(Borrow.id == borrow_id).first()
    if emprestimo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empréstimo não encontrado"
        )
    
    # Buscar informações relacionadas
    copia = db.query(BookCopy).filter(BookCopy.id == emprestimo.book_copy_id).first()
    livro = db.query(Book).filter(Book.id == copia.book_id).first()
    borrower = db.query(User).filter(User.id == emprestimo.borrower_id).first()
    lender = db.query(User).filter(User.id == emprestimo.lender_id).first()
    
    return BorrowDetailResponse(
        id=emprestimo.id,
        book_copy_id=emprestimo.book_copy_id,
        borrower_id=emprestimo.borrower_id,
        lender_id=emprestimo.lender_id,
        borrow_date=emprestimo.borrow_date,
        due_date=emprestimo.due_date,
        return_date=emprestimo.return_date,
        book_title=livro.title,
        book_author=livro.author,
        copy_number=copia.copy_number,
        book_condition=copia.condition,
        borrower_name=borrower.name,
        borrower_email=borrower.email,
        lender_name=lender.name,
        lender_email=lender.email
    )

@router.get("/user/{user_id}", response_model=List[BorrowDetailResponse], summary="Listar empréstimos de um usuário")
def listar_emprestimos_usuario(
    user_id: int, 
    ativo: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    Lista todos os empréstimos de um usuário específico.
    
    - **user_id**: ID do usuário
    - **ativo**: Filtrar por empréstimos ativos (True) ou devolvidos (False)
    """
    # Verificar se o usuário existe
    usuario = db.query(User).filter(User.id == user_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    query = db.query(Borrow).filter(Borrow.borrower_id == user_id)
    
    if ativo is not None:
        if ativo:
            query = query.filter(Borrow.return_date.is_(None))
        else:
            query = query.filter(Borrow.return_date.is_not(None))
    
    emprestimos = query.all()
    
    # Construir resposta detalhada
    resultado = []
    for emprestimo in emprestimos:
        copia = db.query(BookCopy).filter(BookCopy.id == emprestimo.book_copy_id).first()
        livro = db.query(Book).filter(Book.id == copia.book_id).first()
        borrower = db.query(User).filter(User.id == emprestimo.borrower_id).first()
        lender = db.query(User).filter(User.id == emprestimo.lender_id).first()
        
        resultado.append(BorrowDetailResponse(
            id=emprestimo.id,
            book_copy_id=emprestimo.book_copy_id,
            borrower_id=emprestimo.borrower_id,
            lender_id=emprestimo.lender_id,
            borrow_date=emprestimo.borrow_date,
            due_date=emprestimo.due_date,
            return_date=emprestimo.return_date,
            book_title=livro.title,
            book_author=livro.author,
            copy_number=copia.copy_number,
            book_condition=copia.condition,
            borrower_name=borrower.name,
            borrower_email=borrower.email,
            lender_name=lender.name,
            lender_email=lender.email
        ))
    
    return resultado

@router.get("/overdue/", response_model=List[BorrowDetailResponse], summary="Listar empréstimos em atraso")
def listar_emprestimos_atraso(db: Session = Depends(get_db)):
    """
    Lista todos os empréstimos que estão em atraso.
    """
    hoje = datetime.now()
    emprestimos = db.query(Borrow).filter(
        and_(
            Borrow.return_date.is_(None),
            Borrow.due_date < hoje
        )
    ).all()
    
    # Construir resposta detalhada
    resultado = []
    for emprestimo in emprestimos:
        copia = db.query(BookCopy).filter(BookCopy.id == emprestimo.book_copy_id).first()
        livro = db.query(Book).filter(Book.id == copia.book_id).first()
        borrower = db.query(User).filter(User.id == emprestimo.borrower_id).first()
        lender = db.query(User).filter(User.id == emprestimo.lender_id).first()
        
        resultado.append(BorrowDetailResponse(
            id=emprestimo.id,
            book_copy_id=emprestimo.book_copy_id,
            borrower_id=emprestimo.borrower_id,
            lender_id=emprestimo.lender_id,
            borrow_date=emprestimo.borrow_date,
            due_date=emprestimo.due_date,
            return_date=emprestimo.return_date,
            book_title=livro.title,
            book_author=livro.author,
            copy_number=copia.copy_number,
            book_condition=copia.condition,
            borrower_name=borrower.name,
            borrower_email=borrower.email,
            lender_name=lender.name,
            lender_email=lender.email
        ))
    
    return resultado

@router.post("/", response_model=BorrowResponse, status_code=status.HTTP_201_CREATED, summary="Criar novo empréstimo")
def criar_emprestimo(emprestimo: CreateBorrowRequest, db: Session = Depends(get_db)):
    """
    Cria um novo empréstimo no sistema.
    
    - **emprestimo**: Dados do empréstimo a ser criado
    """
    # Validações básicas
    if emprestimo.due_date <= datetime.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A data de devolução deve ser futura"
        )
    
    # Verificar se a cópia está disponível
    copia = verificar_disponibilidade_copia(db, emprestimo.book_copy_id)
    
    # Verificar se o borrower existe
    borrower = db.query(User).filter(User.id == emprestimo.borrower_id).first()
    if not borrower:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário que está emprestando não encontrado"
        )
    
    # Verificar se o lender existe e é funcionário
    lender = db.query(User).filter(User.id == emprestimo.lender_id).first()
    if not lender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funcionário que está processando o empréstimo não encontrado"
        )
    
    if not verificar_funcionario(db, emprestimo.lender_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas funcionários podem processar empréstimos"
        )
    
    # Verificar se o borrower não excedeu o limite de empréstimos
    if not verificar_limite_emprestimos(db, emprestimo.borrower_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário excedeu o limite de empréstimos ativos"
        )
    
    # Verificar se o borrower não tem empréstimos em atraso
    atrasos = verificar_atrasos(db, emprestimo.borrower_id)
    if atrasos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário possui empréstimos em atraso e não pode fazer novos empréstimos"
        )
    
    # Criar o empréstimo
    db_emprestimo = Borrow(
        book_copy_id=emprestimo.book_copy_id,
        borrower_id=emprestimo.borrower_id,
        lender_id=emprestimo.lender_id,
        due_date=emprestimo.due_date
    )
    
    # Marcar a cópia como indisponível
    copia.is_available = False
    
    db.add(db_emprestimo)
    db.commit()
    db.refresh(db_emprestimo)
    
    return db_emprestimo

@router.put("/{borrow_id}/return", response_model=BorrowResponse, summary="Marcar devolução de livro")
def marcar_devolucao(
    borrow_id: int, 
    devolucao: ReturnBookRequest,
    db: Session = Depends(get_db)
):
    """
    Marca a devolução de um livro emprestado.
    
    - **borrow_id**: ID do empréstimo
    - **devolucao**: Data de devolução (opcional, usa data atual se não informada)
    """
    emprestimo = db.query(Borrow).filter(Borrow.id == borrow_id).first()
    if emprestimo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empréstimo não encontrado"
        )
    
    if emprestimo.return_date is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este empréstimo já foi devolvido"
        )
    
    # Definir data de devolução
    data_devolucao = devolucao.return_date if devolucao.return_date else datetime.now()
    
    # Atualizar empréstimo
    emprestimo.return_date = data_devolucao
    
    # Marcar a cópia como disponível novamente
    copia = db.query(BookCopy).filter(BookCopy.id == emprestimo.book_copy_id).first()
    if copia:
        copia.is_available = True
    
    db.commit()
    db.refresh(emprestimo)
    
    return emprestimo

@router.put("/{borrow_id}", response_model=BorrowResponse, summary="Atualizar empréstimo")
def atualizar_emprestimo(
    borrow_id: int, 
    emprestimo_update: BorrowUpdate, 
    db: Session = Depends(get_db)
):
    """
    Atualiza um empréstimo existente.
    
    - **borrow_id**: ID do empréstimo
    - **emprestimo_update**: Dados para atualização
    """
    emprestimo = db.query(Borrow).filter(Borrow.id == borrow_id).first()
    if emprestimo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empréstimo não encontrado"
        )
    
    if emprestimo.return_date is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível atualizar um empréstimo já devolvido"
        )
    
    # Atualizar campos
    if emprestimo_update.due_date is not None:
        if emprestimo_update.due_date <= datetime.now():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A data de devolução deve ser futura"
            )
        emprestimo.due_date = emprestimo_update.due_date
    
    db.commit()
    db.refresh(emprestimo)
    
    return emprestimo

@router.get("/stats/overdue", summary="Estatísticas de empréstimos em atraso")
def estatisticas_atraso(db: Session = Depends(get_db)):
    """
    Retorna estatísticas sobre empréstimos em atraso.
    """
    hoje = datetime.now()
    
    # Total de empréstimos em atraso
    total_atraso = db.query(Borrow).filter(
        and_(
            Borrow.return_date.is_(None),
            Borrow.due_date < hoje
        )
    ).count()
    
    # Empréstimos em atraso por usuário
    atrasos_por_usuario = db.query(
        Borrow.borrower_id,
        User.name,
        User.email
    ).join(User, Borrow.borrower_id == User.id).filter(
        and_(
            Borrow.return_date.is_(None),
            Borrow.due_date < hoje
        )
    ).all()
    
    return {
        "total_emprestimos_atraso": total_atraso,
        "usuarios_com_atraso": [
            {
                "user_id": item.borrower_id,
                "name": item.name,
                "email": item.email
            }
            for item in atrasos_por_usuario
        ]
    }

@router.get("/stats/active", summary="Estatísticas de empréstimos ativos")
def estatisticas_ativos(db: Session = Depends(get_db)):
    """
    Retorna estatísticas sobre empréstimos ativos.
    """
    # Total de empréstimos ativos
    total_ativos = db.query(Borrow).filter(Borrow.return_date.is_(None)).count()
    
    # Empréstimos ativos por usuário
    ativos_por_usuario = db.query(
        Borrow.borrower_id,
        User.name,
        User.email
    ).join(User, Borrow.borrower_id == User.id).filter(
        Borrow.return_date.is_(None)
    ).all()
    
    return {
        "total_emprestimos_ativos": total_ativos,
        "usuarios_com_emprestimos_ativos": [
            {
                "user_id": item.borrower_id,
                "name": item.name,
                "email": item.email
            }
            for item in ativos_por_usuario
        ]
    } 