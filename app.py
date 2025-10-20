from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'GHCP-2o25'

# ============================================
# CONFIGURAÇÃO DO BANCO DE DADOS
# ============================================

DB_CONFIG = {
    'host': 'localhost',
    'port': '3406',
    'user': 'root',
    'password': '',  # ⚠️ Coloque sua senha do MySQL aqui
    'database': 'loja_informatica'
}

def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados"""
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as err:
        print(f"Erro ao conectar ao banco de dados: {err}")
        return None

# ============================================
# DECORATORS E FUNÇÕES AUXILIARES
# ============================================

def login_required(f):
    """Decorator para proteger rotas que precisam de autenticação"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('⚠️ Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def validar_cpf(cpf):
    """Valida formato do CPF"""
    cpf = re.sub(r'\D', '', cpf)
    if len(cpf) != 11:
        return False
    
    # Verificar se todos os dígitos são iguais
    if cpf == cpf[0] * 11:
        return False
    
    # Validação do primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito1 = (soma * 10 % 11) % 10
    
    if digito1 != int(cpf[9]):
        return False
    
    # Validação do segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito2 = (soma * 10 % 11) % 10
    
    return digito2 == int(cpf[10])

def validar_email(email):
    """Valida formato de email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def formatar_cpf(cpf):
    """Formata CPF para o padrão XXX.XXX.XXX-XX"""
    cpf = re.sub(r'\D', '', cpf)
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

def formatar_telefone(telefone):
    """Formata telefone para o padrão (XX) XXXXX-XXXX"""
    telefone = re.sub(r'\D', '', telefone)
    if len(telefone) == 11:
        return f"({telefone[:2]}) {telefone[2:7]}-{telefone[7:]}"
    elif len(telefone) == 10:
        return f"({telefone[:2]}) {telefone[2:6]}-{telefone[6:]}"
    return telefone

# ============================================
# ROTAS DE AUTENTICAÇÃO
# ============================================

@app.route('/')
def inicio():
    """Página inicial"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('index.html', produtos=[])
        
        cursor = conn.cursor(dictionary=True)
        
        # Buscar produtos em destaque
        cursor.execute("""
            SELECT * FROM produto 
            WHERE ativo = TRUE 
            ORDER BY data_cadastro DESC 
            LIMIT 8
        """)
        
        produtos = cursor.fetchall()
        
        return render_template('index.html', produtos=produtos)
    
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar produtos: {err}', 'error')
        return render_template('index.html', produtos=[])
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página e processamento de login"""
    # Se já estiver logado, redireciona
    if 'usuario_id' in session:
        return redirect(url_for('inicio'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        
        # Validações básicas
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
            
            # Buscar usuário pelo email
            cursor.execute("""
                SELECT id_cliente, nome, email, senha, ativo 
                FROM clientes 
                WHERE email = %s
            """, (email,))
            
            usuario = cursor.fetchone()
            
            if usuario and check_password_hash(usuario['senha'], senha):
                if not usuario['ativo']:
                    flash('⚠️ Sua conta está desativada. Entre em contato com o suporte.', 'warning')
                    return render_template('login.html')
                
                # Login bem-sucedido
                session['usuario_id'] = usuario['id_cliente']
                session['usuario_nome'] = usuario['nome']
                session['usuario_email'] = usuario['email']
                
                flash(f'🎉 Bem-vindo de volta, {usuario["nome"]}!', 'success')
                
                # Redirecionar para página anterior ou início
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


@app.route('/cadastro', methods=['POST'])
def cadastro():
    """Processamento de cadastro"""
    # Coletar dados do formulário
    nome = request.form.get('nome', '').strip()
    email = request.form.get('email', '').strip().lower()
    cpf = request.form.get('cpf', '').strip()
    telefone = request.form.get('telefone', '').strip()
    data_nascimento = request.form.get('data_nascimento')
    genero = request.form.get('genero')
    senha = request.form.get('senha', '')
    confirmar_senha = request.form.get('confirmar_senha', '')
    aceitar_termos = request.form.get('aceitar_termos')
    
    # Validações
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
    
    # Formatar CPF
    cpf_formatado = formatar_cpf(cpf)
    
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('login'))
        
        cursor = conn.cursor()
        
        # Verificar se email já existe
        cursor.execute("SELECT id_cliente FROM clientes WHERE email = %s", (email,))
        if cursor.fetchone():
            flash('❌ Este e-mail já está cadastrado.', 'error')
            return redirect(url_for('login'))
        
        # Verificar se CPF já existe
        cursor.execute("SELECT id_cliente FROM clientes WHERE cpf = %s", (cpf_formatado,))
        if cursor.fetchone():
            flash('❌ Este CPF já está cadastrado.', 'error')
            return redirect(url_for('login'))
        
        # Hash da senha
        senha_hash = generate_password_hash(senha)
        
        # Inserir novo cliente
        cursor.execute("""
            INSERT INTO clientes (nome, email, senha, cpf, telefone, data_nascimento, genero)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (nome, email, senha_hash, cpf_formatado, telefone, 
              data_nascimento if data_nascimento else None, 
              genero if genero else None))
        
        conn.commit()
        cliente_id = cursor.lastrowid
        
        # Criar preferências padrão
        cursor.execute("""
            INSERT INTO preferencias (id_cliente, email_notificacoes, ofertas_personalizadas)
            VALUES (%s, TRUE, TRUE)
        """, (cliente_id,))
        
        conn.commit()
        
        # Login automático após cadastro
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


@app.route('/logout')
@login_required
def logout():
    """Fazer logout do sistema"""
    nome = session.get('usuario_nome', 'Usuário')
    session.clear()
    flash(f'👋 Até logo, {nome}! Volte sempre.', 'info')
    return redirect(url_for('inicio'))


@app.route('/recuperar-senha', methods=['GET', 'POST'])
def recuperar_senha():
    """Página de recuperação de senha"""
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
                
                # Aqui você implementaria o envio de email com token
                # Por enquanto, vamos apenas registrar a solicitação no banco
                
                # IMPORTANTE: Em produção, você deve:
                # 1. Gerar um token único
                # 2. Salvar o token no banco com prazo de validade
                # 3. Enviar email com link contendo o token
                # 4. Criar rota para resetar senha com o token
                
                flash('✅ Se o e-mail estiver cadastrado, você receberá as instruções de recuperação em breve.', 'success')
                
                # Log da tentativa (opcional)
                print(f"[RECUPERAÇÃO] Solicitação para: {email} - {usuario['nome']}")
            else:
                # Por segurança, não informar se o email existe ou não
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
    """Página da conta do usuário"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('inicio'))
        
        cursor = conn.cursor(dictionary=True)
        
        # Buscar dados do cliente
        cursor.execute("""
            SELECT c.*, 
                   COUNT(DISTINCT p.id_pedido) as total_pedidos,
                   COALESCE(SUM(CASE WHEN p.status != 'cancelado' THEN p.total ELSE 0 END), 0) as total_gasto
            FROM clientes c
            LEFT JOIN pedidos p ON c.id_cliente = p.id_cliente
            WHERE c.id_cliente = %s
            GROUP BY c.id_cliente
        """, (session['usuario_id'],))
        
        cliente = cursor.fetchone()
        
        if not cliente:
            flash('Erro ao carregar dados do usuário.', 'error')
            return redirect(url_for('inicio'))
        
        # Buscar pedidos recentes
        cursor.execute("""
            SELECT * FROM pedidos 
            WHERE id_cliente = %s 
            ORDER BY data_pedido DESC 
            LIMIT 5
        """, (session['usuario_id'],))
        
        pedidos = cursor.fetchall()
        
        # Buscar endereços
        cursor.execute("""
            SELECT * FROM enderecos 
            WHERE id_cliente = %s 
            ORDER BY principal DESC, data_criacao DESC
        """, (session['usuario_id'],))
        
        enderecos = cursor.fetchall()
        
        # Buscar preferências
        cursor.execute("""
            SELECT * FROM preferencias 
            WHERE id_cliente = %s
        """, (session['usuario_id'],))
        
        preferencias = cursor.fetchone()
        
        return render_template('minha_conta.html', 
                             cliente=cliente, 
                             pedidos=pedidos,
                             enderecos=enderecos,
                             preferencias=preferencias)
    
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar dados: {err}', 'error')
        return redirect(url_for('inicio'))
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


@app.route('/atualizar-perfil', methods=['POST'])
@login_required
def atualizar_perfil():
    """Atualizar dados do perfil"""
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
        
        cursor.execute("""
            UPDATE clientes 
            SET nome = %s, telefone = %s, data_nascimento = %s, genero = %s
            WHERE id_cliente = %s
        """, (nome, telefone, data_nascimento if data_nascimento else None, 
              genero if genero else None, session['usuario_id']))
        
        conn.commit()
        
        # Atualizar sessão
        session['usuario_nome'] = nome
        
        flash('✅ Perfil atualizado com sucesso!', 'success')
    
    except mysql.connector.Error as err:
        flash(f'Erro ao atualizar perfil: {err}', 'error')
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    
    return redirect(url_for('minha_conta'))


@app.route('/alterar-senha', methods=['POST'])
@login_required
def alterar_senha():
    """Alterar senha do usuário"""
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
        
        # Verificar senha atual
        cursor.execute("SELECT senha FROM clientes WHERE id_cliente = %s", (session['usuario_id'],))
        resultado = cursor.fetchone()
        
        if not resultado or not check_password_hash(resultado['senha'], senha_atual):
            flash('❌ Senha atual incorreta.', 'error')
            return redirect(url_for('minha_conta'))
        
        # Atualizar senha (o trigger vai registrar no histórico automaticamente)
        nova_senha_hash = generate_password_hash(nova_senha)
        cursor.execute("""
            UPDATE clientes 
            SET senha = %s 
            WHERE id_cliente = %s
        """, (nova_senha_hash, session['usuario_id']))
        
        conn.commit()
        
        flash('🔒 Senha alterada com sucesso!', 'success')
    
    except mysql.connector.Error as err:
        flash(f'Erro ao alterar senha: {err}', 'error')
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    
    return redirect(url_for('minha_conta'))


@app.route('/adicionar-endereco', methods=['POST'])
@login_required
def adicionar_endereco():
    """Adicionar novo endereço"""
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
        
        cursor.execute("""
            INSERT INTO enderecos 
            (id_cliente, tipo, destinatario, cep, estado, cidade, bairro, rua, numero, complemento, principal)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (session['usuario_id'], tipo, destinatario, cep, estado, cidade, 
              bairro, rua, numero, complemento if complemento else None, principal))
        
        conn.commit()
        
        flash('📍 Endereço adicionado com sucesso!', 'success')
    
    except mysql.connector.Error as err:
        flash(f'Erro ao adicionar endereço: {err}', 'error')
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    
    return redirect(url_for('minha_conta'))


@app.route('/excluir-endereco/<int:id_endereco>', methods=['POST'])
@login_required
def excluir_endereco(id_endereco):
    """Excluir endereço"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('minha_conta'))
        
        cursor = conn.cursor()
        
        # Verificar se o endereço pertence ao usuário
        cursor.execute("""
            DELETE FROM enderecos 
            WHERE id_endereco = %s AND id_cliente = %s
        """, (id_endereco, session['usuario_id']))
        
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


# ============================================
# ROTAS DE PRODUTOS E CARRINHO
# ============================================

@app.route('/produtos')
def listar_produtos():
    """Listar produtos"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('produtos.html', produtos=[])
        
        cursor = conn.cursor(dictionary=True)
        
        # Filtros
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
        
        # Buscar categorias e marcas para filtros
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
    """Detalhes de um produto específico"""
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
        
        # Buscar avaliações do produto
        cursor.execute("""
            SELECT a.*, c.nome as cliente_nome 
            FROM avaliacoes a
            JOIN clientes c ON a.id_cliente = c.id_cliente
            WHERE a.id_produto = %s AND a.aprovado = TRUE
            ORDER BY a.data_avaliacao DESC
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
    """Página do carrinho"""
    # Carrinho será gerenciado via sessão
    carrinho_items = session.get('carrinho', [])
    
    # Calcular totais
    total_itens = sum(item['quantidade'] for item in carrinho_items)
    total_preco = sum(item['preco'] * item['quantidade'] for item in carrinho_items)
    
    return render_template('carrinho.html', 
                         produtos_carrinho=carrinho_items, 
                         total_itens=total_itens, 
                         total_preco=total_preco,
                         total_geral=total_preco)


@app.route('/adicionar-carrinho/<int:id_produto>', methods=['POST'])
def adicionar_carrinho(id_produto):
    """Adicionar produto ao carrinho"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('listar_produtos'))
        
        cursor = conn.cursor(dictionary=True)
        
        # Buscar informações do produto
        cursor.execute("SELECT * FROM produto WHERE id_produto = %s AND ativo = TRUE", (id_produto,))
        produto = cursor.fetchone()
        
        if not produto:
            flash('❌ Produto não encontrado.', 'error')
            return redirect(url_for('listar_produtos'))
        
        # Inicializar carrinho na sessão se não existir
        if 'carrinho' not in session:
            session['carrinho'] = []
        
        # Verificar se o produto já está no carrinho
        carrinho = session['carrinho']
        produto_no_carrinho = next((item for item in carrinho if item['id_produto'] == id_produto), None)
        
        quantidade = int(request.form.get('quantidade', 1))
        
        if produto_no_carrinho:
            # Atualizar quantidade se já estiver no carrinho
            produto_no_carrinho['quantidade'] += quantidade
        else:
            # Adicionar novo item ao carrinho
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
    """Remover produto do carrinho"""
    if 'carrinho' in session:
        carrinho = session['carrinho']
        # Filtrar itens, removendo o produto especificado
        session['carrinho'] = [item for item in carrinho if item['id_produto'] != id_produto]
        session.modified = True
        flash('🗑️ Produto removido do carrinho!', 'success')
    
    return redirect(url_for('carrinho'))


# NOVO: A ROTA NÃO EXIGE MAIS O ID NA URL
@app.route('/atualizar-carrinho', methods=['POST'])
def atualizar_carrinho():
    """Atualizar quantidade de produtos no carrinho lendo todos os campos do formulário."""
    if 'carrinho' in session:
        carrinho = session['carrinho']
        
        # Cria um dicionário de IDs para acesso rápido (simplifica a atualização)
        carrinho_dict = {item['id_produto']: item for item in carrinho}
        
        # Lista temporária para reconstruir o carrinho após as mudanças
        carrinho_atualizado = []
        
        # Itera sobre os dados enviados pelo formulário
        for key, value in request.form.items():
            if key.startswith('quantidade_'):
                try:
                    # Extrai o ID do produto do nome do campo (ex: 'quantidade_123' -> 123)
                    id_produto = int(key.split('_')[1])
                    nova_quantidade = int(value)
                    
                    if id_produto in carrinho_dict:
                        item = carrinho_dict[id_produto]
                        
                        if nova_quantidade > 0:
                            # Se a quantidade for válida, atualiza
                            item['quantidade'] = nova_quantidade
                            # Adiciona à lista atualizada (se não for removido)
                            carrinho_atualizado.append(item) 
                        # Se nova_quantidade <= 0, o item é removido implicitamente por não ser adicionado à lista atualizada

                except ValueError:
                    # Ignora campos que não são números
                    continue
            
            # Garante que itens não presentes no form (ex: se você tivesse outro campo não quantidade) 
            # não seriam perdidos, mas com a lógica acima ele deve funcionar.
            # No seu caso, o carrinho atualizado é a lista de itens válidos do carrinho_dict.

        # O novo carrinho são os itens que sobreviveram ao loop.
        session['carrinho'] = carrinho_atualizado
        session.modified = True
        
        flash('✅ Carrinho atualizado!', 'success')
    
    return redirect(url_for('carrinho'))


@app.route('/limpar-carrinho', methods=['POST'])
def limpar_carrinho():
    """Limpar todo o carrinho"""
    session.pop('carrinho', None)
    flash('🗑️ Carrinho limpo!', 'success')
    return redirect(url_for('carrinho'))

@app.route('/pix')
def pix():
    return render_template('pix.html')

@app.route('/boleto')
def boleto():
    return render_template('boleto.html')

@app.route('/cartoes_credito')
def cartoes_credito():
    return render_template('cartoes_credito.html')




# ============================================
# ROTAS INSTITUCIONAIS E INFORMATIVAS
# ============================================

@app.route('/sobre')
def sobre():
    """Página Sobre a GHCP"""
    return render_template('sobre.html')

@app.route('/contato')
def contato():
    """Página de Contato"""
    return render_template('contato.html')

@app.route('/trabalhe-conosco')
def trabalhe_conosco():
    """Página Trabalhe Conosco"""
    return render_template('trabalhe_conosco.html')

@app.route('/faq')
def faq():
    """Página de Perguntas Frequentes"""
    return render_template('faq.html')

@app.route('/rastreio')
def rastreio():
    """Página de Rastreamento de Pedido"""
    return render_template('rastreio.html')

@app.route('/trocas')
def trocas():
    """Página de Trocas e Devoluções"""
    return render_template('trocas.html')

@app.route('/termos')
def termos():
    """Página de Termos de Uso"""
    return render_template('termos.html')

@app.route('/privacidade')
def privacidade():
    """Página de Política de Privacidade"""
    return render_template('privacidade.html')

@app.route('/cookies')
def cookies():
    """Página de Política de Cookies"""
    return render_template('cookies.html')

@app.route('/prazos')
def prazos():
    """Página de Prazos de Entrega"""
    return render_template('prazos.html')

@app.route('/formas-pagamento')
def formas_pagamento():
    """Página de Formas de Pagamento"""
    return render_template('formas_pagamento.html')

@app.route('/garantia')
def garantia():
    """Página de Garantia"""
    return render_template('garantia.html')

@app.route('/marcas')
def marcas():
    """Página de Marcas Parceiras"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('marcas.html', marcas=[])
        
        cursor = conn.cursor(dictionary=True)
        
        # Buscar todas as marcas distintas
        cursor.execute("""
            SELECT marca, COUNT(*) as total_produtos, 
                   MIN(preco) as preco_minimo, 
                   MAX(preco) as preco_maximo
            FROM produto 
            WHERE ativo = TRUE 
            GROUP BY marca 
            ORDER BY marca
        """)
        
        marcas_lista = cursor.fetchall()
        
        return render_template('marcas.html', marcas=marcas_lista)
    
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar marcas: {err}', 'error')
        return render_template('marcas.html', marcas=[])
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/categorias')
def categorias():
    """Página de Categorias"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('categorias.html', categorias=[])
        
        cursor = conn.cursor(dictionary=True)
        
        # Buscar todas as categorias distintas
        cursor.execute("""
            SELECT categoria, COUNT(*) as total_produtos
            FROM produto 
            WHERE ativo = TRUE 
            GROUP BY categoria 
            ORDER BY categoria
        """)
        
        categorias_lista = cursor.fetchall()
        
        return render_template('categorias.html', categorias=categorias_lista)
    
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar categorias: {err}', 'error')
        return render_template('categorias.html', categorias=[])
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/ofertas')
def ofertas():
    """Página de Ofertas Especiais"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('ofertas.html', produtos=[])
        
        cursor = conn.cursor(dictionary=True)
        
        # Buscar produtos em oferta (você pode adicionar um campo 'em_oferta' na tabela)
        cursor.execute("""
            SELECT * FROM produto 
            WHERE ativo = TRUE 
            ORDER BY preco ASC
            LIMIT 20
        """)
        
        produtos = cursor.fetchall()
        
        return render_template('ofertas.html', produtos=produtos)
    
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar ofertas: {err}', 'error')
        return render_template('ofertas.html', produtos=[])
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/lancamentos')
def lancamentos():
    """Página de Lançamentos"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('lancamentos.html', produtos=[])
        
        cursor = conn.cursor(dictionary=True)
        
        # Buscar produtos mais recentes
        cursor.execute("""
            SELECT * FROM produto 
            WHERE ativo = TRUE 
            ORDER BY data_cadastro DESC
            LIMIT 20
        """)
        
        produtos = cursor.fetchall()
        
        return render_template('lancamentos.html', produtos=produtos)
    
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar lançamentos: {err}', 'error')
        return render_template('lancamentos.html', produtos=[])
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/condicoes')
def condicoes():
    """Página de Condições Comerciais"""
    return render_template('condicoes.html')

@app.route('/monte-seu-pc')
def monte_seu_pc():
    """Página Monte Seu PC"""
    return render_template('monte_seu_pc.html')

@app.route('/assistencia')
def assistencia():
    """Página de Assistência Técnica"""
    return render_template('assistencia.html')

@app.route('/blog')
def blog():
    """Página do Blog"""
    return render_template('blog.html')

@app.route('/newsletter')
def newsletter():
    """Página de Newsletter"""
    return render_template('newsletter.html')


# ============================================
# TRATAMENTO DE ERROS
# ============================================

@app.errorhandler(404)
def page_not_found(e):
    """Página não encontrada"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    """Erro interno do servidor"""
    return render_template('500.html'), 500


# ============================================
# EXECUTAR APLICAÇÃO
# ============================================

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Loja GHCP - Sistema de E-commerce")
    print("=" * 60)
    print("✅ Servidor Flask iniciado com sucesso!")
    print(f"🌐 Acesse: http://localhost:5000")
    print(f"🔐 Login: http://localhost:5000/login")
    print(f"👤 Minha Conta: http://localhost:5000/minha-conta")
    print(f"🛒 Carrinho: http://localhost:5000/carrinho")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)