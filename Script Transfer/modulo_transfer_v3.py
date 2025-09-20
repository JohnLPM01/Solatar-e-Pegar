# -*- coding: utf-8 -*-
########################################
# Agregador V3 - Sistema de Transferência (MVP)
# Carrega submódulos de transferência em uma única namespace global
########################################

import time
import sys

# Caminho base absoluto desta pasta v3 (ajuste conforme seu ambiente)
BASE_PATH_TRANSFER_V3 = r"c:\\Users\\Jonatha Lopes\\Documents\\Tibiame\\Tibime New\\Utilidades\\Pega e Soltar\\Script Transfer"

# 1) Debug (reuso do sistema V3 existente)
execfile(BASE_PATH_TRANSFER_V3 + r"\\debug\\debug_and_cache_v3.py", globals())

def _safe_exec_transfer(rel_path):
    try:
        execfile(BASE_PATH_TRANSFER_V3 + rel_path, globals())
    except Exception as e:
        try:
            debug_erro('TRANSFER_LOADER', 'Falha ao carregar', rel_path + ' | ' + str(e))
            script.StatusMessage('ERRO ao carregar Transfer V3: ' + rel_path)
        except:
            pass
        raise

# 2) Estado e Protocolo do MVP
_safe_exec_transfer(r"\\core_transfer_state_v3.py")
_safe_exec_transfer(r"\\core_transfer_protocol_v3.py")

# 3) Papéis: Coletor e Soltador
_safe_exec_transfer(r"\\core_transfer_collector_v3.py")
_safe_exec_transfer(r"\\core_transfer_dropper_v3.py")

########################################
# Bridge de Eventos para o Script Principal
########################################

def onScriptActivation_Transfer():
    inicializar_debug('Transfer V3 - MVP')
    transfer_reset_state()
    transfer_detect_role()
    if TRANSFER_IS_COLLECTOR:
        collector_on_activation()
    elif TRANSFER_IS_DROPPER:
        dropper_on_activation()
    else:
        script.StatusMessage('Transfer: nenhum papel identificado (nome do personagem)')

def onScriptDeactivation_Transfer():
    try:
        transfer_reset_state()
        script.StatusMessage('Transfer: desativado')
    except:
        pass

def onReceivePrivateMessage_Transfer(name, text):
    if TRANSFER_IS_COLLECTOR:
        collector_on_pm(name, text)
    elif TRANSFER_IS_DROPPER:
        dropper_on_pm(name, text)

def onReceiveItemOnGround_Transfer(x, y, z, itemId):
    if TRANSFER_IS_COLLECTOR:
        collector_on_item_ground(x, y, z, itemId)
    elif TRANSFER_IS_DROPPER:
        dropper_on_item_ground(x, y, z, itemId)

def onReceiveRemoveItemFromGround_Transfer(x, y, z):
    if TRANSFER_IS_COLLECTOR:
        collector_on_item_removed(x, y, z)
    elif TRANSFER_IS_DROPPER:
        dropper_on_item_removed(x, y, z)

def onReceiveDepotMenu_Transfer(depot_name, depot_id, depot_type, slots):
    # Persistir contexto do depot para os módulos
    try:
        script.SetVar('depot_id', depot_id)
        script.SetVar('depot_type', depot_type)
    except:
        pass
    if TRANSFER_IS_COLLECTOR:
        collector_on_depot_menu(depot_name, depot_id, depot_type, slots)
    elif TRANSFER_IS_DROPPER:
        dropper_on_depot_menu(depot_name, depot_id, depot_type, slots)

def onReceiveAddItemToDepot_Transfer(slot, itemId):
    # Disparado quando um item é armazenado no depot
    try:
        if TRANSFER_IS_COLLECTOR:
            collector_on_add_item_to_depot(slot, itemId)
        elif TRANSFER_IS_DROPPER:
            # Opcional: implementar no dropper se necessário
            pass
    except:
        pass

def onEvent_Transfer(event_name):
    # Eventos agendados
    if TRANSFER_IS_COLLECTOR:
        collector_on_event(event_name)
    elif TRANSFER_IS_DROPPER:
        dropper_on_event(event_name)

def onReceiveItemDescriptionBackpack_Transfer(itemId, name, slot):
    # Encaminha a descrição de item da mochila (necessário para a validação por nome do Soltador)
    try:
        if TRANSFER_IS_DROPPER:
            onReceiveItemDescriptionBackpack(itemId, name, slot)
    except:
        pass

def onReceiveItemDescription_Transfer(itemId, name):
    # Evento genérico disparado por LookAtBackPackSlot segundo a doc.
    try:
        if TRANSFER_IS_DROPPER:
            onReceiveItemDescription(itemId, name)
    except:
        pass

def onReceiveFullItemDescriptionEx_Transfer(itemId, name, desc1, desc2, slot):
    # Variante estendida; roteia como a de mochila se Soltador estiver ativo
    try:
        if TRANSFER_IS_DROPPER:
            onReceiveItemDescriptionBackpack(itemId, name, slot)
    except:
        pass

def onReceiveAddItemToBackpack_Transfer(slot, itemId):
    # Encaminha o add à mochila para o Soltador em modo retirada
    try:
        if TRANSFER_IS_DROPPER:
            dropper_on_add_item_to_backpack(slot, itemId)
    except:
        pass

def onReceiveItemDescriptionEx_Transfer(itemId, name, slot):
    # Variante curta (mais comum nos exemplos). Trate como descrição de mochila.
    try:
        if TRANSFER_IS_DROPPER:
            onReceiveItemDescriptionBackpack(itemId, name, slot)
    except:
        pass

########################################
# Fim agregador de Transferência V3
########################################

