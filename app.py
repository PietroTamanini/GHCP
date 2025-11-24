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


app = Flask(__name__)
app.secret_key = 'GHCP-2o25'

@app.template_filter('from_json')
def from_json_filter(value):
    if value:
        try:
            return json.loads(value)
        except:
            return []
    return []

DB_CONFIG = {
    'host': 'localhost',
    'port': '3306',
    'user': 'root',
    'password': '',
    'database': 'loja_informatica'
}

UPLOAD_FOLDER = 'static/uploads/produtos'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hora

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as err:
        print(f"Erro ao conectar ao banco de dados: {err}")
        return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session and 'empresa_id' not in session:
            flash('⚠️ Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('⚠️ Acesso restrito para administradores.', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def validar_cpf(cpf):
    cpf = re.sub(r'\D', '', cpf)
    if len(cpf) != 11:
        return False
    if cpf == cpf[0] * 11:
        return False
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito1 = (soma * 10 % 11) % 10
    if digito1 != int(cpf[9]):
        return False
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito2 = (soma * 10 % 11) % 10
    return digito2 == int(cpf[10])

def validar_cnpj(cnpj):
    cnpj = re.sub(r'\D', '', cnpj)
    if len(cnpj) != 14:
        return False
    if cnpj == cnpj[0] * 14:
        return False
    
    # Validação primeiro dígito
    peso = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * peso[i] for i in range(12))
    digito1 = 11 - (soma % 11)
    digito1 = 0 if digito1 > 9 else digito1
    if digito1 != int(cnpj[12]):
        return False
    
    # Validação segundo dígito
    peso = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * peso[i] for i in range(13))
    digito2 = 11 - (soma % 11)
    digito2 = 0 if digito2 > 9 else digito2
    return digito2 == int(cnpj[13])

def validar_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def formatar_cpf(cpf):
    cpf = re.sub(r'\D', '', cpf)
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

def formatar_cnpj(cnpj):
    cnpj = re.sub(r'\D', '', cnpj)
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"

def formatar_telefone(telefone):
    telefone = re.sub(r'\D', '', telefone)
    if len(telefone) == 11:
        return f"({telefone[:2]}) {telefone[2:7]}-{telefone[7:]}"
    elif len(telefone) == 10:
        return f"({telefone[:2]}) {telefone[2:6]}-{telefone[6:]}"
    return telefone

# ROTAS ORIGINAIS (mantidas)
@app.route('/')
def inicio():
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('index.html', produtos_destaque=[])
        
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT p.* 
            FROM produto p 
            WHERE p.ativo = TRUE 
            ORDER BY p.destaque DESC, p.data_cadastro DESC 
            LIMIT 8
        """)
        produtos_base = cursor.fetchall()
        
        cursor.execute("""
            SELECT o.*, p.nome, p.descricao, p.categoria, p.marca, p.imagens
            FROM ofertas o
            JOIN produto p ON o.id_produto = p.id_produto
            WHERE o.ativa = TRUE 
            AND (o.validade IS NULL OR o.validade >= CURDATE())
            AND p.ativo = TRUE
            ORDER BY o.desconto DESC
            LIMIT 6
        """)
        ofertas = cursor.fetchall()
        
        produtos_destaque = []
        
        for oferta in ofertas:
            produto_com_oferta = {
                'id_produto': oferta['id_produto'],
                'nome': oferta['nome'],
                'descricao': oferta['descricao'],
                'categoria': oferta['categoria'],
                'marca': oferta['marca'],
                'preco': oferta['preco_original'],
                'preco_com_desconto': oferta['preco_com_desconto'],
                'desconto': oferta['desconto'],
                'tem_oferta': True,
                'imagens': oferta['imagens']
            }
            produtos_destaque.append(produto_com_oferta)
        
        produtos_base_ids = [p['id_produto'] for p in produtos_destaque]
        for produto in produtos_base:
            if produto['id_produto'] not in produtos_base_ids and len(produtos_destaque) < 8:
                produto_base = {
                    'id_produto': produto['id_produto'],
                    'nome': produto['nome'],
                    'descricao': produto['descricao'],
                    'categoria': produto['categoria'],
                    'marca': produto['marca'],
                    'preco': produto['preco'],
                    'preco_com_desconto': produto['preco'],
                    'desconto': 0,
                    'tem_oferta': False,
                    'imagens': produto['imagens']
                }
                produtos_destaque.append(produto_base)
        
        return render_template('index.html', produtos_destaque=produtos_destaque)
        
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar produtos: {err}', 'error')
        return render_template('index.html', produtos_destaque=[])
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# NOVA ROTA: Escolha tipo de cadastro (CPF ou CNPJ)
@app.route('/escolher-tipo-cadastro')
def escolher_tipo_cadastro():
    return render_template('escolher_tipo_cadastro.html')

# ROTA DE LOGIN ATUALIZADA
@app.route('/login', methods=['GET', 'POST'])
def login():
    tipo = request.args.get('tipo', 'cliente')
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        tipo_login = request.form.get('tipo_login', 'cliente')  # cliente ou empresa
        
        if not email or not senha:
            flash('❌ Por favor, preencha todos os campos.', 'error')
            return render_template('login.html')
        
        if not validar_email(email):
            flash('❌ E-mail inválido.', 'error')
            return render_template('login.html')
        
        try:
            conn = get_db_connection()
            if not conn:
                flash('Erro ao conectar ao banco de dados.', 'error')
                return render_template('login.html')
            
            cursor = conn.cursor(dictionary=True)
            
            if tipo_login == 'empresa':
                cursor.execute("SELECT id_empresa, razao_social, nome_fantasia, email, senha, ativo, tipo_empresa FROM empresas WHERE email = %s", (email,))
                usuario = cursor.fetchone()
                
                if usuario and check_password_hash(usuario['senha'], senha):
                    if not usuario['ativo']:
                        flash('⚠️ Sua empresa está desativada. Entre em contato com o suporte.', 'warning')
                        return render_template('login.html')
                    
                    session['empresa_id'] = usuario['id_empresa']
                    session['empresa_nome'] = usuario['nome_fantasia'] or usuario['razao_social']
                    session['empresa_email'] = usuario['email']
                    session['empresa_tipo'] = usuario['tipo_empresa']
                    
                    flash(f'🎉 Bem-vindo, {session["empresa_nome"]}!', 'success')
                    return redirect(url_for('painel_empresa'))
                else:
                    flash('❌ E-mail ou senha incorretos.', 'error')
            else:
                cursor.execute("SELECT id_cliente, nome, email, senha, ativo FROM clientes WHERE email = %s", (email,))
                usuario = cursor.fetchone()
                
                if usuario and check_password_hash(usuario['senha'], senha):
                    if not usuario['ativo']:
                        flash('⚠️ Sua conta está desativada. Entre em contato com o suporte.', 'warning')
                        return render_template('login.html')
                    
                    session['usuario_id'] = usuario['id_cliente']
                    session['usuario_nome'] = usuario['nome']
                    session['usuario_email'] = usuario['email']
                    
                    flash(f'🎉 Bem-vindo de volta, {usuario["nome"]}!', 'success')
                    next_page = request.args.get('next')
                    if next_page:
                        return redirect(next_page)
                    return redirect(url_for('inicio'))
                else:
                    flash('❌ E-mail ou senha incorretos.', 'error')
        
        except mysql.connector.Error as err:
            flash(f'Erro ao fazer login: {err}', 'error')
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    return render_template('login.html')

# ROTA CADASTRO CLIENTE (mantida)
@app.route('/cadastro', methods=['POST'])
def cadastro():
    nome = request.form.get('nome', '').strip()
    email = request.form.get('email', '').strip().lower()
    cpf = request.form.get('cpf', '').strip()
    telefone = request.form.get('telefone', '').strip()
    data_nascimento = request.form.get('data_nascimento')
    genero = request.form.get('genero')
    senha = request.form.get('senha', '')
    confirmar_senha = request.form.get('confirmar_senha', '')
    aceitar_termos = request.form.get('aceitar_termos')
    
    if not all([nome, email, cpf, senha, confirmar_senha]):
        flash('❌ Por favor, preencha todos os campos obrigatórios.', 'error')
        return redirect(url_for('login'))
    
    if not aceitar_termos:
        flash('❌ Você precisa aceitar os Termos de Uso e Política de Privacidade.', 'error')
        return redirect(url_for('login'))
    
    if senha != confirmar_senha:
        flash('❌ As senhas não coincidem.', 'error')
        return redirect(url_for('login'))
    
    if len(senha) < 6:
        flash('❌ A senha deve ter no mínimo 6 caracteres.', 'error')
        return redirect(url_for('login'))
    
    if not validar_email(email):
        flash('❌ E-mail inválido.', 'error')
        return redirect(url_for('login'))
    
    if not validar_cpf(cpf):
        flash('❌ CPF inválido.', 'error')
        return redirect(url_for('login'))
    
    cpf_formatado = formatar_cpf(cpf)
    
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('login'))
        
        cursor = conn.cursor()
        
        cursor.execute("SELECT id_cliente FROM clientes WHERE email = %s", (email,))
        if cursor.fetchone():
            flash('❌ Este e-mail já está cadastrado.', 'error')
            return redirect(url_for('login'))
        
        cursor.execute("SELECT id_cliente FROM clientes WHERE cpf = %s", (cpf_formatado,))
        if cursor.fetchone():
            flash('❌ Este CPF já está cadastrado.', 'error')
            return redirect(url_for('login'))
        
        senha_hash = generate_password_hash(senha)
        
        cursor.execute("""
            INSERT INTO clientes (nome, email, senha, cpf, telefone, data_nascimento, genero)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (nome, email, senha_hash, cpf_formatado, telefone, data_nascimento if data_nascimento else None, genero if genero else None))
        
        conn.commit()
        cliente_id = cursor.lastrowid
        
        cursor.execute("INSERT INTO preferencias (id_cliente, email_notificacoes, ofertas_personalizadas) VALUES (%s, TRUE, TRUE)", (cliente_id,))
        conn.commit()
        
        session['usuario_id'] = cliente_id
        session['usuario_nome'] = nome
        session['usuario_email'] = email
        
        flash(f'🎉 Cadastro realizado com sucesso! Bem-vindo, {nome}!', 'success')
        return redirect(url_for('inicio'))
    
    except mysql.connector.Error as err:
        flash(f'Erro ao cadastrar: {err}', 'error')
        return redirect(url_for('login'))
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# Rota específica para login de empresas
@app.route('/login_empresa', methods=['GET', 'POST'])
def login_empresa():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        
        if not email or not senha:
            flash('❌ Por favor, preencha todos os campos.', 'error')
            return render_template('login_empresa.html', form_type='login')
        
        if not validar_email(email):
            flash('❌ E-mail inválido.', 'error')
            return render_template('login_empresa.html', form_type='login')
        
        try:
            conn = get_db_connection()
            if not conn:
                flash('Erro ao conectar ao banco de dados.', 'error')
                return render_template('login_empresa.html', form_type='login')
            
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("SELECT id_empresa, razao_social, nome_fantasia, email, senha, ativo, tipo_empresa FROM empresas WHERE email = %s", (email,))
            usuario = cursor.fetchone()
            
            if usuario and check_password_hash(usuario['senha'], senha):
                if not usuario['ativo']:
                    flash('⚠️ Sua empresa está desativada. Entre em contato com o suporte.', 'warning')
                    return render_template('login_empresa.html', form_type='login')
                
                session['empresa_id'] = usuario['id_empresa']
                session['empresa_nome'] = usuario['nome_fantasia'] or usuario['razao_social']
                session['empresa_email'] = usuario['email']
                session['empresa_tipo'] = usuario['tipo_empresa']
                
                flash(f'🎉 Bem-vindo, {session["empresa_nome"]}!', 'success')
                return redirect(url_for('painel_empresa'))
            else:
                flash('❌ E-mail ou senha incorretos.', 'error')
        
        except mysql.connector.Error as err:
            flash(f'Erro ao fazer login: {err}', 'error')
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    return render_template('login_empresa.html', form_type='login')

# ROTA: Buscar avaliações da empresa (AJAX)
@app.route('/api/avaliacoes-empresa/<int:id_empresa>')
def api_avaliacoes_empresa(id_empresa):
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify([])
        
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT ae.*, 
                   COALESCE(c.nome, e.nome_fantasia, e.razao_social) as avaliador_nome
            FROM avaliacoes_empresas ae
            LEFT JOIN clientes c ON ae.id_cliente = c.id_cliente
            LEFT JOIN empresas e ON ae.id_empresa_avaliadora = e.id_empresa
            WHERE ae.id_empresa_avaliada = %s AND ae.aprovado = TRUE
            ORDER BY ae.data_avaliacao DESC
            LIMIT 10
        """, (id_empresa,))
        
        avaliacoes = cursor.fetchall()
        
        return jsonify(avaliacoes)
    
    except mysql.connector.Error:
        return jsonify([])
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# Rota específica para cadastro de empresas
@app.route('/cadastro_empresa', methods=['GET', 'POST'])
def cadastro_empresa():
    if request.method == 'POST':
        razao_social = request.form.get('razao_social', '').strip()
        nome_fantasia = request.form.get('nome_fantasia', '').strip()
        cnpj = request.form.get('cnpj', '').strip()
        email = request.form.get('email', '').strip().lower()
        telefone = request.form.get('telefone', '').strip()
        tipo_empresa = request.form.get('tipo_empresa', 'comprador')
        endereco = request.form.get('endereco', '').strip()
        senha = request.form.get('senha', '')
        confirmar_senha = request.form.get('confirmar_senha', '')
        aceitar_termos = request.form.get('aceitar_termos')
        
        if not all([razao_social, cnpj, email, senha, confirmar_senha, tipo_empresa]):
            flash('❌ Por favor, preencha todos os campos obrigatórios.', 'error')
            return render_template('login_empresa.html', form_type='cadastro')
        
        if not aceitar_termos:
            flash('❌ Você precisa aceitar os Termos de Uso e Política de Privacidade.', 'error')
            return render_template('login_empresa.html', form_type='cadastro')
        
        if senha != confirmar_senha:
            flash('❌ As senhas não coincidem.', 'error')
            return render_template('login_empresa.html', form_type='cadastro')
        
        if len(senha) < 6:
            flash('❌ A senha deve ter no mínimo 6 caracteres.', 'error')
            return render_template('login_empresa.html', form_type='cadastro')
        
        if not validar_email(email):
            flash('❌ E-mail inválido.', 'error')
            return render_template('login_empresa.html', form_type='cadastro')
        
        if not validar_cnpj(cnpj):
            flash('❌ CNPJ inválido.', 'error')
            return render_template('login_empresa.html', form_type='cadastro')
        
        cnpj_formatado = formatar_cnpj(cnpj)
        
        try:
            conn = get_db_connection()
            if not conn:
                flash('Erro ao conectar ao banco de dados.', 'error')
                return render_template('login_empresa.html', form_type='cadastro')
            
            cursor = conn.cursor()
            
            cursor.execute("SELECT id_empresa FROM empresas WHERE email = %s", (email,))
            if cursor.fetchone():
                flash('❌ Este e-mail já está cadastrado.', 'error')
                return render_template('login_empresa.html', form_type='cadastro')
            
            cursor.execute("SELECT id_empresa FROM empresas WHERE cnpj = %s", (cnpj_formatado,))
            if cursor.fetchone():
                flash('❌ Este CNPJ já está cadastrado.', 'error')
                return render_template('login_empresa.html', form_type='cadastro')
            
            senha_hash = generate_password_hash(senha)
            
            cursor.execute("""
                INSERT INTO empresas (razao_social, nome_fantasia, cnpj, email, senha, telefone, tipo_empresa, endereco)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (razao_social, nome_fantasia, cnpj_formatado, email, senha_hash, telefone, tipo_empresa, endereco))
            
            conn.commit()
            empresa_id = cursor.lastrowid
            
            session['empresa_id'] = empresa_id
            session['empresa_nome'] = nome_fantasia or razao_social
            session['empresa_email'] = email
            session['empresa_tipo'] = tipo_empresa
            
            flash(f'🎉 Cadastro realizado com sucesso! Bem-vindo, {session["empresa_nome"]}!', 'success')
            return redirect(url_for('painel_empresa'))
        
        except mysql.connector.Error as err:
            flash(f'Erro ao cadastrar empresa: {err}', 'error')
            return render_template('login_empresa.html', form_type='cadastro')
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    return render_template('login_empresa.html', form_type='cadastro')

@app.route('/empresas-vendedoras')
def empresas_vendedoras():
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('empresas_vendedoras.html', empresas=[])
        
        cursor = conn.cursor(dictionary=True)
        
        # Verificar se o usuário já comprou em alguma loja
        usuario_comprou_em_lojas = []
        if 'usuario_id' in session:
            cursor.execute("""
                SELECT DISTINCT e.id_empresa
                FROM pedidos p
                JOIN itens_pedido ip ON p.id_pedido = ip.id_pedido
                JOIN produtos_empresa pe ON ip.id_produto = pe.id_produto
                JOIN empresas e ON pe.id_empresa = e.id_empresa
                WHERE p.id_cliente = %s AND p.status = 'concluido'
            """, (session['usuario_id'],))
            usuario_comprou_em_lojas = [row['id_empresa'] for row in cursor.fetchall()]
        
        # Buscar empresas vendedoras com estatísticas
        cursor.execute("""
            SELECT 
                e.id_empresa,
                e.nome_fantasia,
                e.razao_social,
                e.cnpj,
                e.email,
                e.telefone,
                e.tipo_empresa,
                e.endereco,
                e.data_cadastro,
                COUNT(DISTINCT pe.id_produto) as total_produtos,
                COALESCE(AVG(ae.nota), 0) as media_avaliacoes,
                COUNT(DISTINCT ae.id_avaliacao) as total_avaliacoes,
                COUNT(DISTINCT p.id_pedido) as total_vendas
            FROM empresas e
            LEFT JOIN produtos_empresa pe ON e.id_empresa = pe.id_empresa AND pe.ativo = TRUE
            LEFT JOIN avaliacoes_empresas ae ON e.id_empresa = ae.id_empresa_avaliada AND ae.aprovado = TRUE
            LEFT JOIN (
                SELECT DISTINCT pe2.id_empresa, p2.id_pedido
                FROM pedidos p2
                JOIN itens_pedido ip ON p2.id_pedido = ip.id_pedido
                JOIN produtos_empresa pe2 ON ip.id_produto = pe2.id_produto
                WHERE p2.status = 'concluido'
            ) p ON e.id_empresa = p.id_empresa
            WHERE e.tipo_empresa IN ('vendedor', 'ambos') AND e.ativo = TRUE
            GROUP BY e.id_empresa
            ORDER BY media_avaliacoes DESC, total_produtos DESC
        """)
        
        empresas_db = cursor.fetchall()
        
        # Processar dados das empresas corretamente
        empresas_processadas = []
        for empresa in empresas_db:
            nome_exibicao = empresa['nome_fantasia'] or empresa['razao_social']
            
            # Calcular tempo no mercado
            tempo_mercado = 0
            if empresa['data_cadastro']:
                from datetime import datetime
                tempo_mercado = (datetime.now() - empresa['data_cadastro']).days // 365
            
            # Garantir que os valores não sejam None
            media_avaliacoes = empresa['media_avaliacoes'] or 0
            total_produtos = empresa['total_produtos'] or 0
            total_vendas = empresa['total_vendas'] or 0
            total_avaliacoes = empresa['total_avaliacoes'] or 0
            
            empresas_processadas.append({
                'id': empresa['id_empresa'],
                'nome': nome_exibicao,
                'categoria': 'Tecnologia',
                'descricao': f"CNPJ: {empresa['cnpj']} | Telefone: {empresa['telefone'] or 'Não informado'}",
                'logo': nome_exibicao[0].upper() if nome_exibicao else 'E',
                'avaliacao': round(float(media_avaliacoes), 1),
                'total_avaliacoes': total_avaliacoes,
                'total_produtos': total_produtos,
                'total_vendas': total_vendas,
                'tempo_mercado': f"{tempo_mercado} ano(s)" if tempo_mercado > 0 else "Menos de 1 ano",
                'features': ["🚚 Entrega Rápida", "💳 Parcelamento", "🛡️ Garantia"],
                'pode_avaliar': empresa['id_empresa'] in usuario_comprou_em_lojas if 'usuario_id' in session else False
            })
        
        return render_template('empresas_vendedoras.html', 
                             empresas=empresas_processadas,
                             usuario_comprou_em_lojas=usuario_comprou_em_lojas)
    
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar empresas: {err}', 'error')
        return render_template('empresas_vendedoras.html', empresas=[])
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/painel-empresa')
@login_required
def painel_empresa():
    if 'empresa_id' not in session:
        flash('⚠️ Acesso restrito para empresas.', 'warning')
        return redirect(url_for('login'))
    
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('inicio'))
        
        cursor = conn.cursor(dictionary=True)
        
        # Buscar dados da empresa
        cursor.execute("SELECT * FROM empresas WHERE id_empresa = %s", (session['empresa_id'],))
        empresa = cursor.fetchone()
        
        if not empresa:
            flash('Erro ao carregar dados da empresa.', 'error')
            return redirect(url_for('inicio'))
        
        # Buscar produtos da empresa
        cursor.execute("""
            SELECT pe.*, p.nome, p.marca, p.categoria, p.imagens
            FROM produtos_empresa pe
            JOIN produto p ON pe.id_produto = p.id_produto
            WHERE pe.id_empresa = %s
            ORDER BY pe.data_cadastro DESC
        """, (session['empresa_id'],))
        produtos_empresa = cursor.fetchall()
        
        # Processar imagens
        for produto in produtos_empresa:
            if produto.get('imagens'):
                try:
                    produto['imagens'] = json.loads(produto['imagens'])
                except:
                    produto['imagens'] = []
        
        # Buscar produtos disponíveis para adicionar
        cursor.execute("""
            SELECT p.id_produto, p.nome, p.marca, p.preco, p.categoria
            FROM produto p 
            WHERE p.ativo = TRUE 
            AND p.id_produto NOT IN (
                SELECT pe.id_produto FROM produtos_empresa pe 
                WHERE pe.id_empresa = %s AND pe.ativo = TRUE
            )
            ORDER BY p.nome
            LIMIT 50
        """, (session['empresa_id'],))
        produtos_disponiveis = cursor.fetchall()
        
        # Buscar estatísticas
        cursor.execute("""
            SELECT COUNT(*) as total_vendas, COALESCE(SUM(total), 0) as receita_total
            FROM pedidos WHERE id_cliente IN (
                SELECT id_cliente FROM clientes WHERE email = %s
            )
        """, (empresa['email'],))
        stats = cursor.fetchone()
        
        # Buscar avaliações da empresa
        cursor.execute("""
            SELECT ae.*, COALESCE(c.nome, e.nome_fantasia, e.razao_social) as avaliador_nome
            FROM avaliacoes_empresas ae
            LEFT JOIN clientes c ON ae.id_cliente = c.id_cliente
            LEFT JOIN empresas e ON ae.id_empresa_avaliadora = e.id_empresa
            WHERE ae.id_empresa_avaliada = %s AND ae.aprovado = TRUE
            ORDER BY ae.data_avaliacao DESC
            LIMIT 10
        """, (session['empresa_id'],))
        avaliacoes = cursor.fetchall()
        
        # Calcular média de avaliações
        cursor.execute("""
            SELECT AVG(nota) as media_notas, COUNT(*) as total_avaliacoes
            FROM avaliacoes_empresas
            WHERE id_empresa_avaliada = %s AND aprovado = TRUE
        """, (session['empresa_id'],))
        media_avaliacoes = cursor.fetchone()
        
        return render_template('painel_empresa.html', 
                             empresa=empresa,
                             produtos_empresa=produtos_empresa,
                             produtos_disponiveis=produtos_disponiveis,
                             stats=stats,
                             avaliacoes=avaliacoes,
                             media_avaliacoes=media_avaliacoes)
    
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar painel: {err}', 'error')
        return redirect(url_for('inicio'))
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            
# ROTA: Buscar produtos disponíveis para empresa
@app.route('/api/produtos-disponiveis')
@login_required
def api_produtos_disponiveis():
    if 'empresa_id' not in session:
        return jsonify({'error': 'Acesso não autorizado'}), 403
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Erro de conexão'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Buscar produtos que ainda não foram adicionados pela empresa
        cursor.execute("""
            SELECT p.id_produto, p.nome, p.marca, p.preco, p.estoque, p.categoria, p.imagens
            FROM produto p 
            WHERE p.ativo = TRUE 
            AND p.id_produto NOT IN (
                SELECT pe.id_produto FROM produtos_empresa pe 
                WHERE pe.id_empresa = %s AND pe.ativo = TRUE
            )
            ORDER BY p.nome
        """, (session['empresa_id'],))
        
        produtos = cursor.fetchall()
        
        # Processar imagens
        for produto in produtos:
            if produto.get('imagens'):
                try:
                    produto['imagens'] = json.loads(produto['imagens'])
                except:
                    produto['imagens'] = []
        
        return jsonify(produtos)
    
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# ROTA: Adicionar produto à empresa
@app.route('/empresa/adicionar-produto', methods=['POST'])
@login_required
def adicionar_produto_empresa():
    if 'empresa_id' not in session:
        flash('❌ Acesso não autorizado.', 'error')
        return redirect(url_for('painel_empresa'))
    
    try:
        id_produto = request.form.get('id_produto', type=int)
        preco_empresa = request.form.get('preco_empresa', type=float)
        estoque_empresa = request.form.get('estoque_empresa', type=int)
        ativo = request.form.get('ativo') == 'on'
        
        if not all([id_produto, preco_empresa is not None, estoque_empresa is not None]):
            flash('❌ Preencha todos os campos obrigatórios.', 'error')
            return redirect(url_for('painel_empresa'))
        
        conn = get_db_connection()
        if not conn:
            flash('❌ Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('painel_empresa'))
        
        cursor = conn.cursor()
        
        # Verificar se produto já foi adicionado
        cursor.execute("""
            SELECT id_produto_empresa FROM produtos_empresa 
            WHERE id_empresa = %s AND id_produto = %s
        """, (session['empresa_id'], id_produto))
        
        if cursor.fetchone():
            flash('⚠️ Este produto já foi adicionado à sua loja.', 'warning')
            return redirect(url_for('painel_empresa'))
        
        # Inserir produto na loja da empresa
        cursor.execute("""
            INSERT INTO produtos_empresa (id_empresa, id_produto, preco_empresa, estoque_empresa, ativo)
            VALUES (%s, %s, %s, %s, %s)
        """, (session['empresa_id'], id_produto, preco_empresa, estoque_empresa, ativo))
        
        conn.commit()
        
        flash('✅ Produto adicionado à sua loja com sucesso!', 'success')
        return redirect(url_for('painel_empresa'))
    
    except mysql.connector.Error as err:
        flash(f'❌ Erro ao adicionar produto: {err}', 'error')
        return redirect(url_for('painel_empresa'))
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# ROTA: Remover produto da empresa
@app.route('/empresa/remover-produto/<int:id_produto_empresa>', methods=['POST'])
@login_required
def remover_produto_empresa(id_produto_empresa):
    if 'empresa_id' not in session:
        flash('❌ Acesso não autorizado.', 'error')
        return redirect(url_for('painel_empresa'))
    
    try:
        conn = get_db_connection()
        if not conn:
            flash('❌ Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('painel_empresa'))
        
        cursor = conn.cursor()
        
        # Verificar se o produto pertence à empresa
        cursor.execute("""
            SELECT id_produto_empresa FROM produtos_empresa 
            WHERE id_produto_empresa = %s AND id_empresa = %s
        """, (id_produto_empresa, session['empresa_id']))
        
        if not cursor.fetchone():
            flash('❌ Produto não encontrado.', 'error')
            return redirect(url_for('painel_empresa'))
        
        # Remover produto
        cursor.execute("""
            DELETE FROM produtos_empresa 
            WHERE id_produto_empresa = %s AND id_empresa = %s
        """, (id_produto_empresa, session['empresa_id']))
        
        conn.commit()
        
        flash('🗑️ Produto removido da sua loja com sucesso!', 'success')
        return redirect(url_for('painel_empresa'))
    
    except mysql.connector.Error as err:
        flash(f'❌ Erro ao remover produto: {err}', 'error')
        return redirect(url_for('painel_empresa'))
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# ROTA: Atualizar produto da empresa
@app.route('/empresa/atualizar-produto/<int:id_produto_empresa>', methods=['POST'])
@login_required
def atualizar_produto_empresa(id_produto_empresa):
    if 'empresa_id' not in session:
        return jsonify({'success': False, 'error': 'Acesso não autorizado'}), 403
    
    try:
        data = request.get_json()
        preco_empresa = data.get('preco_empresa')
        estoque_empresa = data.get('estoque_empresa')
        ativo = data.get('ativo')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro de conexão'}), 500
        
        cursor = conn.cursor()
        
        # Atualizar produto
        cursor.execute("""
            UPDATE produtos_empresa 
            SET preco_empresa = %s, estoque_empresa = %s, ativo = %s
            WHERE id_produto_empresa = %s AND id_empresa = %s
        """, (preco_empresa, estoque_empresa, ativo, id_produto_empresa, session['empresa_id']))
        
        conn.commit()
        
        return jsonify({'success': True, 'message': 'Produto atualizado com sucesso!'})
    
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'error': str(err)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()    

# NOVA ROTA: Avaliar Produto
@app.route('/avaliar-produto/<int:id_produto>', methods=['POST'])
@login_required
def avaliar_produto(id_produto):
    nota = request.form.get('nota', type=int)
    titulo = request.form.get('titulo', '').strip()
    comentario = request.form.get('comentario', '').strip()
    
    if not nota or nota < 1 or nota > 5:
        flash('❌ Nota inválida. Deve ser entre 1 e 5.', 'error')
        return redirect(url_for('detalhes_produto', id_produto=id_produto))
    
    if not comentario:
        flash('❌ Por favor, escreva um comentário.', 'error')
        return redirect(url_for('detalhes_produto', id_produto=id_produto))
    
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('detalhes_produto', id_produto=id_produto))
        
        cursor = conn.cursor()
        
        if 'usuario_id' in session:
            # Verificar se já avaliou
            cursor.execute("SELECT id_avaliacao FROM avaliacoes WHERE id_cliente = %s AND id_produto = %s", 
                         (session['usuario_id'], id_produto))
            if cursor.fetchone():
                flash('⚠️ Você já avaliou este produto.', 'warning')
                return redirect(url_for('detalhes_produto', id_produto=id_produto))
            
            cursor.execute("""
                INSERT INTO avaliacoes (id_cliente, id_produto, nota, titulo, comentario, tipo_avaliador)
                VALUES (%s, %s, %s, %s, %s, 'cliente')
            """, (session['usuario_id'], id_produto, nota, titulo, comentario))
        
        elif 'empresa_id' in session:
            cursor.execute("SELECT id_avaliacao FROM avaliacoes WHERE id_empresa = %s AND id_produto = %s", 
                         (session['empresa_id'], id_produto))
            if cursor.fetchone():
                flash('⚠️ Sua empresa já avaliou este produto.', 'warning')
                return redirect(url_for('detalhes_produto', id_produto=id_produto))
            
            cursor.execute("""
                INSERT INTO avaliacoes (id_empresa, id_produto, nota, titulo, comentario, tipo_avaliador)
                VALUES (%s, %s, %s, %s, %s, 'empresa')
            """, (session['empresa_id'], id_produto, nota, titulo, comentario))
        
        conn.commit()
        flash('✅ Avaliação enviada com sucesso! Será analisada pela nossa equipe.', 'success')
    
    except mysql.connector.Error as err:
        flash(f'Erro ao enviar avaliação: {err}', 'error')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    
    return redirect(url_for('detalhes_produto', id_produto=id_produto))

# NOVA ROTA: Avaliar Empresa
@app.route('/avaliar-empresa/<int:id_empresa>', methods=['POST'])
@login_required
def avaliar_empresa(id_empresa):
    nota = request.form.get('nota', type=int)
    titulo = request.form.get('titulo', '').strip()
    comentario = request.form.get('comentario', '').strip()
    
    if not nota or nota < 1 or nota > 5:
        flash('❌ Nota inválida. Deve ser entre 1 e 5.', 'error')
        return redirect(request.referrer or url_for('inicio'))
    
    if not comentario:
        flash('❌ Por favor, escreva um comentário.', 'error')
        return redirect(request.referrer or url_for('inicio'))
    
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(request.referrer or url_for('inicio'))
        
        cursor = conn.cursor()
        
        if 'usuario_id' in session:
            cursor.execute("""
                SELECT id_avaliacao FROM avaliacoes_empresas 
                WHERE id_cliente = %s AND id_empresa_avaliada = %s
            """, (session['usuario_id'], id_empresa))
            
            if cursor.fetchone():
                flash('⚠️ Você já avaliou esta empresa.', 'warning')
                return redirect(request.referrer or url_for('inicio'))
            
            cursor.execute("""
                INSERT INTO avaliacoes_empresas (id_empresa_avaliada, id_cliente, nota, titulo, comentario)
                VALUES (%s, %s, %s, %s, %s)
            """, (id_empresa, session['usuario_id'], nota, titulo, comentario))
        
        elif 'empresa_id' in session:
            if session['empresa_id'] == id_empresa:
                flash('❌ Você não pode avaliar sua própria empresa.', 'error')
                return redirect(request.referrer or url_for('inicio'))
            
            cursor.execute("""
                SELECT id_avaliacao FROM avaliacoes_empresas 
                WHERE id_empresa_avaliadora = %s AND id_empresa_avaliada = %s
            """, (session['empresa_id'], id_empresa))
            
            if cursor.fetchone():
                flash('⚠️ Sua empresa já avaliou esta empresa.', 'warning')
                return redirect(request.referrer or url_for('inicio'))
            
            cursor.execute("""
                INSERT INTO avaliacoes_empresas (id_empresa_avaliada, id_empresa_avaliadora, nota, titulo, comentario)
                VALUES (%s, %s, %s, %s, %s)
            """, (id_empresa, session['empresa_id'], nota, titulo, comentario))
        
        conn.commit()
        flash('✅ Avaliação enviada com sucesso!', 'success')
    
    except mysql.connector.Error as err:
        flash(f'Erro ao enviar avaliação: {err}', 'error')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    
    return redirect(request.referrer or url_for('inicio'))

# ROTA DE LOGOUT ATUALIZADA
@app.route('/logout')
@login_required
def logout():
    nome = session.get('usuario_nome') or session.get('empresa_nome', 'Usuário')
    session.clear()
    flash(f'👋 Até logo, {nome}! Volte sempre.', 'info')
    return redirect(url_for('inicio'))

# CONTINUA COM AS ROTAS ORIGINAIS...
@app.route('/recuperar-senha', methods=['GET', 'POST'])
def recuperar_senha():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if not email:
            flash('❌ Por favor, informe seu e-mail.', 'error')
            return render_template('recuperar_senha.html')
        if not validar_email(email):
            flash('❌ E-mail inválido.', 'error')
            return render_template('recuperar_senha.html')
        try:
            conn = get_db_connection()
            if not conn:
                flash('Erro ao conectar ao banco de dados.', 'error')
                return render_template('recuperar_senha.html')
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id_cliente, nome, ativo FROM clientes WHERE email = %s", (email,))
            usuario = cursor.fetchone()
            if usuario:
                if not usuario['ativo']:
                    flash('⚠️ Esta conta está desativada. Entre em contato com o suporte.', 'warning')
                    return render_template('recuperar_senha.html')
                flash('✅ Se o e-mail estiver cadastrado, você receberá as instruções de recuperação em breve.', 'success')
                print(f"[RECUPERAÇÃO] Solicitação para: {email} - {usuario['nome']}")
            else:
                flash('✅ Se o e-mail estiver cadastrado, você receberá as instruções de recuperação em breve.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash(f'Erro ao processar solicitação: {err}', 'error')
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    return render_template('recuperar_senha.html')

@app.route('/minha-conta')
@login_required
def minha_conta():
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('inicio'))
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.*, COUNT(DISTINCT p.id_pedido) as total_pedidos,
            COALESCE(SUM(CASE WHEN p.status != 'cancelado' THEN p.total ELSE 0 END), 0) as total_gasto
            FROM clientes c LEFT JOIN pedidos p ON c.id_cliente = p.id_cliente
            WHERE c.id_cliente = %s GROUP BY c.id_cliente
        """, (session['usuario_id'],))
        cliente = cursor.fetchone()
        if not cliente:
            flash('Erro ao carregar dados do usuário.', 'error')
            return redirect(url_for('inicio'))
        cursor.execute("SELECT * FROM pedidos WHERE id_cliente = %s ORDER BY data_pedido DESC LIMIT 5", (session['usuario_id'],))
        pedidos = cursor.fetchall()
        cursor.execute("SELECT * FROM enderecos WHERE id_cliente = %s ORDER BY principal DESC, data_criacao DESC", (session['usuario_id'],))
        enderecos = cursor.fetchall()
        cursor.execute("SELECT * FROM preferencias WHERE id_cliente = %s", (session['usuario_id'],))
        preferencias = cursor.fetchone()
        return render_template('minha_conta.html', cliente=cliente, usuario=cliente, pedidos=pedidos, enderecos=enderecos, preferencias=preferencias)
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar dados: {err}', 'error')
        return redirect(url_for('inicio'))
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/atualizar_dados', methods=['POST'])
@login_required
def atualizar_dados():
    nome = request.form.get('nome', '').strip()
    telefone = request.form.get('telefone', '').strip()
    data_nascimento = request.form.get('data_nascimento')
    genero = request.form.get('genero')
    if not nome:
        flash('❌ O nome é obrigatório.', 'error')
        return redirect(url_for('minha_conta'))
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('minha_conta'))
        cursor = conn.cursor()
        cursor.execute("UPDATE clientes SET nome = %s, telefone = %s, data_nascimento = %s, genero = %s WHERE id_cliente = %s",
                      (nome, telefone, data_nascimento if data_nascimento else None, genero if genero else None, session['usuario_id']))
        conn.commit()
        session['usuario_nome'] = nome
        flash('✅ Dados atualizados com sucesso!', 'success')
    except mysql.connector.Error as err:
        flash(f'Erro ao atualizar dados: {err}', 'error')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return redirect(url_for('minha_conta'))

@app.route('/alterar_senha', methods=['POST'])
@login_required
def alterar_senha():
    senha_atual = request.form.get('senha_atual', '')
    nova_senha = request.form.get('nova_senha', '')
    confirmar_senha = request.form.get('confirmar_senha', '')
    if not all([senha_atual, nova_senha, confirmar_senha]):
        flash('❌ Preencha todos os campos de senha.', 'error')
        return redirect(url_for('minha_conta'))
    if nova_senha != confirmar_senha:
        flash('❌ A nova senha e a confirmação não coincidem.', 'error')
        return redirect(url_for('minha_conta'))
    if len(nova_senha) < 6:
        flash('❌ A nova senha deve ter no mínimo 6 caracteres.', 'error')
        return redirect(url_for('minha_conta'))
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('minha_conta'))
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT senha FROM clientes WHERE id_cliente = %s", (session['usuario_id'],))
        resultado = cursor.fetchone()
        if not resultado or not check_password_hash(resultado['senha'], senha_atual):
            flash('❌ Senha atual incorreta.', 'error')
            return redirect(url_for('minha_conta'))
        nova_senha_hash = generate_password_hash(nova_senha)
        cursor.execute("UPDATE clientes SET senha = %s WHERE id_cliente = %s", (nova_senha_hash, session['usuario_id']))
        conn.commit()
        flash('🔐 Senha alterada com sucesso!', 'success')
    except mysql.connector.Error as err:
        flash(f'Erro ao alterar senha: {err}', 'error')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return redirect(url_for('minha_conta'))

@app.route('/adicionar_endereco', methods=['POST'])
@login_required
def adicionar_endereco():
    tipo = request.form.get('tipo', 'Casa')
    destinatario = request.form.get('destinatario', '').strip()
    cep = request.form.get('cep', '').strip()
    estado = request.form.get('estado', '').strip().upper()
    cidade = request.form.get('cidade', '').strip()
    bairro = request.form.get('bairro', '').strip()
    rua = request.form.get('rua', '').strip()
    numero = request.form.get('numero', '').strip()
    complemento = request.form.get('complemento', '').strip()
    principal = request.form.get('principal') == 'on'
    if not all([destinatario, cep, estado, cidade, bairro, rua, numero]):
        flash('❌ Preencha todos os campos obrigatórios do endereço.', 'error')
        return redirect(url_for('minha_conta'))
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('minha_conta'))
        cursor = conn.cursor()
        if principal:
            cursor.execute("UPDATE enderecos SET principal = FALSE WHERE id_cliente = %s", (session['usuario_id'],))
        cursor.execute("""
            INSERT INTO enderecos (id_cliente, tipo, destinatario, cep, estado, cidade, bairro, rua, numero, complemento, principal)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (session['usuario_id'], tipo, destinatario, cep, estado, cidade, bairro, rua, numero, complemento if complemento else None, principal))
        conn.commit()
        flash('📍 Endereço adicionado com sucesso!', 'success')
    except mysql.connector.Error as err:
        flash(f'Erro ao adicionar endereço: {err}', 'error')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return redirect(url_for('minha_conta'))

@app.route('/editar_endereco/<int:id_endereco>', methods=['POST'])
@login_required
def editar_endereco(id_endereco):
    tipo = request.form.get('tipo', 'Casa')
    destinatario = request.form.get('destinatario', '').strip()
    cep = request.form.get('cep', '').strip()
    estado = request.form.get('estado', '').strip().upper()
    cidade = request.form.get('cidade', '').strip()
    bairro = request.form.get('bairro', '').strip()
    rua = request.form.get('rua', '').strip()
    numero = request.form.get('numero', '').strip()
    complemento = request.form.get('complemento', '').strip()
    principal = request.form.get('principal') == 'on'
    if not all([destinatario, cep, estado, cidade, bairro, rua, numero]):
        flash('❌ Preencha todos os campos obrigatórios do endereço.', 'error')
        return redirect(url_for('minha_conta'))
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('minha_conta'))
        cursor = conn.cursor()
        cursor.execute("SELECT id_endereco FROM enderecos WHERE id_endereco = %s AND id_cliente = %s", (id_endereco, session['usuario_id']))
        if not cursor.fetchone():
            flash('❌ Endereço não encontrado.', 'error')
            return redirect(url_for('minha_conta'))
        if principal:
            cursor.execute("UPDATE enderecos SET principal = FALSE WHERE id_cliente = %s AND id_endereco != %s", (session['usuario_id'], id_endereco))
        cursor.execute("""
            UPDATE enderecos SET tipo = %s, destinatario = %s, cep = %s, estado = %s, cidade = %s, bairro = %s, 
            rua = %s, numero = %s, complemento = %s, principal = %s WHERE id_endereco = %s AND id_cliente = %s
        """, (tipo, destinatario, cep, estado, cidade, bairro, rua, numero, complemento if complemento else None, principal, id_endereco, session['usuario_id']))
        conn.commit()
        flash('✅ Endereço atualizado com sucesso!', 'success')
    except mysql.connector.Error as err:
        flash(f'Erro ao atualizar endereço: {err}', 'error')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return redirect(url_for('minha_conta'))

@app.route('/excluir-endereco/<int:id_endereco>', methods=['POST'])
@login_required
def excluir_endereco(id_endereco):
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('minha_conta'))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM enderecos WHERE id_endereco = %s AND id_cliente = %s", (id_endereco, session['usuario_id']))
        conn.commit()
        if cursor.rowcount > 0:
            flash('🗑️ Endereço excluído com sucesso!', 'success')
        else:
            flash('❌ Endereço não encontrado.', 'error')
    except mysql.connector.Error as err:
        flash(f'Erro ao excluir endereço: {err}', 'error')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return redirect(url_for('minha_conta'))

@app.route('/definir_endereco_principal/<int:id_endereco>', methods=['POST'])
@login_required
def definir_endereco_principal(id_endereco):
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('minha_conta'))
        cursor = conn.cursor()
        cursor.execute("SELECT id_endereco FROM enderecos WHERE id_endereco = %s AND id_cliente = %s", (id_endereco, session['usuario_id']))
        if not cursor.fetchone():
            flash('❌ Endereço não encontrado.', 'error')
            return redirect(url_for('minha_conta'))
        cursor.execute("UPDATE enderecos SET principal = FALSE WHERE id_cliente = %s", (session['usuario_id'],))
        cursor.execute("UPDATE enderecos SET principal = TRUE WHERE id_endereco = %s AND id_cliente = %s", (id_endereco, session['usuario_id']))
        conn.commit()
        flash('✅ Endereço principal definido com sucesso!', 'success')
    except mysql.connector.Error as err:
        flash(f'Erro ao definir endereço principal: {err}', 'error')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return redirect(url_for('minha_conta'))

@app.route('/atualizar_preferencias', methods=['POST'])
@login_required
def atualizar_preferencias():
    email_notificacoes = request.form.get('email_notificacoes') == 'on'
    ofertas_personalizadas = request.form.get('ofertas_personalizadas') == 'on'
    newsletter = request.form.get('newsletter') == 'on'
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('minha_conta'))
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_preferencia FROM preferencias WHERE id_cliente = %s", (session['usuario_id'],))
        existe = cursor.fetchone()
        if existe:
            cursor.execute("UPDATE preferencias SET email_notificacoes = %s, ofertas_personalizadas = %s, newsletter = %s WHERE id_cliente = %s",
                          (email_notificacoes, ofertas_personalizadas, newsletter, session['usuario_id']))
        else:
            cursor.execute("INSERT INTO preferencias (id_cliente, email_notificacoes, ofertas_personalizadas, newsletter) VALUES (%s, %s, %s, %s)",
                          (session['usuario_id'], email_notificacoes, ofertas_personalizadas, newsletter))
        conn.commit()
        flash('⚙️ Preferências atualizadas com sucesso!', 'success')
    except mysql.connector.Error as err:
        flash(f'Erro ao atualizar preferências: {err}', 'error')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return redirect(url_for('minha_conta'))

@app.route('/produtos')
def listar_produtos():
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('produtos.html', produtos=[], categorias=[], marcas=[])
        
        cursor = conn.cursor(dictionary=True)
        categoria = request.args.get('categoria')
        marca = request.args.get('marca')
        busca = request.args.get('busca')
        
        query = "SELECT * FROM produto WHERE ativo = TRUE"
        params = []
        
        if categoria:
            query += " AND categoria = %s"
            params.append(categoria)
        
        if marca:
            query += " AND marca = %s"
            params.append(marca)
        
        if busca:
            query += " AND (nome LIKE %s OR descricao LIKE %s)"
            params.extend([f"%{busca}%", f"%{busca}%"])
        
        query += " ORDER BY data_cadastro DESC"
        
        cursor.execute(query, params)
        produtos = cursor.fetchall()
        
        # PROCESSAR IMAGENS JSON - IMPORTANTE!
        for produto in produtos:
            if produto.get('imagens'):
                try:
                    produto['imagens'] = json.loads(produto['imagens'])
                except:
                    produto['imagens'] = []
        
        cursor.execute("SELECT DISTINCT categoria FROM produto WHERE ativo = TRUE ORDER BY categoria")
        categorias = [row['categoria'] for row in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT marca FROM produto WHERE ativo = TRUE ORDER BY marca")
        marcas = [row['marca'] for row in cursor.fetchall()]
        
        return render_template('produtos.html', produtos=produtos, categorias=categorias, marcas=marcas)
    
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar produtos: {err}', 'error')
        return render_template('produtos.html', produtos=[], categorias=[], marcas=[])
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/produto/<int:id_produto>')
def detalhes_produto(id_produto):
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('listar_produtos'))
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM produto WHERE id_produto = %s AND ativo = TRUE", (id_produto,))
        produto = cursor.fetchone()
        
        if not produto:
            flash('❌ Produto não encontrado.', 'error')
            return redirect(url_for('listar_produtos'))
        
        # DEBUG - ADICIONE ESTAS LINHAS:
        print("=" * 50)
        print(f"DEBUG - ID Produto: {id_produto}")
        print(f"DEBUG - Campo imagens (raw): {produto.get('imagens')}")
        print(f"DEBUG - Tipo: {type(produto.get('imagens'))}")
        
        # PROCESSAR IMAGENS JSON
        if produto.get('imagens'):
            try:
                produto['imagens'] = json.loads(produto['imagens'])
                print(f"DEBUG - Imagens processadas: {produto['imagens']}")
                print(f"DEBUG - Tipo após processar: {type(produto['imagens'])}")
            except Exception as e:
                print(f"DEBUG - Erro ao processar: {e}")
                produto['imagens'] = []
        
        print("=" * 50)
        # FIM DEBUG
        
        cursor.execute("""
            SELECT a.*, c.nome as cliente_nome FROM avaliacoes a
            JOIN clientes c ON a.id_cliente = c.id_cliente
            WHERE a.id_produto = %s AND a.aprovado = TRUE ORDER BY a.data_avaliacao DESC
        """, (id_produto,))
        avaliacoes = cursor.fetchall()
        
        return render_template('produto_detalhes.html', produto=produto, avaliacoes=avaliacoes)
    
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar produto: {err}', 'error')
        return redirect(url_for('listar_produtos'))
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/carrinho')
def carrinho():
    carrinho_items = session.get('carrinho', [])
    total_itens = sum(item['quantidade'] for item in carrinho_items)
    total_preco = sum(item['preco'] * item['quantidade'] for item in carrinho_items)
    return render_template('carrinho.html', produtos_carrinho=carrinho_items, total_itens=total_itens, total_preco=total_preco, total_geral=total_preco)

@app.route('/adicionar-carrinho/<int:id_produto>', methods=['POST'])
def adicionar_carrinho(id_produto):
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('listar_produtos'))
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM produto WHERE id_produto = %s AND ativo = TRUE", (id_produto,))
        produto = cursor.fetchone()
        if not produto:
            flash('❌ Produto não encontrado.', 'error')
            return redirect(url_for('listar_produtos'))
        if 'carrinho' not in session:
            session['carrinho'] = []
        carrinho = session['carrinho']
        produto_no_carrinho = next((item for item in carrinho if item['id_produto'] == id_produto), None)
        quantidade = int(request.form.get('quantidade', 1))
        if produto_no_carrinho:
            produto_no_carrinho['quantidade'] += quantidade
        else:
            carrinho.append({
                'id_produto': produto['id_produto'],
                'nome': produto['nome'],
                'preco': float(produto['preco']),
                'quantidade': quantidade,
                'imagem': produto['imagem'],
                'categoria': produto['categoria']
            })
        session['carrinho'] = carrinho
        session.modified = True
        flash(f'✅ {produto["nome"]} adicionado ao carrinho!', 'success')
        return redirect(url_for('listar_produtos'))
    except mysql.connector.Error as err:
        flash(f'Erro ao adicionar produto ao carrinho: {err}', 'error')
        return redirect(url_for('listar_produtos'))
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/remover-carrinho/<int:id_produto>', methods=['POST'])
def remover_carrinho(id_produto):
    if 'carrinho' in session:
        carrinho = session['carrinho']
        session['carrinho'] = [item for item in carrinho if item['id_produto'] != id_produto]
        session.modified = True
        flash('🗑️ Produto removido do carrinho!', 'success')
    return redirect(url_for('carrinho'))

@app.route('/atualizar-carrinho', methods=['POST'])
def atualizar_carrinho():
    if 'carrinho' in session:
        carrinho = session['carrinho']
        carrinho_dict = {item['id_produto']: item for item in carrinho}
        carrinho_atualizado = []
        for key, value in request.form.items():
            if key.startswith('quantidade_'):
                try:
                    id_produto = int(key.split('_')[1])
                    nova_quantidade = int(value)
                    if id_produto in carrinho_dict:
                        item = carrinho_dict[id_produto]
                        if nova_quantidade > 0:
                            item['quantidade'] = nova_quantidade
                            carrinho_atualizado.append(item)
                except ValueError:
                    continue
        session['carrinho'] = carrinho_atualizado
        session.modified = True
        flash('✅ Carrinho atualizado!', 'success')
    return redirect(url_for('carrinho'))

@app.route('/limpar-carrinho', methods=['POST'])
def limpar_carrinho():
    session.pop('carrinho', None)
    flash('🗑️ Carrinho limpo!', 'success')
    return redirect(url_for('carrinho'))

def gerar_qrcode_pix(valor_total):
    """Gera QR Code e código Copia e Cola PIX com base no valor total"""
    chave_pix = "14057629939" 
    nome_recebedor = "CAETANO GBUR PETRY"  
    cidade_recebedor = "JOINVILLE"

    def emv(id, valor):
        tamanho = str(len(valor)).zfill(2)
        return f"{id}{tamanho}{valor}"

    merchant_account = emv("00", "br.gov.bcb.pix") + emv("01", chave_pix)
    merchant_info = emv("26", merchant_account)
    transaction_amount = emv("54", f"{valor_total:.2f}")
    txid = emv("05", f"GHCP{int(valor_total * 100)}")

    payload = (
        emv("00", "01")
        + emv("01", "12")
        + merchant_info
        + emv("52", "0000")
        + emv("53", "986")
        + transaction_amount
        + emv("58", "BR")
        + emv("59", nome_recebedor)
        + emv("60", cidade_recebedor)
        + emv("62", txid)
    )

    def crc16(payload):
        polinomio = 0x1021
        resultado = 0xFFFF
        payload += "6304"
        for byte in bytearray(payload, "utf-8"):
            resultado ^= byte << 8
            for _ in range(8):
                if resultado & 0x8000:
                    resultado = (resultado << 1) ^ polinomio
                else:
                    resultado <<= 1
                resultado &= 0xFFFF
        return f"{payload}{resultado:04X}"

    copia_cola = crc16(payload)

    img = qrcode.make(copia_cola)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return qr_base64, copia_cola

@app.route('/gerar-pix/<float:valor>')
def gerar_pix(valor):
    qr_base64, copia_cola = gerar_qrcode_pix(valor)
    return render_template('gerar_pix.html', valor=valor, qr_base64=qr_base64, copia_cola=copia_cola)

@app.route('/finalizar-carrinho', methods=['GET', 'POST'])
def finalizar_carrinho():
    if 'usuario_id' not in session:
        flash('⚠️ Faça login para finalizar sua compra.', 'warning')
        return redirect(url_for('login', next=url_for('finalizar_carrinho')))

    produtos_carrinho = session.get('carrinho', [])
    total_geral = sum(item['preco'] * item['quantidade'] for item in produtos_carrinho)

    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        endereco = request.form.get('endereco')
        pagamento = request.form.get('pagamento')

        if not produtos_carrinho:
            flash('⚠️ Seu carrinho está vazio.', 'warning')
            return redirect(url_for('carrinho'))

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            # Pra ver o estoque
            for item in produtos_carrinho:
                cursor.execute("SELECT nome, estoque FROM produto WHERE id_produto = %s", (item['id_produto'],))
                produto_db = cursor.fetchone()
                if not produto_db:
                    flash(f"❌ Produto '{item['nome']}' não encontrado.", 'error')
                    return redirect(url_for('carrinho'))
                if produto_db['estoque'] < item['quantidade']:
                    flash(f"⚠️ Estoque insuficiente de '{produto_db['nome']}'.", 'warning')
                    return redirect(url_for('carrinho'))

            # Pra criar o pedido
            cursor.execute("""
                INSERT INTO pedidos (id_cliente, total, forma_pagamento, status, data_pedido)
                VALUES (%s, %s, %s, %s, NOW())
            """, (session['usuario_id'], total_geral, pagamento, 'pendente'))
            pedido_id = cursor.lastrowid

            #  Pra adicionar itens e atualiza estoque
            for item in produtos_carrinho:
                cursor.execute("""
                    INSERT INTO itens_pedido (id_pedido, id_produto, quantidade, preco_unitario)
                    VALUES (%s, %s, %s, %s)
                """, (pedido_id, item['id_produto'], item['quantidade'], item['preco']))
                cursor.execute("""
                    UPDATE produto SET estoque = estoque - %s WHERE id_produto = %s
                """, (item['quantidade'], item['id_produto']))

            # 💾 4️⃣ Registra pagamento (opcional, mas recomendado)
            cursor.execute("""
                INSERT INTO pagamentos (nome, email, endereco, metodo, valor)
                VALUES (%s, %s, %s, %s, %s)
            """, (nome, email, endereco, pagamento, total_geral))

            conn.commit()

            # 💸 5️⃣ Gera PIX se for o método escolhido
            if pagamento == 'pix':
                qr_base64, copia_cola = gerar_qrcode_pix(total_geral)
                session.pop('carrinho', None)
                flash('🎉 Compra finalizada com sucesso! Escaneie o QR Code para pagar via PIX.', 'success')
                return render_template(
                    'compra-sucedida.html',
                    valor=total_geral,
                    qr_base64=qr_base64,
                    copia_cola=copia_cola,
                    pedido_id=pedido_id
                )
            else:
                flash('💳 Pagamento por cartão/boleto ainda não implementado.', 'info')
                return redirect(url_for('inicio'))

        except mysql.connector.Error as err:
            conn.rollback()
            flash(f'❌ Erro ao finalizar compra: {err}', 'error')
            return redirect(url_for('carrinho'))
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    return render_template('finalizar-carrinho.html',
                           produtos_carrinho=produtos_carrinho,
                           total_geral=total_geral)


@app.route('/compra-sucedida')
def compra_sucedida():
    return render_template('compra-sucedida.html')

@app.route('/pix')
def pix():
    return render_template('pix.html')

@app.route('/boleto')
def boleto():
    return render_template('boleto.html')

@app.route('/cartoes')
def cartoes():
    return render_template('cartoes.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        if not email or not senha:
            flash('❌ Preencha todos os campos.', 'error')
            return render_template('admin/login.html')
        try:
            conn = get_db_connection()
            if not conn:
                flash('Erro ao conectar ao banco de dados.', 'error')
                return render_template('admin/login.html')
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM funcionarios WHERE email = %s AND ativo = TRUE", (email,))
            admin = cursor.fetchone()
            if admin and check_password_hash(admin['senha'], senha):
                session['admin_id'] = admin['id_funcionario']
                session['admin_nome'] = admin['nome']
                session['admin_cargo'] = admin['cargo']
                cursor.execute("UPDATE funcionarios SET ultimo_login = NOW() WHERE id_funcionario = %s", (admin['id_funcionario'],))
                conn.commit()
                flash(f'🎉 Bem-vindo, {admin["nome"]}!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('❌ Credenciais inválidas.', 'error')
        except mysql.connector.Error as err:
            flash(f'Erro ao fazer login: {err}', 'error')
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_nome', None)
    session.pop('admin_cargo', None)
    flash('👋 Logout realizado com sucesso!', 'info')
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    total_clientes = 0
    total_produtos = 0
    pedidos_hoje = 0
    receita_hoje = 0
    diagnosticos_pendentes = 0
    estoque_baixo = []
    pedidos_recentes = []
    diagnosticos_recentes = []

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