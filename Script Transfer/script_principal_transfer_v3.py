# -*- coding: utf-8 -*-
########################################
# Script Principal - Transferência V3 (MVP)
########################################

# Caminho do agregador Transfer V3
CAMINHO_MODULO_TRANSFER_V3 = r'c:\\Users\\Jonatha Lopes\\Documents\\Tibiame\\Tibime New\\Utilidades\\Pega e Soltar\\Script Transfer\\modulo_transfer_v3.py'

def limpar_console_script():
    try:
        script.ClearScriptChat()
        script.StatusMessage('Console limpo (Transfer V3)!')
    except Exception as e:
        script.StatusMessage('Erro ao limpar console (Transfer V3): ' + str(e))

def carregar_modulo_transfer_v3():
    try:
        globals_dict = globals()
        execfile(CAMINHO_MODULO_TRANSFER_V3, globals_dict)
        script.StatusMessage('Transfer V3 carregado com sucesso!')
        return True
    except Exception as e:
        script.StatusMessage('ERRO ao carregar Transfer V3: ' + str(e))
        script.StatusMessage('Verifique o caminho: ' + CAMINHO_MODULO_TRANSFER_V3)
        return False

def onScriptActivation():
    limpar_console_script()
    if carregar_modulo_transfer_v3():
        try:
            onScriptActivation_Transfer()
        except Exception as e:
            script.StatusMessage('ERRO na ativação do Transfer V3: ' + str(e))
    else:
        script.StatusMessage('Falha ao carregar Transfer V3. Deslogando...')
        try:
            script.Logout()
        except:
            pass

def onScriptDeactivation():
    try:
        onScriptDeactivation_Transfer()
    except:
        pass

def onReceivePrivateMessage(name, text):
    try:
        onReceivePrivateMessage_Transfer(name, text)
    except:
        pass

def onReceiveItemOnGround(x, y, z, itemId):
    try:
        onReceiveItemOnGround_Transfer(x, y, z, itemId)
    except:
        pass

def onReceiveRemoveItemFromGround(x, y, z):
    try:
        onReceiveRemoveItemFromGround_Transfer(x, y, z)
    except:
        pass

def onReceiveDepotMenu(depot_name, depot_id, depot_type, slots):
    try:
        onReceiveDepotMenu_Transfer(depot_name, depot_id, depot_type, slots)
    except:
        pass

def onReceiveItemDescriptionBackpack(itemId, name, slot):
    try:
        onReceiveItemDescriptionBackpack_Transfer(itemId, name, slot)
    except:
        pass

def onReceiveItemDescription(itemId, name):
    try:
        onReceiveItemDescription_Transfer(itemId, name)
    except:
        pass

def onReceiveFullItemDescriptionEx(itemId, name, desc1, desc2, slot):
    try:
        onReceiveFullItemDescriptionEx_Transfer(itemId, name, desc1, desc2, slot)
    except:
        pass

def onReceiveItemDescriptionEx(itemId, name, slot):
    try:
        onReceiveItemDescriptionEx_Transfer(itemId, name, slot)
    except:
        pass

def onReceiveAddItemToDepot(slot, itemId):
    try:
        onReceiveAddItemToDepot_Transfer(slot, itemId)
    except:
        pass

def onEvent(event_name):
    try:
        onEvent_Transfer(event_name)
    except:
        pass

def onReceiveAddItemToBackpack(slot, itemId):
    try:
        onReceiveAddItemToBackpack_Transfer(slot, itemId)
    except:
        pass

