from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Book(Base):
    __tablename__ = "book"
    __allow_unmapped__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(256), nullable=False)
    author = Column(String(128), nullable=False)
    isbn = Column(String(20), nullable=True)
    publisher = Column(String(128), nullable=True)
    publication_year = Column(Integer, nullable=True)


    copies = relationship("BookCopy", back_populates="book")


class BookCopy(Base):
    __tablename__ = "book_copy"
    __allow_unmapped__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("book.id"), nullable=False)
    edition = Column(String(64), nullable=True)
    copy_number = Column(Integer, nullable=False)
    condition = Column(String(64), nullable=True)
    is_available = Column(Boolean, default=True)

    book = relationship("Book", back_populates="copies")
    # Relationship for Borrow model
    borrows = relationship("Borrow", back_populates="book_copy", lazy="dynamic")
