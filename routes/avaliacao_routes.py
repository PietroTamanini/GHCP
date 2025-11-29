from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from models.database import get_db_connection
from utils.decorators import login_required
import json

avaliacao_bp = Blueprint('avaliacao', __name__)

@avaliacao_bp.route('/produto/<int:id_produto>/avaliar', methods=['GET', 'POST'])
@login_required
def criar_avaliacao(id_produto):
    # ✅ VERIFICAÇÃO CORRIGIDA - Usa a mesma função
    if not verificar_pagamento_banco(session['usuario_id']):
        flash('❌ Você precisa confirmar o pagamento antes de avaliar os produtos', 'error')
        return redirect(url_for('finalizar_carrinho'))
    
    # 🔹 SEU CÓDIGO ATUAL CONTINUA A PARTIR DAQUI
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

@avaliacao_bp.route('/minhas-avaliacoes-pendentes')
@login_required
def minhas_avaliacoes_pendentes():
    """Página que mostra produtos comprados para avaliar - VERSÃO CORRIGIDA"""
    
    # ✅ VERIFICAÇÃO CORRIGIDA - Usa a mesma função
    if not verificar_pagamento_banco(session['usuario_id']):
        flash('❌ Confirme o pagamento antes de avaliar os produtos', 'error')
        return redirect(url_for('finalizar_carrinho'))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # ✅ BUSCA PRODUTOS COM STATUS 'concluido'
        cursor.execute("""
            SELECT DISTINCT p.id_produto, p.nome, p.marca, p.categoria, p.imagens
            FROM itens_pedido ip
            JOIN pedidos pd ON ip.id_pedido = pd.id_pedido
            JOIN produto p ON ip.id_produto = p.id_produto
            WHERE pd.id_cliente = %s 
            AND pd.status = 'concluido'  -- ✅ CORRIGIDO: 'concluido' em vez de 'aprovado'
            AND p.id_produto NOT IN (
                SELECT id_produto 
                FROM avaliacoes 
                WHERE id_cliente = %s
            )
        """, (session['usuario_id'], session['usuario_id']))
        
        produtos = cursor.fetchall()
        
        # Processar imagens
        for produto in produtos:
            if produto.get('imagens'):
                try:
                    produto['imagens'] = json.loads(produto['imagens'])
                except:
                    produto['imagens'] = []
        
        cursor.close()
        conn.close()
        
        print(f"✅ Produtos para avaliação: {len(produtos)}")
        
        return render_template('avaliacoes-pendentes.html', produtos=produtos)
                             
    except Exception as e:
        print(f"❌ Erro ao buscar avaliações pendentes: {e}")
        flash('Erro ao carregar produtos para avaliação', 'error')
        return redirect(url_for('listar_produtos'))

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

# 🔥 FUNÇÃO CORRIGIDA - SUBSTITUI A ANTERIOR
def verificar_pagamento_banco(id_cliente):
    """Verifica se o pagamento foi confirmado - VERSÃO CORRIGIDA para 'concluido'"""
    try:
        # 1️⃣ Verifica na SESSION (mais rápido)
        if session.get('pagamento_confirmado'):
            return True
        
        # 2️⃣ Verifica no BANCO (backup)
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id_pedido, status 
            FROM pedidos 
            WHERE id_cliente = %s 
            ORDER BY id_pedido DESC 
            LIMIT 1
        """, (id_cliente,))
        
        pedido = cursor.fetchone()
        cursor.close()
        conn.close()
        
        print(f"🔍 DEBUG - Pedido encontrado: {pedido}")
        
        # ✅ CORREÇÃO: Verifica por 'concluido' em vez de 'aprovado'
        if pedido and pedido.get('status') == 'concluido':
            session['pagamento_confirmado'] = True
            print(f"✅ Pedido {pedido['id_pedido']} está CONCLUÍDO - Permite avaliação")
            return True
        else:
            status_atual = pedido.get('status') if pedido else 'Nenhum pedido'
            print(f"❌ Pedido não está concluído. Status atual: {status_atual}")
            return False
        
    except Exception as e:
        print(f"Erro ao verificar pagamento: {e}")
        return False