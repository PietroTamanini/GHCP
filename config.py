import os
from datetime import timedelta

class Config:
    SECRET_KEY = 'GHCP-2o25'
    
    # Database Configuration
    DB_CONFIG = {
        'host': 'localhost',
        'port': '3306',
        'user': 'root',
        'password': '',
        'database': 'loja_informatica'
    }
    
    # Upload Configuration
    UPLOAD_FOLDER = 'static/uploads/produtos'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # Session Configuration
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    
    # PIX Configuration
    PIX_CHAVE = "14057629939"
    PIX_NOME = "CAETANO GBUR PETRY"
    PIX_CIDADE = "JOINVILLE"