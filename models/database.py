import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash
from config import Config

def get_db_connection():
    try:
        return mysql.connector.connect(**Config.DB_CONFIG)
    except Error as err:
        print(f"Erro ao conectar ao banco de dados: {err}")
        return None

def criar_tabelas_necessarias():
    """Cria tabelas que podem estar faltando no banco de dados"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Erro ao conectar ao banco para criar tabelas")
            return
        
        cursor = conn.cursor()
        
        # Tabela de empresas (se não existir)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS empresas (
                id_empresa INT AUTO_INCREMENT PRIMARY KEY,
                razao_social VARCHAR(255) NOT NULL,
                nome_fantasia VARCHAR(255),
                cnpj VARCHAR(18) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                senha VARCHAR(255) NOT NULL,
                telefone VARCHAR(20),
                tipo_empresa ENUM('comprador', 'vendedor', 'ambos') DEFAULT 'comprador',
                endereco TEXT,
                ativo BOOLEAN DEFAULT TRUE,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabela de produtos_empresa (se não existir)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS produtos_empresa (
                id_produto_empresa INT AUTO_INCREMENT PRIMARY KEY,
                id_empresa INT NOT NULL,
                id_produto INT NOT NULL,
                preco_empresa DECIMAL(10,2) NOT NULL,
                estoque_empresa INT DEFAULT 0,
                ativo BOOLEAN DEFAULT TRUE,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (id_empresa) REFERENCES empresas(id_empresa) ON DELETE CASCADE,
                FOREIGN KEY (id_produto) REFERENCES produto(id_produto) ON DELETE CASCADE,
                UNIQUE KEY unique_empresa_produto (id_empresa, id_produto)
            )
        """)
        
        conn.commit()
        print("✅ Tabelas verificadas/criadas com sucesso!")
        
    except mysql.connector.Error as err:
        print(f"❌ Erro ao criar tabelas: {err}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def criar_admin_padrao():
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Erro ao conectar ao banco para criar admin padrão")
            return
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_funcionario FROM funcionarios WHERE email = 'admin@ghcp.com'")
        admin_existe = cursor.fetchone()
        if not admin_existe:
            senha_hash = generate_password_hash('admin123')
            cursor.execute("""
                INSERT INTO funcionarios (nome, email, senha, cargo, ativo)
                VALUES (%s, %s, %s, %s, %s)
            """, ('Administrador', 'admin@ghcp.com', senha_hash, 'admin', True))
            conn.commit()
            print("✅ Admin padrão criado com sucesso!")
            print("📧 Email: admin@ghcp.com")
            print("🔑 Senha: admin123")
        else:
            print("ℹ️ Admin padrão já existe no banco")
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"❌ Erro ao criar admin padrão: {err}")