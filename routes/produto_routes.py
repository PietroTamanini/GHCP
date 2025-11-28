from flask import render_template, request, flash, redirect, url_for, session
from models.database import get_db_connection
from utils.decorators import login_required
import json
import mysql.connector

def configure_produto_routes(app):
    
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
            
            # PROCESSAR IMAGENS JSON
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
            
            # PROCESSAR IMAGENS JSON
            if produto.get('imagens'):
                try:
                    produto['imagens'] = json.loads(produto['imagens'])
                except Exception as e:
                    print(f"DEBUG - Erro ao processar: {e}")
                    produto['imagens'] = []
            
            # BUSCAR AVALIAÇÕES E ESTATÍSTICAS
            cursor.execute("""
                SELECT a.*, c.nome as cliente_nome FROM avaliacoes a
                JOIN clientes c ON a.id_cliente = c.id_cliente
                WHERE a.id_produto = %s AND a.aprovado = TRUE ORDER BY a.data_avaliacao DESC
            """, (id_produto,))
            avaliacoes = cursor.fetchall()
            
            # BUSCAR ESTATÍSTICAS DAS AVALIAÇÕES
            cursor.execute("""
                SELECT 
                    AVG(nota) as media,
                    COUNT(*) as total_avaliacoes,
                    SUM(CASE WHEN nota = 5 THEN 1 ELSE 0 END) as cinco_estrelas,
                    SUM(CASE WHEN nota = 4 THEN 1 ELSE 0 END) as quatro_estrelas,
                    SUM(CASE WHEN nota = 3 THEN 1 ELSE 0 END) as tres_estrelas,
                    SUM(CASE WHEN nota = 2 THEN 1 ELSE 0 END) as duas_estrelas,
                    SUM(CASE WHEN nota = 1 THEN 1 ELSE 0 END) as uma_estrela
                FROM avaliacoes 
                WHERE id_produto = %s AND aprovado = TRUE
            """, (id_produto,))
            
            media_avaliacoes = cursor.fetchone()
            
            return render_template('produto_detalhes.html', 
                                produto=produto, 
                                avaliacoes=avaliacoes,
                                media_avaliacoes=media_avaliacoes)  # ← NOVO PARÂMETRO
        
        except mysql.connector.Error as err:
            flash(f'Erro ao carregar produto: {err}', 'error')
            return redirect(url_for('listar_produtos'))
        
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

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

    # Outras rotas de produtos...
    @app.route('/categorias')
    def categorias():
        try:
            conn = get_db_connection()
            if not conn:
                flash('Erro ao conectar ao banco de dados.', 'error')
                return render_template('categorias.html', categorias=[])
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT categoria, COUNT(*) as total_produtos FROM produto 
                WHERE ativo = TRUE GROUP BY categoria ORDER BY categoria
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

    @app.route('/marcas')
    def marcas():
        try:
            conn = get_db_connection()
            if not conn:
                flash('Erro ao conectar ao banco de dados.', 'error')
                return render_template('marcas.html', marcas=[])
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT marca, COUNT(*) as total_produtos, MIN(preco) as preco_minimo, MAX(preco) as preco_maximo
                FROM produto WHERE ativo = TRUE GROUP BY marca ORDER BY marca
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

# ... (seu código existente)

# FUNÇÕES PARA AVALIAÇÕES - ADICIONE ISSO NO FINAL DO ARQUIVO
def buscar_avaliacoes_produto(id_produto):
    """Busca todas as avaliações de um produto"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT a.*, c.nome as cliente_nome 
        FROM avaliacoes a
        JOIN clientes c ON a.id_cliente = c.id_cliente
        WHERE a.id_produto = %s AND a.aprovado = TRUE 
        ORDER BY a.data_avaliacao DESC
    """, (id_produto,))
    
    avaliacoes = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return avaliacoes

def calcular_media_avaliacoes(id_produto):
    """Calcula a média das avaliações de um produto"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT 
            AVG(nota) as media,
            COUNT(*) as total_avaliacoes,
            SUM(CASE WHEN nota = 5 THEN 1 ELSE 0 END) as cinco_estrelas,
            SUM(CASE WHEN nota = 4 THEN 1 ELSE 0 END) as quatro_estrelas,
            SUM(CASE WHEN nota = 3 THEN 1 ELSE 0 END) as tres_estrelas,
            SUM(CASE WHEN nota = 2 THEN 1 ELSE 0 END) as duas_estrelas,
            SUM(CASE WHEN nota = 1 THEN 1 ELSE 0 END) as uma_estrela
        FROM avaliacoes 
        WHERE id_produto = %s AND aprovado = TRUE
    """, (id_produto,))
    
    resultado = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return resultado