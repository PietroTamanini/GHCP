import json
from datetime import datetime

def from_json_filter(value):
    if value:
        try:
            return json.loads(value)
        except:
            return []
    return []

def calcular_tempo_mercado(data_cadastro):
    if data_cadastro:
        tempo_mercado = (datetime.now() - data_cadastro).days // 365
        return f"{tempo_mercado} ano(s)" if tempo_mercado > 0 else "Menos de 1 ano"
    return "Novo"