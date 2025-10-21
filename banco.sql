-- ============================================
-- ATUALIZAÇÃO DO BANCO PARA PAINEL ADMIN
-- ============================================

USE loja_informatica;

-- Tabela de funcionários/admin
DROP TABLE IF EXISTS funcionarios;
CREATE TABLE funcionarios (
    id_funcionario INT PRIMARY KEY AUTO_INCREMENT,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    senha VARCHAR(255) NOT NULL,
    cargo ENUM('admin', 'gerente', 'vendedor', 'suporte') DEFAULT 'vendedor',
    ativo BOOLEAN DEFAULT TRUE,
    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultimo_login TIMESTAMP NULL,
    INDEX idx_email (email),
    INDEX idx_cargo (cargo)
);

-- Tabela de diagnósticos
DROP TABLE IF EXISTS diagnosticos;
CREATE TABLE diagnosticos (
    id_diagnostico INT PRIMARY KEY AUTO_INCREMENT,
    id_cliente INT,
    nome_cliente VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    telefone VARCHAR(20),
    tipo_equipamento VARCHAR(100) NOT NULL,
    marca VARCHAR(100),
    modelo VARCHAR(100),
    problema TEXT NOT NULL,
    sintomas TEXT,
    data_entrada TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('recebido', 'em_analise', 'diagnosticado', 'orcamento', 'aprovado', 'reparacao', 'concluido', 'entregue') DEFAULT 'recebido',
    relatorio_final TEXT,
    pecas_defeito TEXT,
    orcamento DECIMAL(10, 2) DEFAULT 0,
    observacoes TEXT,
    tecnico_responsavel INT,
    data_conclusao TIMESTAMP NULL,
    FOREIGN KEY (tecnico_responsavel) REFERENCES funcionarios(id_funcionario) ON DELETE SET NULL,
    INDEX idx_status (status),
    INDEX idx_data (data_entrada)
);

-- Tabela de logs do sistema
DROP TABLE IF EXISTS logs_sistema;
CREATE TABLE logs_sistema (
    id_log INT PRIMARY KEY AUTO_INCREMENT,
    id_funcionario INT,
    acao VARCHAR(255) NOT NULL,
    modulo VARCHAR(100) NOT NULL,
    descricao TEXT,
    ip VARCHAR(45),
    data_log TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_funcionario) REFERENCES funcionarios(id_funcionario) ON DELETE SET NULL,
    INDEX idx_modulo (modulo),
    INDEX idx_data (data_log)
);

-- Inserir admin padrão (senha: admin123)
INSERT INTO funcionarios (nome, email, senha, cargo) VALUES 
('Administrador', 'admin@ghcp.com', '$2b$12$LQv3c1yqBzwZ0Jn6aUhW.uRgOEkZG/gC6Zgv.7pBw5O8nL2pYzJQa', 'admin');

-- Adicionar campos para múltiplas imagens no produto (se não existirem)
ALTER TABLE produto 
ADD COLUMN IF NOT EXISTS imagens JSON,
ADD COLUMN IF NOT EXISTS destaque BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS peso DECIMAL(8,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS dimensoes VARCHAR(50);

-- Atualizar produtos existentes com valores padrão para novos campos
UPDATE produto SET 
    imagens = CASE WHEN imagem IS NOT NULL THEN JSON_ARRAY(imagem) ELSE JSON_ARRAY() END,
    destaque = FALSE,
    peso = 0,
    dimensoes = NULL
WHERE imagens IS NULL;

-- Trigger para logs automáticos (após inserção)
DELIMITER //
CREATE TRIGGER after_funcionario_login
AFTER UPDATE ON funcionarios
FOR EACH ROW
BEGIN
    IF NEW.ultimo_login IS NOT NULL AND (OLD.ultimo_login IS NULL OR NEW.ultimo_login != OLD.ultimo_login) THEN
        INSERT INTO logs_sistema (id_funcionario, acao, modulo, descricao)
        VALUES (NEW.id_funcionario, 'LOGIN', 'AUTENTICACAO', CONCAT('Login realizado por ', NEW.nome));
    END IF;
END//
DELIMITER ;

-- View para relatórios mensais
CREATE OR REPLACE VIEW view_relatorios_mensais AS
SELECT 
    YEAR(data_pedido) as ano,
    MONTH(data_pedido) as mes,
    COUNT(*) as total_pedidos,
    COALESCE(SUM(total), 0) as receita_total,
    COALESCE(AVG(total), 0) as ticket_medio,
    COUNT(DISTINCT id_cliente) as clientes_unicos,
    SUM(CASE WHEN status = 'cancelado' THEN 1 ELSE 0 END) as pedidos_cancelados
FROM pedidos
WHERE data_pedido IS NOT NULL
GROUP BY YEAR(data_pedido), MONTH(data_pedido)
ORDER BY ano DESC, mes DESC;

-- View para produtos mais vendidos
CREATE OR REPLACE VIEW view_produtos_mais_vendidos AS
SELECT 
    p.id_produto,
    p.nome,
    p.marca,
    p.categoria,
    COALESCE(SUM(ip.quantidade), 0) as total_vendido,
    COALESCE(SUM(ip.quantidade * ip.preco_unitario), 0) as receita_total
FROM produto p
LEFT JOIN itens_pedido ip ON p.id_produto = ip.id_produto
LEFT JOIN pedidos ped ON ip.id_pedido = ped.id_pedido AND ped.status != 'cancelado'
GROUP BY p.id_produto
ORDER BY total_vendido DESC;

-- View para clientes mais ativos
CREATE OR REPLACE VIEW view_clientes_ativos AS
SELECT 
    c.id_cliente,
    c.nome,
    c.email,
    COUNT(p.id_pedido) as total_pedidos,
    COALESCE(SUM(p.total), 0) as total_gasto,
    MAX(p.data_pedido) as ultima_compra
FROM clientes c
LEFT JOIN pedidos p ON c.id_cliente = p.id_cliente AND p.status != 'cancelado'
GROUP BY c.id_cliente
ORDER BY total_gasto DESC;

-- View para estoque crítico
CREATE OR REPLACE VIEW view_estoque_critico AS
SELECT 
    p.id_produto,
    p.nome,
    p.marca,
    p.categoria,
    p.estoque,
    p.preco,
    COALESCE(SUM(ip.quantidade), 0) as vendas_mes
FROM produto p
LEFT JOIN itens_pedido ip ON p.id_produto = ip.id_produto
LEFT JOIN pedidos ped ON ip.id_pedido = ped.id_pedido 
    AND ped.data_pedido >= DATE_SUB(CURRENT_DATE, INTERVAL 30 DAY)
    AND ped.status != 'cancelado'
WHERE p.estoque <= 10 AND p.ativo = TRUE
GROUP BY p.id_produto
ORDER BY p.estoque ASC;

-- Inserir alguns diagnósticos de exemplo
INSERT INTO diagnosticos (id_cliente, nome_cliente, email, telefone, tipo_equipamento, marca, modelo, problema, sintomas, status) VALUES
(1, 'João Silva', 'joao.silva@email.com', '(11) 99999-9999', 'Notebook', 'Dell', 'Inspiron 15', 'Não liga', 'Quando pressiono o botão power, nada acontece. A luz do carregador fica acesa normalmente.', 'recebido'),
(2, 'Maria Santos', 'maria.santos@email.com', '(11) 88888-8888', 'Desktop', 'Positivo', 'Casa', 'Lentidão extrema', 'Demora mais de 10 minutos para ligar. Travamentos constantes durante o uso.', 'em_analise'),
(NULL, 'Carlos Oliveira', 'carlos.tech@email.com', '(11) 77777-7777', 'All-in-One', 'Lenovo', 'IdeaCentre', 'Tela azul', 'Aparece tela azul com erro SYSTEM_THREAD_EXCEPTION_NOT_HANDLED após 5 minutos de uso.', 'diagnosticado');

-- Inserir alguns logs de exemplo
INSERT INTO logs_sistema (id_funcionario, acao, modulo, descricao) VALUES
(1, 'CADASTRO', 'PRODUTOS', 'Produto cadastrado: Mouse Gamer RGB'),
(1, 'LOGIN', 'AUTENTICACAO', 'Login realizado por Administrador'),
(1, 'EDICAO', 'CLIENTES', 'Cliente atualizado: João Silva');

SELECT '✅ Painel administrativo configurado com sucesso!' as mensagem;
SELECT '👑 Admin criado: admin@ghcp.com / admin123' as credenciais;
SELECT '📊 Views criadas: relatórios, produtos mais vendidos, clientes ativos, estoque crítico' as views;
SELECT '🔧 Diagnósticos de exemplo inseridos' as diagnosticos;