from functools import wraps
from flask import session, redirect, url_for, flash, request, jsonify

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.headers.get('Content-Type') == 'application/json':
                return jsonify({'error': 'Unauthorized'}), 401
            flash('❌ Você precisa fazer login para acessar esta página.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('❌ Você precisa fazer login como administrador para acessar esta página.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def permission_required(permissions=[]):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'admin_id' not in session:
                flash('❌ Você precisa fazer login para acessar esta página.', 'error')
                return redirect(url_for('admin_login'))
            
            user_cargo = session.get('admin_cargo', '').lower()
            
            # Admin tem acesso total
            if user_cargo == 'admin':
                return f(*args, **kwargs)
            
            # Verificar se o cargo tem permissão para a rota
            if user_cargo not in permissions:
                flash('❌ Acesso não autorizado para o seu cargo.', 'error')
                return redirect(url_for('admin_dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Permissões pré-definidas para cada cargo
PERMISSIONS = {
    'admin': ['admin', 'gerente', 'vendedor', 'suporte'],  # Acesso total
    'gerente': ['gerente', 'vendedor', 'suporte'],  # Gestão sem admin
    'vendedor': ['vendedor'],  # Apenas visualização
    'suporte': ['suporte']  # Apenas diagnósticos
}

def customer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'cliente_id' not in session:
            flash('❌ Você precisa fazer login para acessar esta área.', 'error')
            return redirect(url_for('cliente_login'))
        return f(*args, **kwargs)
    return decorated_function

def api_key_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        if not api_key or api_key != Config.API_KEY:
            return jsonify({'error': 'Invalid or missing API key'}), 401
        return f(*args, **kwargs)
    return decorated_function