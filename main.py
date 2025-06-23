import uvicorn
from fastapi import FastAPI
from database import engine, Base
from app.routers import empresa as e, book as b, user as u, borrow as br
from app.models import user, empresa, borrow, book
from settings import APP_NAME, APP_VERSION, APP_DESCRIPTION, HOST, PORT, RELOAD

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=APP_DESCRIPTION
)

# Criação das tabelas do banco de dados
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

@app.get("/")
def check_api():
    return {"response": "Api Online!", "version": APP_VERSION}

# Inclusão dos routers
app.include_router(e.router)
app.include_router(b.router)
app.include_router(u.router)
app.include_router(br.router)

if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=RELOAD)
    
    
