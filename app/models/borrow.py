from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

# It's good practice to define enums for status fields if applicable,
# though not explicitly requested, it can be useful for borrow status.
# For now, let's stick to the core requirements.

class Borrow(Base):
    __tablename__ = "borrow"
    __allow_unmapped__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_copy_id = Column(Integer, ForeignKey("book_copy.id"), nullable=False)
    borrower_id = Column(Integer, ForeignKey("user.id"), nullable=False)  # This will be a User ID (Cliente or Funcionario)
    lender_id = Column(Integer, ForeignKey("user.id"), nullable=False) # This will be a User ID (Funcionario)

    borrow_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False)
    return_date = Column(DateTime(timezone=True), nullable=True) # Nullable, as it's set when returned

    # Relationships
    # Relationship to the specific copy of the book being borrowed
    book_copy = relationship("BookCopy", back_populates="borrows", foreign_keys=[book_copy_id])

    # Relationship to the User who is borrowing the book (Cliente or Funcionario)
    borrower = relationship("User", foreign_keys=[borrower_id], back_populates="borrowed_items")

    # Relationship to the User (Funcionario) who processed the loan
    lender = relationship("User", foreign_keys=[lender_id], back_populates="processed_loans")

# To make these relationships work, we'll need to add `borrows` to BookCopy,
# and `borrowed_items` and `processed_loans` to User in later steps.
