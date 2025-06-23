import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Configurações do banco de dados
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./biblioteca.db")

# Configurações da aplicação
APP_NAME = "Sistema de Biblioteca"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "API para gerenciamento de biblioteca com empréstimos, livros e usuários"

# Configurações do servidor
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", 5000))
RELOAD = os.getenv("RELOAD", "True").lower() == "true"

# Configurações de segurança
SECRET_KEY = os.getenv("SECRET_KEY", "sua_chave_secreta_aqui")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
