respostas = {
    "como cadastrar": "Para cadastrar um item, vá no menu 'Cadastro' e clique em 'Novo'.",
    "esqueci a senha": "Clique na opção 'Recuperar Senha' na tela de login.",
    "erro 404": "Isso significa que a página solicitada não foi encontrada.",
    "como excluir": "Vá na listagem, selecione o item e clique no botão 'Excluir'."
}

def responder(pergunta):
    pergunta = pergunta.lower()

    for chave in respostas:
        if chave in pergunta:
            return respostas[chave]

    return "Não entendi sua dúvida. Tente perguntar de outra forma!"
