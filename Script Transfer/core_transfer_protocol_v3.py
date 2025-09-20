# -*- coding: utf-8 -*-
########################################
# V3 - Protocolo de Mensagens (MVP)
########################################

import time
import sys

########################################
# Formatos aceitos (em português conforme pedido)
# Coletor → Soltador
#   PEDIR id_item qtd
#   ACK 1
#   FIM_ITEM
#   FIM_SESSAO
# Soltador → Coletor
#   CONFIRMAR qtd
#   CONCLUIDO qtd
#   SEM_ESTOQUE qtd
########################################

def parse_mensagem(texto):
    try:
        t = texto.strip()
        partes = t.split(' ')
        cmd = partes[0].upper()
        if cmd == 'PEDIR' and len(partes) >= 3:
            return ('PEDIR', int(partes[1]), int(partes[2]))
        if cmd == 'ACK' and len(partes) >= 2:
            return ('ACK', int(partes[1]))
        if cmd == 'FIM_ITEM':
            return ('FIM_ITEM',)
        if cmd == 'FIM_SESSAO':
            return ('FIM_SESSAO',)
        if cmd == 'CONFIRMAR' and len(partes) >= 2:
            return ('CONFIRMAR', int(partes[1]))
        if cmd == 'CONCLUIDO' and len(partes) >= 2:
            return ('CONCLUIDO', int(partes[1]))
        if cmd == 'SEM_ESTOQUE' and len(partes) >= 2:
            return ('SEM_ESTOQUE', int(partes[1]))
    except:
        pass
    return ('INVALIDO', texto)

def montar_pedir(id_item, qtd):
    return 'PEDIR ' + str(id_item) + ' ' + str(qtd)

def montar_ack():
    return 'ACK 1'

def montar_fim_item():
    return 'FIM_ITEM'

def montar_fim_sessao():
    return 'FIM_SESSAO'

def montar_confirmar(qtd):
    return 'CONFIRMAR ' + str(qtd)

def montar_concluido(qtd):
    return 'CONCLUIDO ' + str(qtd)

def montar_sem_estoque(qtd):
    return 'SEM_ESTOQUE ' + str(qtd)

