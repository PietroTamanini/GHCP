from flask import Flask
from config import Config
from routes.main_routes import configure_main_routes
from routes.auth_routes import configure_auth_routes
from routes.empresa_routes import configure_empresa_routes
from routes.admin_routes import configure_admin_routes
from routes.produto_routes import configure_produto_routes
from routes.carrinho_routes import configure_carrinho_routes
from utils.helpers import from_json_filter
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Configurar filtros de template
    app.jinja_env.filters['from_json'] = from_json_filter
    
    # Configurar rotas
    configure_main_routes(app)
    configure_auth_routes(app)
    configure_empresa_routes(app)
    configure_admin_routes(app)
    configure_produto_routes(app)
    configure_carrinho_routes(app)
    
    # Garantir que a pasta de uploads existe
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    
    return app

app = create_app()

if __name__ == '__main__':
    from models.database import criar_tabelas_necessarias, criar_admin_padrao
    
    print("=" * 60)
    print("🚀 Loja GHCP - Sistema de E-commerce + Admin + Empresas")
    print("=" * 60)
    
    # Verificar e criar tabelas necessárias
    criar_tabelas_necessarias()
    
    # Criar admin padrão
    criar_admin_padrao()
    
    print("✅ Servidor Flask iniciado com sucesso!")
    print(f"🌐 Site: http://localhost:5000")
    print(f"🛡️ Admin: http://localhost:5000/admin/login")
    print(f"🏢 Empresas: http://localhost:5000/cadastro-empresa")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)