# -*- coding: utf-8 -*-
########################################
# V3 - Estado e Constantes do MVP de Transferência
########################################

import time
import sys

########################################
# Configurações gerais do MVP
########################################

# Papéis detectados por nome do personagem (padrões)
# Agora suportamos configuração dinâmica via ROLES
COLETOR_NOME = 'Nywk'
SOLTADOR_NOME = 'Johmartins'

########################################
# Configuração de múltiplos itens por personagem
########################################

PERSONAGEM_ITEMS = {
    'Falconx': [
        {'item_id': 2606, 'pagina_coletor': 1, 'max_por_pagina': 10},
    ],
    'Igris': [
    ],
    'Johmartins': [
        {'item_id': 6406, 'pagina_coletor': 10, 'nome': 'Crystal stinger'},
    ],
    'Junas': [
    ],
    'Ltdn': [
        {'item_id': 6584, 'pagina_coletor': 4, 'max_por_pagina': 21, 'nome': 'Spider crystal'},
        {'item_id': 6406, 'pagina_coletor': 4, 'max_por_pagina': 21, 'nome': 'Crystal stinger'},
        {'item_id': 2598, 'pagina_coletor': 4, 'max_por_pagina': 21, 'nome': 'Crystal eye'},
        {'item_id': 6584, 'pagina_coletor': 5, 'max_por_pagina': 21, 'nome': 'Spider crystal'},
        {'item_id': 6406, 'pagina_coletor': 5, 'max_por_pagina': 21, 'nome': 'Crystal stinger'},
        {'item_id': 2598, 'pagina_coletor': 5, 'max_por_pagina': 21, 'nome': 'Crystal eye'},
        {'item_id': 5186, 'pagina_coletor': 6, 'nome': 'Leechacle'},
        {'item_id': 5186, 'pagina_coletor': 7, 'nome': 'Leechacle'},
        {'item_id': 5216, 'pagina_coletor': 8, 'nome': 'Nudelishroom'},
        {'item_id': 5216, 'pagina_coletor': 9, 'nome': 'Nudelishroom'},
        {'item_id': 2566, 'pagina_coletor': 10, 'nome': 'Focus crystal'},
        {'item_id': 2566, 'pagina_coletor': 11, 'nome': 'Focus crystal'},
        {'item_id': 6532, 'pagina_coletor': 12, 'nome': 'Nuna filet'},
        {'item_id': 6532, 'pagina_coletor': 13, 'nome': 'Nuna filet'},
        {'item_id': 5257, 'pagina_coletor': 14, 'nome': 'Adamantine'},
        {'item_id': 5257, 'pagina_coletor': 15, 'nome': 'Adamantine'},
        {'item_id': 5257, 'pagina_coletor': 16, 'nome': 'Adamantine'},
        {'item_id': 2606, 'pagina_coletor': 17, 'nome': 'Breathnut'},
    ],
    'Nywk': [
        {'item_id': 2606, 'pagina_coletor': 3, 'max_por_pagina': 28, 'nome': 'Breathnut'},
        {'item_id': 6584, 'pagina_coletor': 3, 'max_por_pagina': 14, 'nome': 'Spider crystal'},
        {'item_id': 6406, 'pagina_coletor': 3, 'max_por_pagina': 14, 'nome': 'Crystal stinger'},
        {'item_id': 2598, 'pagina_coletor': 3, 'max_por_pagina': 14, 'nome': 'Crystal eye'},
        {'item_id': 5216, 'pagina_coletor': 4, 'nome': 'Nudelishroom'},
        {'item_id': 5186, 'pagina_coletor': 5, 'nome': 'Leechacle'},
        {'item_id': 2566, 'pagina_coletor': 6, 'nome': 'Focus crystal'},
        {'item_id': 6532, 'pagina_coletor': 7, 'nome': 'Nuna filet'},
        {'item_id': 5257, 'pagina_coletor': 8, 'nome': 'Adamantine'},
    ],
    'Vectway': [
        {'item_id': 6584, 'pagina_coletor': 3, 'max_por_pagina': 21, 'nome': 'Spider crystal'},
        {'item_id': 2598, 'pagina_coletor': 3, 'max_por_pagina': 21, 'nome': 'Crystal eye'},
        {'item_id': 6406, 'pagina_coletor': 3, 'max_por_pagina': 21, 'nome': 'Crystal stinger'},
        {'item_id': 5216, 'pagina_coletor': 4, 'nome': 'Nudelishroom'},
        {'item_id': 5186, 'pagina_coletor': 5, 'nome': 'Leechacle'},
        {'item_id': 6532, 'pagina_coletor': 7, 'nome': 'Nuna filet'},
        {'item_id': 2566, 'pagina_coletor': 6, 'nome': 'Focus crystal'},
        {'item_id': 5257, 'pagina_coletor': 8, 'nome': 'Adamantine'},
    ],
}

# Mapeamento de papéis para nomes, para facilitar troca de Coletor e Soltador
ROLES = {
    'collector': COLETOR_NOME,
    'dropper': SOLTADOR_NOME,
}

# Índice do item ativo da lista de itens do personagem atual (0-based)
CURRENT_ITEM_INDEX = 0

# Tile fixo de drop (ponte de entrada/saída do depot)
DROP_TILE_X = 32059
DROP_TILE_Y = 32144
DROP_TILE_Z = 7

# Lote máximo
LOTE_MAX = 9

# Timeout de ACK (segundos) e máximo de timeouts consecutivos para abortar lote
ACK_TIMEOUT_S = 10
ACK_MAX_TIMEOUTS = 3

# Item-alvo do MVP inicial e página do Coletor
# Estes valores são atualizados dinamicamente a partir de PERSONAGEM_ITEMS
ITEM_ALVO_ID = 0# Será definido dinamicamente
ITEM_PAGINA_COLETOR = 1# Será definido dinamicamente
# Limite opcional por página para o item ativo (None = sem limite)
ITEM_CAP_POR_PAGINA = None
# Nome esperado opcional para validação por nome (None = sem validação por nome)
ITEM_ALVO_NOME = None

# Parâmetros de varredura do Soltador
MAX_TEMPO_BUSCA_MS = 15000
MAX_PAGINAS_VISITADAS = 35
########################################
# Nomes padrão por item (fallback)
########################################

ITEM_ID_DEFAULT_NAME = {
    2566: 'Focus crystal',
    2598: 'Crystal eye',
    2606: 'Breathnut',
    5186: "Leechacle's heart",
    5216: 'Nudelishroom',
    5257: 'Adamantine',
    6406: 'Crystal stinger',
    6532: 'Nuna filet',
    6584: 'Spider crystal',
}


########################################
# Estados da sessão
########################################

ESTADO_IDLE = 'IDLE'
ESTADO_PREPARANDO_LOTE = 'PREPARANDO_LOTE'
ESTADO_ENTREGANDO = 'ENTREGANDO'
ESTADO_AGUARDANDO = 'AGUARDANDO'
ESTADO_DEPOSITANDO = 'DEPOSITANDO'
ESTADO_CONCLUIDO = 'CONCLUIDO'

########################################
# Variáveis de execução (globais)
########################################

TRANSFER_IS_COLLECTOR = False
TRANSFER_IS_DROPPER = False

sessao_estado = ESTADO_IDLE
sessao_item_atual = 0
sessao_faltam = 0
sessao_lote_pedido = 0
sessao_lote_confirmado = 0
sessao_lote_entregue = 0

ack_timeouts_consecutivos = 0

# Controle de posição do último item no chão
last_item_x = 0
last_item_y = 0
last_item_z = 0
aguardando_item_no_chao = False

# Controle de depot
depot_aberto = False
depot_pagina_atual = 0

# Blacklist de slots rejeitados por nome no depósito (mantido por sessão)
# Formato da chave: "{depot_type}:{depot_id}:{slot}"
REJECTED_DEPOT_SLOTS = set()

########################################
# Helpers de estado
########################################

def transfer_reset_state():
    global sessao_estado, sessao_item_atual, sessao_faltam, sessao_lote_pedido
    global sessao_lote_confirmado, sessao_lote_entregue, ack_timeouts_consecutivos
    global last_item_x, last_item_y, last_item_z, aguardando_item_no_chao
    global depot_aberto, depot_pagina_atual
    sessao_estado = ESTADO_IDLE
    # Garante que a configuração ativa seja aplicada antes de setar o item da sessão
    try:
        transfer_apply_active_config()
    except:
        pass
    sessao_item_atual = ITEM_ALVO_ID
    sessao_faltam = 0
    sessao_lote_pedido = 0
    sessao_lote_confirmado = 0
    sessao_lote_entregue = 0
    ack_timeouts_consecutivos = 0
    last_item_x = 0
    last_item_y = 0
    last_item_z = 0
    aguardando_item_no_chao = False
    depot_aberto = False
    depot_pagina_atual = 0

def transfer_detect_role():
    global TRANSFER_IS_COLLECTOR, TRANSFER_IS_DROPPER
    global COLETOR_NOME, SOLTADOR_NOME
    try:
        nome = script.GetCharacterName()
        # Atualiza nomes dos papéis a partir de ROLES
        try:
            COLETOR_NOME = ROLES.get('collector', COLETOR_NOME)
            SOLTADOR_NOME = ROLES.get('dropper', SOLTADOR_NOME)
        except:
            pass
        TRANSFER_IS_COLLECTOR = (nome == COLETOR_NOME)
        TRANSFER_IS_DROPPER = (nome == SOLTADOR_NOME)
        if TRANSFER_IS_COLLECTOR:
            script.StatusMessage('Transfer: papel detectado = COLETOR (' + COLETOR_NOME + ')')
        elif TRANSFER_IS_DROPPER:
            script.StatusMessage('Transfer: papel detectado = SOLTADOR (' + SOLTADOR_NOME + ')')
        else:
            script.StatusMessage('Transfer: papel não identificado para o nome: ' + str(nome))
        # Aplica configuração ativa (item/página) para este personagem
        try:
            transfer_apply_active_config()
        except:
            pass
    except Exception as e:
        try:
            script.StatusMessage('Transfer: falha ao detectar papel: ' + str(e))
        except:
            pass

########################################
# Helpers de configuração dinâmica
########################################

def transfer_set_roles(collector_name, dropper_name):
    """Atualiza os papéis (coletor/soltador) de forma centralizada.

    Args:
        collector_name: Nome do personagem que atuará como Coletor
        dropper_name: Nome do personagem que atuará como Soltador

    Returns:
        None
    """
    global ROLES, COLETOR_NOME, SOLTADOR_NOME
    assert collector_name is not None and dropper_name is not None
    ROLES['collector'] = str(collector_name)
    ROLES['dropper'] = str(dropper_name)
    COLETOR_NOME = ROLES['collector']
    SOLTADOR_NOME = ROLES['dropper']

def transfer_set_active_item_index(index):
    """Define o índice do item ativo para o personagem atual.

    Args:
        index: Índice 0-based do item na lista configurada para o personagem

    Returns:
        None
    """
    global CURRENT_ITEM_INDEX
    try:
        idx = int(index)
        if idx < 0:
            idx = 0
        CURRENT_ITEM_INDEX = idx
        # Reaplica configuração ativa imediatamente
        transfer_apply_active_config()
    except:
        pass

def transfer_get_items_for_character(char_name):
    """Recupera lista de itens configurados para um personagem.

    Args:
        char_name: Nome do personagem

    Returns:
        list: Lista de dicionários {'item_id': int, 'pagina_coletor': int}
    """
    try:
        name = str(char_name)
    except:
        name = ''
    items = PERSONAGEM_ITEMS.get(name)
    if items is None:
        return []
    return items

def transfer_get_active_item_cap():
    """Retorna o limite por página configurado para o item ativo, ou None.

    Returns:
        int|None: Limite por página, se configurado; caso contrário None
    """
    try:
        return ITEM_CAP_POR_PAGINA
    except:
        return None

def _resolve_item_config(char_name, index):
    """Resolve item_id e pagina_coletor para um personagem e índice.

    Args:
        char_name: Nome do personagem
        index: Índice 0-based dentro de PERSONAGEM_ITEMS[char]

    Returns:
        tuple: (item_id:int, pagina:int, max_por_pagina:Optional[int], nome_esperado:Optional[str])
    """
    # Defaults de segurança
    item_id = ITEM_ALVO_ID
    pagina = ITEM_PAGINA_COLETOR
    cap = None
    nome_esperado = None
    try:
        items = PERSONAGEM_ITEMS.get(char_name)
        if items and len(items) > 0:
            idx = index
            if idx >= len(items):
                idx = len(items) - 1
            if idx < 0:
                idx = 0
            cfg = items[idx]
            try:
                item_id = int(cfg.get('item_id', item_id))
            except:
                pass
            try:
                pagina = int(cfg.get('pagina_coletor', pagina))
            except:
                pass
            try:
                if 'max_por_pagina' in cfg:
                    cap = int(cfg.get('max_por_pagina'))
            except:
                cap = None
            try:
                nome_esperado = cfg.get('nome')
                if nome_esperado is not None:
                    nome_esperado = str(nome_esperado)
            except:
                nome_esperado = None
    except:
        pass
    return (item_id, pagina, cap, nome_esperado)

def transfer_apply_active_config():
    """Aplica a configuração ativa (item/página) ao ambiente global.

    Escolhe o item pela combinação (personagem atual, CURRENT_ITEM_INDEX).
    Atualiza variáveis globais para manter compatibilidade com os módulos
    existentes (ITEM_ALVO_ID, ITEM_PAGINA_COLETOR).
    """
    global ITEM_ALVO_ID, ITEM_PAGINA_COLETOR, sessao_item_atual, ITEM_CAP_POR_PAGINA, ITEM_ALVO_NOME
    try:
        nome = script.GetCharacterName()
    except:
        nome = ''
    item_id, pagina, cap, nome_esperado = _resolve_item_config(nome, CURRENT_ITEM_INDEX)
    ITEM_ALVO_ID = item_id
    ITEM_PAGINA_COLETOR = pagina
    try:
        ITEM_CAP_POR_PAGINA = None if cap is None else int(cap)
    except:
        ITEM_CAP_POR_PAGINA = None
    try:
        ITEM_ALVO_NOME = None if nome_esperado is None else str(nome_esperado)
    except:
        ITEM_ALVO_NOME = None
    # Mantém a sessão alinhada com o item ativo atual
    sessao_item_atual = ITEM_ALVO_ID

########################################
# Helpers de validação por nome e blacklist de slots
########################################

def transfer_get_expected_item_name():
    """Retorna o nome esperado do item ativo (ou None se não definido)."""
    try:
        return ITEM_ALVO_NOME
    except:
        return None

def _make_rejected_key(depot_type, depot_id, slot):
    try:
        return str(int(depot_type)) + ':' + str(int(depot_id)) + ':' + str(int(slot))
    except:
        return str(depot_type) + ':' + str(depot_id) + ':' + str(slot)

def transfer_mark_rejected_slot(depot_type, depot_id, slot):
    """Marca um slot do depósito como rejeitado por nome para evitar novas tentativas.

    Args:
        depot_type: 0=inventory, 1=depotmail, 2=depot
        depot_id: id da página do depósito
        slot: índice 1-based do slot na página
    """
    try:
        key = _make_rejected_key(depot_type, depot_id, slot)
        REJECTED_DEPOT_SLOTS.add(key)
    except:
        pass

def transfer_is_slot_rejected(depot_type, depot_id, slot):
    """Retorna True se o slot do depósito foi marcado como rejeitado por nome."""
    try:
        key = _make_rejected_key(depot_type, depot_id, slot)
        return key in REJECTED_DEPOT_SLOTS
    except:
        return False

def transfer_advance_to_next_item():
    """Avança para o próximo item configurado do personagem atual (com wrap)."""
    global CURRENT_ITEM_INDEX
    try:
        nome = script.GetCharacterName()
    except:
        nome = ''
    items = transfer_get_items_for_character(nome)
    if not items or len(items) == 0:
        return
    try:
        CURRENT_ITEM_INDEX = (int(CURRENT_ITEM_INDEX) + 1) % len(items)
    except:
        CURRENT_ITEM_INDEX = 0
    try:
        transfer_apply_active_config()
    except:
        pass

