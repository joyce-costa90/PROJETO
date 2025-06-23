from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
import re

from database import get_db
from app.models.book import Book, BookCopy

router = APIRouter(prefix="/books", tags=["Livros"])

# Schemas Pydantic para Book
class BookBase(BaseModel):
    title: str
    author: str
    isbn: str | None = None
    publisher: str | None = None
    publication_year: int | None = None

class BookCreate(BookBase):
    pass

class BookUpdate(BaseModel):
    title: str | None = None
    author: str | None = None
    isbn: str | None = None
    publisher: str | None = None
    publication_year: int | None = None

class BookResponse(BookBase):
    id: int
    
    class Config:
        from_attributes = True

# Schemas Pydantic para BookCopy
class BookCopyBase(BaseModel):
    book_id: int
    edition: str | None = None
    copy_number: int
    condition: str | None = None
    is_available: bool = True

class BookCopyCreate(BookCopyBase):
    pass

class BookCopyUpdate(BaseModel):
    edition: str | None = None
    copy_number: int | None = None
    condition: str | None = None
    is_available: bool | None = None

class BookCopyResponse(BookCopyBase):
    id: int
    
    class Config:
        from_attributes = True

# Schema para Book com cópias
class BookWithCopiesResponse(BookResponse):
    copies: List[BookCopyResponse] = []
    
    class Config:
        from_attributes = True

# Funções auxiliares
def validar_isbn(isbn: str) -> bool:
    """Valida formato básico de ISBN"""
    # Remove hífens e espaços
    isbn_limpo = re.sub(r'[-\s]', '', isbn)
    
    # ISBN-10 tem 10 dígitos, ISBN-13 tem 13 dígitos
    if len(isbn_limpo) not in [10, 13]:
        return False
    
    # Verifica se são apenas dígitos (exceto o último que pode ser X para ISBN-10)
    if len(isbn_limpo) == 10:
        return isbn_limpo[:-1].isdigit() and (isbn_limpo[-1].isdigit() or isbn_limpo[-1].upper() == 'X')
    else:
        return isbn_limpo.isdigit()

def validar_ano_publicacao(ano: int) -> bool:
    """Valida se o ano de publicação é razoável"""
    return 1000 <= ano <= 2024

# Operações CRUD para Book
@router.get("/", response_model=List[BookResponse], summary="Listar todos os livros")
def listar_livros(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Lista todos os livros cadastrados no sistema.
    
    - **skip**: Número de registros para pular (para paginação)
    - **limit**: Número máximo de registros a retornar
    """
    livros = db.query(Book).offset(skip).limit(limit).all()
    return livros

@router.get("/{book_id}", response_model=BookResponse, summary="Buscar livro por ID")
def buscar_livro(book_id: int, db: Session = Depends(get_db)):
    """
    Busca um livro específico pelo ID.
    
    - **book_id**: ID único do livro
    """
    livro = db.query(Book).filter(Book.id == book_id).first()
    if livro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livro não encontrado"
        )
    return livro

@router.get("/{book_id}/with-copies", response_model=BookWithCopiesResponse, summary="Buscar livro com cópias")
def buscar_livro_com_copias(book_id: int, db: Session = Depends(get_db)):
    """
    Busca um livro específico com todas as suas cópias.
    
    - **book_id**: ID único do livro
    """
    livro = db.query(Book).filter(Book.id == book_id).first()
    if livro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livro não encontrado"
        )
    return livro

@router.get("/isbn/{isbn}", response_model=BookResponse, summary="Buscar livro por ISBN")
def buscar_livro_por_isbn(isbn: str, db: Session = Depends(get_db)):
    """
    Busca um livro pelo ISBN.
    
    - **isbn**: ISBN do livro
    """
    # Remove caracteres especiais do ISBN
    isbn_limpo = re.sub(r'[-\s]', '', isbn)
    
    livro = db.query(Book).filter(Book.isbn == isbn_limpo).first()
    if livro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livro não encontrado"
        )
    return livro

@router.get("/author/{author}", response_model=List[BookResponse], summary="Buscar livros por autor")
def buscar_livros_por_autor(author: str, db: Session = Depends(get_db)):
    """
    Busca livros por autor.
    
    - **author**: Nome do autor
    """
    livros = db.query(Book).filter(Book.author.ilike(f"%{author}%")).all()
    return livros

@router.post("/", response_model=BookResponse, status_code=status.HTTP_201_CREATED, summary="Criar novo livro")
def criar_livro(livro: BookCreate, db: Session = Depends(get_db)):
    """
    Cria um novo livro no sistema.
    
    - **livro**: Dados do livro a ser criado
    """
    # Validações
    if livro.isbn and not validar_isbn(livro.isbn):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ISBN inválido"
        )
    
    if livro.publication_year and not validar_ano_publicacao(livro.publication_year):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ano de publicação inválido"
        )
    
    # Remove caracteres especiais do ISBN
    isbn_limpo = None
    if livro.isbn:
        isbn_limpo = re.sub(r'[-\s]', '', livro.isbn)
        
        # Verifica se já existe livro com este ISBN
        livro_existente = db.query(Book).filter(Book.isbn == isbn_limpo).first()
        if livro_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe um livro cadastrado com este ISBN"
            )
    
    # Cria novo livro
    db_livro = Book(
        title=livro.title,
        author=livro.author,
        isbn=isbn_limpo,
        publisher=livro.publisher,
        publication_year=livro.publication_year
    )
    
    db.add(db_livro)
    db.commit()
    db.refresh(db_livro)
    
    return db_livro

@router.put("/{book_id}", response_model=BookResponse, summary="Atualizar livro")
def atualizar_livro(book_id: int, livro_update: BookUpdate, db: Session = Depends(get_db)):
    """
    Atualiza os dados de um livro existente.
    
    - **book_id**: ID do livro a ser atualizado
    - **livro_update**: Dados a serem atualizados
    """
    # Busca o livro
    db_livro = db.query(Book).filter(Book.id == book_id).first()
    if db_livro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livro não encontrado"
        )
    
    # Validações
    if livro_update.isbn:
        if not validar_isbn(livro_update.isbn):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ISBN inválido"
            )
        
        isbn_limpo = re.sub(r'[-\s]', '', livro_update.isbn)
        
        # Verifica se já existe outro livro com este ISBN
        livro_existente = db.query(Book).filter(
            Book.isbn == isbn_limpo,
            Book.id != book_id
        ).first()
        if livro_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe outro livro cadastrado com este ISBN"
            )
    
    if livro_update.publication_year and not validar_ano_publicacao(livro_update.publication_year):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ano de publicação inválido"
        )
    
    # Atualiza os campos fornecidos
    update_data = livro_update.model_dump(exclude_unset=True)
    
    if "isbn" in update_data:
        update_data["isbn"] = re.sub(r'[-\s]', '', update_data["isbn"])
    
    for field, value in update_data.items():
        setattr(db_livro, field, value)
    
    db.commit()
    db.refresh(db_livro)
    
    return db_livro

@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Deletar livro")
def deletar_livro(book_id: int, db: Session = Depends(get_db)):
    """
    Remove um livro do sistema.
    
    - **book_id**: ID do livro a ser removido
    """
    # Busca o livro
    db_livro = db.query(Book).filter(Book.id == book_id).first()
    if db_livro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livro não encontrado"
        )
    
    # Verifica se há cópias associadas
    copias = db.query(BookCopy).filter(BookCopy.book_id == book_id).count()
    if copias > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível deletar um livro que possui cópias cadastradas"
        )
    
    # Remove o livro
    db.delete(db_livro)
    db.commit()
    
    return None

# Operações CRUD para BookCopy
@router.get("/copies/", response_model=List[BookCopyResponse], summary="Listar todas as cópias")
def listar_copias(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Lista todas as cópias de livros cadastradas no sistema.
    
    - **skip**: Número de registros para pular (para paginação)
    - **limit**: Número máximo de registros a retornar
    """
    copias = db.query(BookCopy).offset(skip).limit(limit).all()
    return copias

@router.get("/copies/{copy_id}", response_model=BookCopyResponse, summary="Buscar cópia por ID")
def buscar_copia(copy_id: int, db: Session = Depends(get_db)):
    """
    Busca uma cópia específica pelo ID.
    
    - **copy_id**: ID único da cópia
    """
    copia = db.query(BookCopy).filter(BookCopy.id == copy_id).first()
    if copia is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cópia não encontrada"
        )
    return copia

@router.get("/copies/book/{book_id}", response_model=List[BookCopyResponse], summary="Listar cópias de um livro")
def listar_copias_do_livro(book_id: int, db: Session = Depends(get_db)):
    """
    Lista todas as cópias de um livro específico.
    
    - **book_id**: ID do livro
    """
    # Verifica se o livro existe
    livro = db.query(Book).filter(Book.id == book_id).first()
    if livro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livro não encontrado"
        )
    
    copias = db.query(BookCopy).filter(BookCopy.book_id == book_id).all()
    return copias

@router.get("/copies/available/", response_model=List[BookCopyResponse], summary="Listar cópias disponíveis")
def listar_copias_disponiveis(db: Session = Depends(get_db)):
    """
    Lista todas as cópias disponíveis para empréstimo.
    """
    copias = db.query(BookCopy).filter(BookCopy.is_available == True).all()
    return copias

@router.post("/copies/", response_model=BookCopyResponse, status_code=status.HTTP_201_CREATED, summary="Criar nova cópia")
def criar_copia(copia: BookCopyCreate, db: Session = Depends(get_db)):
    """
    Cria uma nova cópia de livro no sistema.
    
    - **copia**: Dados da cópia a ser criada
    """
    # Verifica se o livro existe
    livro = db.query(Book).filter(Book.id == copia.book_id).first()
    if livro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livro não encontrado"
        )
    
    # Verifica se já existe uma cópia com o mesmo número para este livro
    copia_existente = db.query(BookCopy).filter(
        BookCopy.book_id == copia.book_id,
        BookCopy.copy_number == copia.copy_number
    ).first()
    if copia_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe uma cópia com este número para este livro"
        )
    
    # Cria nova cópia
    db_copia = BookCopy(
        book_id=copia.book_id,
        edition=copia.edition,
        copy_number=copia.copy_number,
        condition=copia.condition,
        is_available=copia.is_available
    )
    
    db.add(db_copia)
    db.commit()
    db.refresh(db_copia)
    
    return db_copia

@router.put("/copies/{copy_id}", response_model=BookCopyResponse, summary="Atualizar cópia")
def atualizar_copia(copy_id: int, copia_update: BookCopyUpdate, db: Session = Depends(get_db)):
    """
    Atualiza os dados de uma cópia existente.
    
    - **copy_id**: ID da cópia a ser atualizada
    - **copia_update**: Dados a serem atualizados
    """
    # Busca a cópia
    db_copia = db.query(BookCopy).filter(BookCopy.id == copy_id).first()
    if db_copia is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cópia não encontrada"
        )
    
    # Validações
    if copia_update.copy_number is not None:
        # Verifica se já existe outra cópia com o mesmo número para este livro
        copia_existente = db.query(BookCopy).filter(
            BookCopy.book_id == db_copia.book_id,
            BookCopy.copy_number == copia_update.copy_number,
            BookCopy.id != copy_id
        ).first()
        if copia_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe outra cópia com este número para este livro"
            )
    
    # Atualiza os campos fornecidos
    update_data = copia_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(db_copia, field, value)
    
    db.commit()
    db.refresh(db_copia)
    
    return db_copia

@router.delete("/copies/{copy_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Deletar cópia")
def deletar_copia(copy_id: int, db: Session = Depends(get_db)):
    """
    Remove uma cópia do sistema.
    
    - **copy_id**: ID da cópia a ser removida
    """
    # Busca a cópia
    db_copia = db.query(BookCopy).filter(BookCopy.id == copy_id).first()
    if db_copia is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cópia não encontrada"
        )
    
    # Verifica se a cópia está emprestada
    if not db_copia.is_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível deletar uma cópia que está emprestada"
        )
    
    # Remove a cópia
    db.delete(db_copia)
    db.commit()
    
    return None 