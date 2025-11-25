from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from models.database import get_db_connection
from utils.decorators import login_required
import json

avaliacao_bp = Blueprint('avaliacao', __name__)

@avaliacao_bp.route('/produto/<int:id_produto>/avaliar', methods=['GET', 'POST'])
@login_required
def criar_avaliacao(id_produto):
    # Buscar produto
    produto = buscar_produto_por_id(id_produto)
    if not produto:
        flash('Produto não encontrado', 'error')
        return redirect(url_for('listar_produtos'))
    
    # Verificar se usuário já avaliou este produto
    if request.method == 'GET':
        avaliacao_existente = buscar_avaliacao_usuario(session['usuario_id'], id_produto)
        if avaliacao_existente:
            flash('Você já avaliou este produto', 'warning')
            return redirect(url_for('detalhes_produto', id_produto=id_produto))
    
    if request.method == 'POST':
        nota = request.form.get('nota')
        titulo = request.form.get('titulo', '').strip()
        comentario = request.form.get('comentario', '').strip()
        
        # Validações
        if not nota or not comentario:
            flash('Preencha todos os campos obrigatórios', 'error')
            return render_template('avaliacoes.html', produto=produto)
        
        if len(comentario) < 10:
            flash('O comentário deve ter pelo menos 10 caracteres', 'error')
            return render_template('avaliacoes.html', produto=produto)
        
        # Salvar avaliação
        if salvar_avaliacao(session['usuario_id'], id_produto, nota, titulo, comentario):
            flash('Avaliação enviada com sucesso! Obrigado pelo feedback.', 'success')
            return redirect(url_for('detalhes_produto', id_produto=id_produto))
        else:
            flash('Erro ao enviar avaliação. Tente novamente.', 'error')
    
    return render_template('avaliacoes.html', produto=produto)

# Funções auxiliares para avaliações
def buscar_produto_por_id(id_produto):
    """Busca produto pelo ID"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT id_produto, nome, marca, preco, descricao, estoque, 
               imagem, categoria, imagens 
        FROM produto 
        WHERE id_produto = %s AND ativo = TRUE
    """, (id_produto,))
    
    produto = cursor.fetchone()
    
    # PROCESSAR IMAGENS (igual ao seu código)
    if produto and produto.get('imagens'):
        try:
            produto['imagens'] = json.loads(produto['imagens'])
        except Exception as e:
            print(f"DEBUG - Erro ao processar: {e}")
            produto['imagens'] = []
    
    cursor.close()
    conn.close()
    
    return produto

def buscar_avaliacao_usuario(id_cliente, id_produto):
    """Verifica se usuário já avaliou o produto"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT id_avaliacao 
        FROM avaliacoes 
        WHERE id_cliente = %s AND id_produto = %s
    """, (id_cliente, id_produto))
    
    avaliacao = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return avaliacao

def salvar_avaliacao(id_cliente, id_produto, nota, titulo, comentario):
    """Salva uma nova avaliação no banco"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO avaliacoes 
            (id_cliente, id_produto, nota, titulo, comentario, aprovado) 
            VALUES (%s, %s, %s, %s, %s, TRUE)
        """, (id_cliente, id_produto, nota, titulo, comentario))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao salvar avaliação: {e}")
        return False