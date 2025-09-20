# -*- coding: utf-8 -*-
########################################
# V3 - Lado Soltador (MVP)
########################################

import time
import sys

########################################
# Constantes de tempo e watchdog
########################################
WAITING_MENU_RECHECK_MS = 1100  # Delay quando aguardando novo menu após DepotGoNext
ACK_TIMEOUT_MS = 10000          # 10s aguardando ACK 1 do coletor
ACK_MAX_TIMEOUTS = 3            # Após 3 timeouts, finalizar parcial

# Flag de debug conciso para o fast-path de drop
TRANSFER_DROP_FAST_DEBUG = True

# Janela curta para confiar no ACK após DropItem retornar ok
ACK_SHORT_CONFIRM_MS = 1000     # 1s para aguardar ACK antes de validar por contador

# Cadência mais rápida após ACK e tempos reduzidos no caminho alternativo
NEXT_DROP_AFTER_ACK_MS = 200    # próximo drop após ACK (delay ligeiramente maior para estabilidade)
ALT_RETRY_SLEEP_1_MS = 300      # primeira espera curta no caminho alternativo
ALT_RETRY_SLEEP_2_MS = 300      # segunda espera curta no caminho alternativo
RETRY_NEXT_DROP_MS = 600        # reagenda novo drop após falha
PM_SEND_DELAY_MS = 200          # pequeno atraso antes de enviar PM

########################################
# Estado auxiliar para confirmação curta pós-drop
########################################
dropper_pending_confirm = False
dropper_pending_quantidade_antes = 0
dropper_pending_slot_item = 0

########################################
# Validação por nome (retirada com checagem)
########################################
name_check_pending = False
name_check_expected = None
name_check_depot_type = 2
name_check_depot_id = 0
name_check_depot_slot = 0
name_check_backpack_slot = 0
name_check_timeout_armed = False
name_check_attempts = 0

########################################
# Importa variáveis/funcões do estado e protocolo (mesmo namespace via execfile)
########################################

def _soltador_log(msg):
    try:
        script.StatusMessage('[SOLTADOR] ' + str(msg))
    except:
        pass
    try:
        debug_log('SOLTADOR', str(msg), 'INFO')
    except:
        pass

def _trace_fast(msg):
    if not TRANSFER_DROP_FAST_DEBUG:
        return
    try:
        debug_log('SOLTADOR', '[FAST] ' + str(msg), 'DEBUG')
    except:
        pass

def _soltador_pm_coletor(texto):
    try:
        try:
            time.sleep(PM_SEND_DELAY_MS / 1000.0)
        except:
            pass
        script.SendPM(COLETOR_NOME, texto)
    except:
        pass

def dropper_on_activation():
    _soltador_log('Ativado e aguardando pedidos do Coletor: ' + COLETOR_NOME)

def dropper_on_pm(name, text):
    # Autoriza apenas o Coletor configurado
    try:
        if name != COLETOR_NOME:
            return
    except:
        pass
    cmd = parse_mensagem(text)
    if cmd[0] == 'PEDIR':
        try:
            debug_log('SOLTADOR', 'Recebido PM PEDIR: item=' + str(cmd[1]) + ' qtd=' + str(cmd[2]), 'INFO')
        except:
            pass
        _soltador_on_pedir(cmd[1], cmd[2])
    elif cmd[0] == 'ACK':
        _soltador_on_ack(cmd[1])

def _soltador_on_pedir(item_id, qtd):
    # Atualiza dinamicamente o item alvo da sessão para atender ao pedido do coletor
    global ITEM_ALVO_ID
    try:
        ITEM_ALVO_ID = int(item_id)
    except:
        ITEM_ALVO_ID = item_id
    # Vai para o tile de drop
    try:
        script.GoToLocationEx(DROP_TILE_X, DROP_TILE_Y, DROP_TILE_Z)
    except:
        pass
    # Confirmação: não confiar apenas em GetItemsCount (pode não incluir depot conforme cliente)
    qtd_req = 0
    try:
        qtd_req = max(0, int(qtd))
    except:
        qtd_req = 0
    if qtd_req <= 0:
        _soltador_pm_coletor(montar_sem_estoque(0))
        return
    estoque_total = 0
    try:
        estoque_total = script.GetItemsCount(item_id, True)
    except:
        estoque_total = 0
    # Se estoque_total for 0 ou desconhecido, ainda confirmamos o pedido e vamos retirar do depot
    confirmar = qtd_req if estoque_total <= 0 else min(qtd_req, estoque_total)
    _soltador_pm_coletor(montar_confirmar(confirmar))
    try:
        debug_log('SOLTADOR', 'Enviado PM CONFIRMAR: ' + str(confirmar), 'INFO')
    except:
        pass
    # Inicia ciclo de retirada no depot para encher a mochila com a quantidade confirmada
    # Inicia ciclo de retirada com pequena defasagem para garantir que chegou ao tile
    try:
        script.RunEventEx('dropper_start_retrieve', confirmar, 450)
    except:
        _iniciar_retirada(confirmar)

def _iniciar_entrega(qtd_confirmada):
    global sessao_lote_confirmado, sessao_lote_entregue
    global dropper_waiting_ack, dropper_ack_timeouts, dropper_ack_watchdog_scheduled, dropper_ack_wait_start_ms
    sessao_lote_confirmado = qtd_confirmada
    sessao_lote_entregue = 0
    dropper_waiting_ack = False
    dropper_ack_timeouts = 0
    dropper_ack_watchdog_scheduled = False
    dropper_ack_wait_start_ms = 0
    script.RunEvent('dropper_drop_proximo', 300)

def dropper_on_event(event_name):
    if event_name == 'dropper_drop_proximo':
        _dropper_drop_proximo()
    elif event_name == 'dropper_retrieve_cycle':
        _dropper_retrieve_cycle()
    elif event_name == 'dropper_ack_watchdog':
        _dropper_ack_watchdog()
    elif event_name == 'dropper_wait_menu_recheck':
        _dropper_wait_menu_recheck()
    elif event_name == 'dropper_name_check_timeout':
        _dropper_name_check_timeout()

def dropper_start_retrieve(qtd_confirmada):
    """Entrada compatível com RunEventEx para iniciar a retirada com atraso controlado."""
    try:
        _iniciar_retirada(qtd_confirmada)
    except Exception as e:
        try:
            debug_log('SOLTADOR', 'Erro em dropper_start_retrieve: ' + str(e), 'ERROR')
        except:
            pass

# Wrappers para compatibilidade com RunEvent chamando métodos diretamente
def dropper_retrieve_cycle():
    try:
        _dropper_retrieve_cycle()
    except Exception as e:
        try:
            debug_log('SOLTADOR', 'Erro em dropper_retrieve_cycle: ' + str(e), 'ERROR')
        except:
            pass

def dropper_drop_proximo():
    try:
        _dropper_drop_proximo()
    except Exception as e:
        try:
            debug_log('SOLTADOR', 'Erro em dropper_drop_proximo: ' + str(e), 'ERROR')
        except:
            pass

# Estado interno de retirada
dropper_retrieve_target = 0
dropper_retrieved = 0
dropper_pages_visited = set()
dropper_retrieve_start_ms = 0
dropper_wrap_attempted = False
dropper_waiting_ack = False
dropper_waiting_menu = False
dropper_nav_steps = 0
dropper_waiting_menu = False
dropper_nav_steps = 0
dropper_ack_wait_start_ms = 0
dropper_ack_timeouts = 0
dropper_ack_watchdog_scheduled = False
sessao_lote_confirmado = 0
sessao_lote_entregue = 0
dropper_session_active = False
dropper_wait_menu_recheck_scheduled = False

########################################
# Seção: Reset de Estado do Soltador
########################################
def _dropper_reset_total():
    """Reseta completamente o estado do Soltador para aguardar novo pedido.

    Fecha menus, sai do depot, limpa flags e contadores e desarma watchdogs.
    """
    global dropper_pending_confirm, dropper_pending_quantidade_antes, dropper_pending_slot_item
    global dropper_retrieve_target, dropper_retrieved, dropper_pages_visited, dropper_retrieve_start_ms
    global dropper_wrap_attempted, dropper_waiting_ack, dropper_waiting_menu, dropper_nav_steps
    global dropper_ack_wait_start_ms, dropper_ack_timeouts, dropper_ack_watchdog_scheduled
    global sessao_lote_confirmado, sessao_lote_entregue, dropper_session_active
    # Tenta normalizar UI/estado do cliente
    try:
        if script.IsUsingMenu():
            script.CloseMenu()
    except:
        pass
    try:
        if script.IsInShop():
            script.LeaveShop()
    except:
        pass
    try:
        script.SetVar('depotMode', 0)
    except:
        pass
    # Limpa confirmações pendentes
    dropper_pending_confirm = False
    dropper_pending_quantidade_antes = 0
    dropper_pending_slot_item = 0
    # Limpa estado de retirada
    dropper_retrieve_target = 0
    dropper_retrieved = 0
    dropper_pages_visited = set()
    dropper_retrieve_start_ms = 0
    dropper_wrap_attempted = False
    dropper_waiting_menu = False
    dropper_nav_steps = 0
    # Limpa estado de ACK/watchdog
    dropper_waiting_ack = False
    dropper_ack_wait_start_ms = 0
    dropper_ack_timeouts = 0
    dropper_ack_watchdog_scheduled = False
    # Limpa sessão atual
    sessao_lote_confirmado = 0
    sessao_lote_entregue = 0
    dropper_session_active = False
    # Garante reposicionamento no tile de drop
    try:
        script.GoToLocationEx(DROP_TILE_X, DROP_TILE_Y, DROP_TILE_Z)
    except:
        pass
    # Mensagem como no início (ativado/aguardando)
    try:
        dropper_on_activation()
    except:
        try:
            _soltador_log('Aguardando próximo pedido...')
        except:
            pass
    try:
        debug_log('SOLTADOR', 'Estado resetado para idle no tile de drop.', 'INFO')
    except:
        pass

def _iniciar_retirada(qtd_confirmada):
    global dropper_retrieve_target, dropper_retrieved, dropper_pages_visited, dropper_retrieve_start_ms
    global dropper_wrap_attempted, dropper_waiting_menu, dropper_nav_steps, dropper_session_active
    dropper_retrieve_target = max(0, int(qtd_confirmada))
    dropper_retrieved = 0
    dropper_pages_visited = set()
    dropper_retrieve_start_ms = int(time.time() * 1000)
    dropper_wrap_attempted = False
    dropper_waiting_menu = False
    dropper_nav_steps = 0
    dropper_session_active = True
    # Garante posicionamento próximo ao depot antes de tentar entrar
    try:
        script.GoToLocationEx(DROP_TILE_X, DROP_TILE_Y, DROP_TILE_Z)
        time.sleep(0.25)
    except:
        pass
    # Entra no depot
    for tentativa in range(3):
        entrou = False
        try:
            entrou = script.EnterShop()
        except:
            entrou = False
        if entrou:
            break
        try:
            debug_log('SOLTADOR', 'EnterShop falhou (tentativa ' + str(tentativa + 1) + '). Reposicionando e tentando de novo...', 'WARNING')
        except:
            pass
        try:
            script.GoToLocationEx(DROP_TILE_X, DROP_TILE_Y, DROP_TILE_Z)
        except:
            pass
        time.sleep(0.35)
    if not entrou:
        _soltador_log('Falha ao entrar no depot para retirar. Tentando novamente...')
        try:
            debug_log('SOLTADOR', 'EnterShop falhou. Reagendando ciclo', 'WARNING')
        except:
            pass
        script.RunEvent('dropper_retrieve_cycle', 1500)
        return
    try:
        debug_log('SOLTADOR', 'EnterShop OK. Iniciando ciclo de retirada', 'INFO')
    except:
        pass
    try:
        script.SetVar('depotMode', 2)
        debug_log('SOLTADOR', 'depotMode=2 (retirada) setado', 'INFO')
    except:
        pass
    # Ao entrar no depot, aguardamos explicitamente o primeiro onReceiveDepotMenu
    dropper_waiting_menu = True
    # Agenda rechecagem simples do menu, como no método do script clássico
    try:
        global dropper_wait_menu_recheck_scheduled
        if not dropper_wait_menu_recheck_scheduled:
            script.RunEvent('dropper_wait_menu_recheck', WAITING_MENU_RECHECK_MS)
            dropper_wait_menu_recheck_scheduled = True
    except:
        pass
    # Não iniciar ciclo agora; será disparado pelo onReceiveDepotMenu

def _dropper_retrieve_cycle():
    global dropper_retrieve_target, dropper_retrieved, dropper_pages_visited, dropper_waiting_menu, dropper_nav_steps, dropper_session_active
    try:
        debug_log('SOLTADOR', 'Ciclo retirar: alvo=' + str(dropper_retrieve_target) + ' retirados=' + str(dropper_retrieved), 'INFO')
    except:
        pass
    # Se não há sessão ativa, ignora eventos disparados tardiamente
    if not dropper_session_active:
        return
    # Se há verificação de nome pendente, aguarda callback para não misturar itens
    try:
        if name_check_pending:
            try:
                debug_log('SOLTADOR', 'Aguardando verificação de nome pendente (slot mochila=' + str(name_check_backpack_slot) + ')', 'DEBUG')
            except:
                pass
            return
    except:
        pass
    # Se estamos aguardando menu, não fazemos nada aqui. Espera onReceiveDepotMenu
    if dropper_waiting_menu:
        return
    # Condições de parada
    if dropper_retrieved >= dropper_retrieve_target:
        # Fecha menus abertos antes de iniciar entrega, para evitar ficar preso em inventory/depotmail
        try:
            script.ForceCloseInventory()
        except:
            pass
        try:
            script.ForceCloseMenus()
        except:
            pass
        try:
            script.LeaveShop()
        except:
            pass
        try:
            script.SetVar('depotMode', 0)
            debug_log('SOLTADOR', 'depotMode=0 (idle) após concluir retirada', 'INFO')
        except:
            pass
        # Inicia drops com a quantidade REALMENTE retirada
        _iniciar_entrega(dropper_retrieved)
        return
    # Verifica se está no depot
    if not script.IsInShop():
        entrou = False
        try:
            entrou = script.EnterShop()
        except:
            entrou = False
        if not entrou:
            try:
                debug_log('SOLTADOR', 'EnterShop falhou durante ciclo. Reposicionando e tentando de novo...', 'WARNING')
            except:
                pass
            try:
                script.GoToLocationEx(DROP_TILE_X, DROP_TILE_Y, DROP_TILE_Z)
            except:
                pass
            script.RunEvent('dropper_retrieve_cycle', 1200)
            return
        try:
            script.SetVar('depotMode', 2)
            debug_log('SOLTADOR', 'depotMode=2 (retirada) ao reentrar', 'INFO')
        except:
            pass
    # Identifica página atual
    depot_id = 0
    depot_type = 2
    try:
        depot_id = script.GetVar('depot_id')
        depot_type = script.GetVar('depot_type')
    except:
        pass
    try:
        debug_log('SOLTADOR', 'Depot contexto: tipo=' + str(depot_type) + ' id=' + str(depot_id) + ' waiting_menu=' + str(dropper_waiting_menu) + ' nav_steps=' + str(dropper_nav_steps), 'INFO')
    except:
        pass
    pagina_key = str(depot_type) + '_' + str(depot_id)
    # Busca slot do item na página atual (pula slots previamente rejeitados por nome)
    slot = -1
    try:
        if depot_type == 0:
            items = script.GetInventoryItems()
        elif depot_type == 1:
            items = script.GetDepotmailItems()
        elif depot_type == 2:
            items = script.GetCurrentDepotItems()
        else:
            items = script.GetCurrentDepotItems()
        if items is not None:
            try:
                debug_log('SOLTADOR', 'Página itens len=' + str(len(items)) + ' procurando id=' + str(ITEM_ALVO_ID), 'DEBUG')
            except:
                pass
            for i in range(len(items)):
                if items[i] == ITEM_ALVO_ID:
                    candidate = i + 1
                    try:
                        if transfer_is_slot_rejected(depot_type, depot_id, candidate):
                            try:
                                debug_log('SOLTADOR', 'Slot ' + str(candidate) + ' ignorado (blacklist por nome)', 'DEBUG')
                            except:
                                pass
                            continue
                    except:
                        pass
                    slot = candidate
                    break
    except:
        slot = -1
    if slot != -1:
        # Se mochila cheia, encerra retirada e inicia entrega parcial
        try:
            free_slot = script.GetFreeBackpackSlot()
        except:
            free_slot = 0
        if free_slot == 255:
            try:
                debug_log('SOLTADOR', 'Backpack cheia durante retirada. Iniciando entrega parcial.', 'WARNING')
            except:
                pass
            try:
                script.LeaveShop()
            except:
                pass
            if dropper_retrieved == 0:
                _soltador_pm_coletor(montar_sem_estoque(0))
                return
            _iniciar_entrega(dropper_retrieved)
            return
        ok = False
        # Nome esperado: usar sempre o nome padrão do item solicitado
        # Não usar transfer_get_expected_item_name() pois retorna a configuração do soltador
        expected_name = None
        try:
            expected_name = ITEM_ID_DEFAULT_NAME.get(ITEM_ALVO_ID)
        except:
            expected_name = None
        try:
            debug_log('SOLTADOR', 'Slot candidato=' + str(slot) + ' expected_name=' + str(expected_name), 'DEBUG')
        except:
            pass
        # Se vamos validar por nome, direcione para um slot conhecido da mochila
        to_backpack_slot = 0
        try:
            to_backpack_slot = free_slot
        except:
            to_backpack_slot = 0
        try:
            if expected_name is None:
                ok = script.RetrieveSlotToBackpack(slot, depot_type)
            else:
                try:
                    debug_log('SOLTADOR', 'RetrieveSlotToBackpackSlot(slot=' + str(slot) + ', to=' + str(to_backpack_slot) + ', type=' + str(depot_type) + ')', 'DEBUG')
                except:
                    pass
                ok = script.RetrieveSlotToBackpackSlot(slot, to_backpack_slot, depot_type)
        except:
            ok = False
        if ok:
            # Se não há verificação por nome, mantém fluxo antigo
            if expected_name is None:
                dropper_retrieved += 1
                _soltador_log('Retirado do depot (' + str(dropper_retrieved) + '/' + str(dropper_retrieve_target) + ')')
                try:
                    debug_log('SOLTADOR', 'Retrieve OK slot=' + str(slot) + ' tipo=' + str(depot_type), 'INFO')
                except:
                    pass
                # Pequeno delay para estabilizar inventário antes do próximo ciclo
                try:
                    time.sleep(0.15)
                except:
                    pass
                script.RunEvent('dropper_retrieve_cycle', 400)
                return
            # Verificação por nome: aguardar descrição automática do item recém-retirado
            try:
                global name_check_pending, name_check_expected, name_check_depot_type, name_check_depot_id, name_check_depot_slot, name_check_backpack_slot, name_check_timeout_armed
                name_check_pending = True
                name_check_expected = str(expected_name)
                name_check_depot_type = depot_type
                name_check_depot_id = depot_id
                name_check_depot_slot = slot
                name_check_backpack_slot = to_backpack_slot
                name_check_timeout_armed = False
                # reset tentativas
                try:
                    global name_check_attempts
                    name_check_attempts = 0
                except:
                    pass
            except:
                pass
            # Arma um timeout brando para aguardar onReceiveItemDescription* após a retirada
            try:
                script.RunEvent('dropper_name_check_timeout', 1200)
                name_check_timeout_armed = True
                debug_log('SOLTADOR', 'Aguardando descrição automática do item retirado (timeout 1200ms)', 'DEBUG')
            except:
                pass
            return
        # Falha ao retirar, tenta novamente um pouco depois
        try:
            debug_log('SOLTADOR', 'Retrieve FALHOU slot=' + str(slot) + ' tipo=' + str(depot_type) + ' (to_backpack_slot=' + str(to_backpack_slot) + ' expected_name=' + str(expected_name) + ')', 'WARNING')
        except:
            pass
        script.RunEvent('dropper_retrieve_cycle', 800)
        return
    # Sem item nesta página: continua varredura com DepotGoNext() e espera menu
    if pagina_key not in dropper_pages_visited:
        dropper_pages_visited.add(pagina_key)
    # Timeout ou páginas demais?
    try:
        now_ms = int(time.time() * 1000)
    except:
        now_ms = 0
    if (now_ms - dropper_retrieve_start_ms) > MAX_TEMPO_BUSCA_MS or len(dropper_pages_visited) >= MAX_PAGINAS_VISITADAS:
        try:
            debug_log('SOLTADOR', 'Fim da varredura por timeout/limite. Entregando parcial.', 'WARNING')
        except:
            pass
        try:
            script.LeaveShop()
        except:
            pass
        try:
            script.SetVar('depotMode', 0)
            debug_log('SOLTADOR', 'depotMode=0 (idle) por mochila cheia', 'INFO')
        except:
            pass
        if dropper_retrieved == 0:
            _soltador_pm_coletor(montar_sem_estoque(0))
            return
        _iniciar_entrega(dropper_retrieved)
        return
    # Apenas DepotGoNext(): chama UMA vez e aguarda próximo menu (sem martelar)
    if not dropper_waiting_menu:
        try:
            debug_log('SOLTADOR', 'DepotGoNext() chamado', 'INFO')
        except:
            pass
        try:
            script.DepotGoNext()
        except:
            pass
        dropper_waiting_menu = True
        dropper_nav_steps += 1
        # Agenda rechecagem do menu para evitar travar aguardando indefinidamente
        try:
            global dropper_wait_menu_recheck_scheduled
            if not dropper_wait_menu_recheck_scheduled:
                script.RunEvent('dropper_wait_menu_recheck', WAITING_MENU_RECHECK_MS)
                dropper_wait_menu_recheck_scheduled = True
        except:
            pass
    # Não reagendar ciclo aqui. Espera o próximo onReceiveDepotMenu, como em Soltar_intdp.DoRetrieve
    return

def _dropper_drop_proximo():
    global sessao_lote_entregue, sessao_lote_confirmado, dropper_session_active
    global dropper_waiting_ack, dropper_ack_wait_start_ms, dropper_ack_watchdog_scheduled
    # Se não há sessão ativa, não faz nada
    if not dropper_session_active:
        return
    # Não soltar dentro do depot
    if script.IsInShop():
        try:
            script.LeaveShop()
        except:
            pass
        script.RunEvent('dropper_drop_proximo', 500)
        return
    # Não soltar com menus abertos (inventory/depotmail) — fecha antes
    try:
        if script.IsUsingMenu():
            script.CloseMenu()
            time.sleep(0.2)
    except:
        pass
    if sessao_lote_entregue >= sessao_lote_confirmado:
        _soltador_pm_coletor(montar_concluido(sessao_lote_entregue))
        # Ao concluir o último item, reseta todo estado e aguarda próximo pedido
        _dropper_reset_total()
        return
    if dropper_waiting_ack:
        try:
            debug_log('SOLTADOR', 'Aguardando ACK do coletor. Não vai soltar novo item ainda.', 'INFO')
        except:
            pass
        return
    # Verifica se temos item no backpack; se não, tenta retirar do depot caso esteja dentro
    try:
        quantidade = script.GetItemsCount(ITEM_ALVO_ID, False)
    except:
        quantidade = 0
    if quantidade == 0:
        # Tenta recuperar 1 do depot se estiver dentro
        if script.IsInShop():
            try:
                items = script.GetCurrentDepotItems()
                slot = -1
                if items is not None:
                    for i in range(len(items)):
                        if items[i] == ITEM_ALVO_ID:
                            slot = i + 1
                            break
                if slot != -1:
                    if script.RetrieveSlotToBackpack(slot, 2):
                        time.sleep(0.3)
                        quantidade = script.GetItemsCount(ITEM_ALVO_ID, False)
            except:
                pass
        if quantidade == 0:
            _soltador_pm_coletor(montar_sem_estoque(sessao_lote_entregue))
            return
    # Encontra slot do item e tenta soltar
    slot_item = 0
    try:
        slot_item = script.GetItemSlot(ITEM_ALVO_ID)
    except:
        slot_item = 0
    if slot_item == 0:
        try:
            items = script.GetBackpackItems()
            if items is not None:
                for i in range(len(items)):
                    if items[i] == ITEM_ALVO_ID:
                        slot_item = i + 1
                        break
        except:
            slot_item = 0
    if slot_item == 0:
        _soltador_pm_coletor(montar_sem_estoque(sessao_lote_entregue))
        return
    # Medição antes/depois para validar que o item realmente saiu do backpack
    quantidade_antes = 0
    try:
        quantidade_antes = script.GetItemsCount(ITEM_ALVO_ID, False)
    except:
        quantidade_antes = 0
    # Garantias finais: não estar em shop/menu antes de dropar
    try:
        if script.IsInShop():
            _trace_fast('LeaveShop antes de dropar')
            script.LeaveShop()
            time.sleep(0.3)
    except:
        pass
    try:
        if script.IsUsingMenu():
            _trace_fast('CloseMenu antes de dropar')
            script.CloseMenu()
            time.sleep(0.3)
    except:
        pass
    try:
        script.PZChecksForDrop(0)
    except:
        pass
    time.sleep(0.2)
    resultado = ''
    try:
        _trace_fast('DropItem slot=' + str(slot_item) + ' modo=1')
        resultado = script.DropItem(slot_item, 1)
    except:
        resultado = ''
    # Início do fluxo: confiar primeiro no ACK curto; só depois validar por contador
    if (resultado == 'ok' or resultado == '[ok]'):
        # Marca confirmação pendente e passa a aguardar ACK
        global dropper_pending_confirm, dropper_pending_quantidade_antes, dropper_pending_slot_item
        dropper_pending_confirm = True
        dropper_pending_quantidade_antes = quantidade_antes
        dropper_pending_slot_item = slot_item
        # Inicia espera por ACK
        global dropper_waiting_ack, dropper_ack_wait_start_ms, dropper_ack_watchdog_scheduled
        dropper_waiting_ack = True
        try:
            dropper_ack_wait_start_ms = int(time.time() * 1000)
        except:
            dropper_ack_wait_start_ms = 0
        if not dropper_ack_watchdog_scheduled:
            try:
                script.RunEvent('dropper_ack_watchdog', 1000)
            except:
                pass
            dropper_ack_watchdog_scheduled = True
        # Janela curta para validação por contador caso ACK não chegue (com atraso levemente maior)
        try:
            script.RunEvent('dropper_confirm_after_short_ack', ACK_SHORT_CONFIRM_MS + 200)
        except:
            pass
        # Verificação imediata por contador: se já reduziu, contabiliza agora e não aguarda confirmação tardia/ACK
        try:
            time.sleep(0.2)
        except:
            pass
        quantidade_depois_now = dropper_pending_quantidade_antes
        try:
            quantidade_depois_now = script.GetItemsCount(ITEM_ALVO_ID, False)
        except:
            quantidade_depois_now = dropper_pending_quantidade_antes
        if quantidade_depois_now < dropper_pending_quantidade_antes:
            try:
                sessao_lote_entregue = int(sessao_lote_entregue) + 1
            except:
                sessao_lote_entregue = sessao_lote_entregue + 1
            _soltador_log('Soltado 1 (' + str(sessao_lote_entregue) + '/' + str(sessao_lote_confirmado) + ')')
            dropper_pending_confirm = False
            try:
                script.CancelEvent('dropper_confirm_after_short_ack')
            except:
                pass
            # Desarma espera de ACK para não duplicar contagem
            dropper_waiting_ack = False
            dropper_ack_watchdog_scheduled = False
            dropper_ack_wait_start_ms = 0
            try:
                script.RunEvent('dropper_drop_proximo', NEXT_DROP_AFTER_ACK_MS)
            except:
                pass
            return
        return
    else:
        # Drop falhou imediatamente; tenta alternativa curta
        try:
            script.PZChecksForDrop(0)
        except:
            pass
        time.sleep((ALT_RETRY_SLEEP_1_MS + 100) / 1000.0)
        alt_res = ''
        try:
            _trace_fast('DropItem slot=' + str(slot_item) + ' modo=0 (alternativa)')
            alt_res = script.DropItem(slot_item, 0)
        except:
            alt_res = ''
        time.sleep((ALT_RETRY_SLEEP_2_MS + 100) / 1000.0)
        try:
            script.PZChecksForDrop(1)
        except:
            pass
        if (alt_res == 'ok' or alt_res == '[ok]'):
            # Mesma lógica: aguardará ACK e confirmação curta
            global dropper_pending_confirm, dropper_pending_quantidade_antes, dropper_pending_slot_item
            dropper_pending_confirm = True
            dropper_pending_quantidade_antes = quantidade_antes
            dropper_pending_slot_item = slot_item
            global dropper_waiting_ack, dropper_ack_wait_start_ms, dropper_ack_watchdog_scheduled
            dropper_waiting_ack = True
            try:
                dropper_ack_wait_start_ms = int(time.time() * 1000)
            except:
                dropper_ack_wait_start_ms = 0
            if not dropper_ack_watchdog_scheduled:
                try:
                    script.RunEvent('dropper_ack_watchdog', 1000)
                except:
                    pass
                dropper_ack_watchdog_scheduled = True
            try:
                script.RunEvent('dropper_confirm_after_short_ack', ACK_SHORT_CONFIRM_MS + 200)
            except:
                pass
            # Verificação imediata por contador (caminho alternativo)
            try:
                time.sleep(0.2)
            except:
                pass
            alt_depois_now = dropper_pending_quantidade_antes
            try:
                alt_depois_now = script.GetItemsCount(ITEM_ALVO_ID, False)
            except:
                alt_depois_now = dropper_pending_quantidade_antes
            if alt_depois_now < dropper_pending_quantidade_antes:
                try:
                    sessao_lote_entregue = int(sessao_lote_entregue) + 1
                except:
                    sessao_lote_entregue = sessao_lote_entregue + 1
                _soltador_log('Soltado 1 (' + str(sessao_lote_entregue) + '/' + str(sessao_lote_confirmado) + ')')
                dropper_pending_confirm = False
                try:
                    script.CancelEvent('dropper_confirm_after_short_ack')
                except:
                    pass
                dropper_waiting_ack = False
                dropper_ack_watchdog_scheduled = False
                dropper_ack_wait_start_ms = 0
                try:
                    script.RunEvent('dropper_drop_proximo', NEXT_DROP_AFTER_ACK_MS)
                except:
                    pass
                return
            return
        # Alternativa também falhou: reagendar novo drop
        _soltador_log('Falha ao soltar. Tentando novamente...')
        try:
            script.RunEvent('dropper_drop_proximo', RETRY_NEXT_DROP_MS)
        except:
            pass
        return

def dropper_on_item_ground(x, y, z, itemId):
    # O Soltador não precisa reagir diretamente; usa PM/contador
    pass

def dropper_on_item_removed(x, y, z):
    # Sem ação; a cadência é temporizada e dirigida pelo lote/contador
    pass

def dropper_on_left_shop():
    """Limpa flags de menu/espera ao sair do shop para evitar estados presos na reentrada."""
    global dropper_waiting_menu, dropper_wait_menu_recheck_scheduled
    dropper_waiting_menu = False
    dropper_wait_menu_recheck_scheduled = False
    try:
        debug_log('SOLTADOR', 'onReceiveLeftShop: limpando flags de menu/espera', 'DEBUG')
    except:
        pass
    # Reposiciona no tile de drop ao sair do depot
    try:
        script.GoToLocationEx(DROP_TILE_X, DROP_TILE_Y, DROP_TILE_Z)
    except:
        pass

def onReceiveLeftShop():
    try:
        dropper_on_left_shop()
    except:
        pass

def dropper_on_depot_menu(depot_name, depot_id, depot_type, slots):
    # Dispara o ciclo de retirada quando o menu muda; logs e ações apenas em modo de retirada
    global dropper_waiting_menu
    modo = 0
    try:
        modo = script.GetVar('depotMode')
    except:
        modo = 0
    if modo != 2:
        # Fora de retirada: fecha menus pendentes e ignora (evita ficar preso ao reentrar)
        try:
            script.ForceCloseInventory()
        except:
            pass
        try:
            script.ForceCloseMenus()
        except:
            pass
        return
    try:
        debug_log('SOLTADOR', 'onReceiveDepotMenu: tipo=' + str(depot_type) + ' id=' + str(depot_id) + ' slots=' + str(slots), 'INFO')
    except:
        pass
    # Qualquer menu recebido encerra o estado de "aguardando menu" anterior
    dropper_waiting_menu = False
    try:
        global dropper_wait_menu_recheck_scheduled
        dropper_wait_menu_recheck_scheduled = False
    except:
        pass
    # Padrão igual ao Soltar_intdp: não navegar aqui. Apenas acionar o ciclo de retirada.
    script.RunEvent('dropper_retrieve_cycle', 300)

def dropper_confirm_after_short_ack():
    """
    Confirmação tardia após janela curta de ACK.
    Se não chegou ACK em ACK_SHORT_CONFIRM_MS, valida pelo contador
    e, em último caso, tenta alternativa leve antes de desistir.
    """
    global dropper_pending_confirm, dropper_pending_quantidade_antes, dropper_pending_slot_item
    global dropper_waiting_ack, dropper_ack_watchdog_scheduled, sessao_lote_entregue, sessao_lote_confirmado, dropper_session_active
    if not dropper_session_active:
        return
    if not dropper_pending_confirm:
        return
    # Tenta confirmar por contador com uma janela um pouco maior (plataforma nova)
    try:
        time.sleep(0.8)
    except:
        pass
    quantidade_depois = dropper_pending_quantidade_antes
    try:
        quantidade_depois = script.GetItemsCount(ITEM_ALVO_ID, False)
    except:
        quantidade_depois = dropper_pending_quantidade_antes
    if quantidade_depois < dropper_pending_quantidade_antes:
        # Confirmado por contador: finalizar ciclo sem depender de ACK
        sessao_lote_entregue += 1
        _soltador_log('Soltado 1 (' + str(sessao_lote_entregue) + '/' + str(sessao_lote_confirmado) + ')')
        dropper_pending_confirm = False
        dropper_waiting_ack = False
        dropper_ack_watchdog_scheduled = False
        dropper_ack_wait_start_ms = 0
        try:
            script.CancelEvent('dropper_confirm_after_short_ack')
        except:
            pass
        try:
            script.RunEvent('dropper_drop_proximo', NEXT_DROP_AFTER_ACK_MS)
        except:
            pass
        return
    # Última tentativa leve: PZ check e drop em modo alternativo
    try:
        script.PZChecksForDrop(0)
    except:
        pass
    try:
        time.sleep(ALT_RETRY_SLEEP_1_MS / 1000.0)
    except:
        pass
    alt_res = ''
    try:
        _trace_fast('DropItem(slot=' + str(dropper_pending_slot_item) + ', modo=0) na confirmação tardia')
        alt_res = script.DropItem(dropper_pending_slot_item, 0)
    except:
        alt_res = ''
    try:
        time.sleep(ALT_RETRY_SLEEP_2_MS / 1000.0)
    except:
        pass
    try:
        script.PZChecksForDrop(1)
    except:
        pass
    if alt_res == 'ok' or alt_res == '[ok]':
        # Reconfirma por contador com mais 0.8s
        try:
            time.sleep(0.8)
        except:
            pass
        alt_depois = dropper_pending_quantidade_antes
        try:
            alt_depois = script.GetItemsCount(ITEM_ALVO_ID, False)
        except:
            alt_depois = dropper_pending_quantidade_antes
        if alt_depois < dropper_pending_quantidade_antes:
            sessao_lote_entregue += 1
            _soltador_log('Soltado 1 (' + str(sessao_lote_entregue) + '/' + str(sessao_lote_confirmado) + ')')
            dropper_pending_confirm = False
            dropper_waiting_ack = False
            dropper_ack_watchdog_scheduled = False
            dropper_ack_wait_start_ms = 0
            try:
                script.CancelEvent('dropper_confirm_after_short_ack')
            except:
                pass
            try:
                script.RunEvent('dropper_drop_proximo', NEXT_DROP_AFTER_ACK_MS)
            except:
                pass
            return
    # Não confirmado nem por contador: considera falha, libera novo ciclo
    dropper_pending_confirm = False
    dropper_waiting_ack = False
    dropper_ack_watchdog_scheduled = False
    dropper_ack_wait_start_ms = 0
    _soltador_log('Falha ao soltar. Tentando novamente...')
    try:
        script.RunEvent('dropper_drop_proximo', RETRY_NEXT_DROP_MS)
    except:
        pass

def _soltador_on_ack(qtd):
    # ACK não altera contagem. Contagem é feita apenas por verificação de mochila.
    # Mantemos a confirmação tardia agendada. Não liberamos novo drop aqui para evitar dupla cadência.
    try:
        debug_log('SOLTADOR', 'ACK recebido (ignorado para contagem). Aguardando verificação.', 'INFO')
    except:
        pass
    return

def _dropper_ack_watchdog():
    """
    Watchdog de ACK para o Soltador: enquanto aguardando ACK 1 do coletor,
    verifica a cada ~1s se o tempo de espera excedeu ACK_TIMEOUT_MS. Ao exceder,
    incrementa dropper_ack_timeouts. Ao atingir ACK_MAX_TIMEOUTS, finaliza a entrega
    parcial enviando CONCLUIDO com a quantidade já entregue, evitando travamento.
    """
    global dropper_waiting_ack, dropper_ack_timeouts, dropper_ack_wait_start_ms, dropper_ack_watchdog_scheduled, sessao_lote_entregue, dropper_session_active
    try:
        now_ms = int(time.time() * 1000)
    except:
        now_ms = 0
    # Se não estamos mais esperando, desarma watchdog
    if not dropper_waiting_ack:
        dropper_ack_watchdog_scheduled = False
        return
    # Verifica timeout
    if dropper_ack_wait_start_ms > 0 and (now_ms - dropper_ack_wait_start_ms) >= ACK_TIMEOUT_MS:
        dropper_ack_timeouts += 1
        dropper_ack_wait_start_ms = now_ms
        try:
            debug_log('SOLTADOR', 'ACK watchdog: timeout #' + str(dropper_ack_timeouts), 'WARNING')
        except:
            pass
        if dropper_ack_timeouts >= ACK_MAX_TIMEOUTS:
            # Finaliza parcial
            dropper_waiting_ack = False
            dropper_ack_watchdog_scheduled = False
            try:
                debug_log('SOLTADOR', 'ACK watchdog: máximo de timeouts. Enviando CONCLUIDO parcial e finalizando.', 'ERROR')
            except:
                pass
            _soltador_pm_coletor(montar_concluido(sessao_lote_entregue))
            # Após finalizar parcial por watchdog, reseta estado para aguardar novo pedido
            _dropper_reset_total()
            return
    # Reagenda próxima verificação
    try:
        script.RunEvent('dropper_ack_watchdog', 1000)
    except:
        pass


########################################
# Seção: Rechecagem de Menu (anti-trava)
########################################
def _dropper_wait_menu_recheck():
    """Rechecagem simples quando aguardando menu do depot após DepotGoNext.

    Se ainda estamos em modo de retirada (depotMode==2) e esperando menu,
    chama DepotGoNext() mais uma vez e reagenda nova verificação.
    """
    global dropper_waiting_menu, dropper_session_active, dropper_wait_menu_recheck_scheduled
    if not dropper_session_active:
        dropper_wait_menu_recheck_scheduled = False
        return
    # Se já não estamos mais esperando menu, encerra rechecagens
    if not dropper_waiting_menu:
        dropper_wait_menu_recheck_scheduled = False
        return
    # Confere contexto de depot e modo
    modo = 0
    try:
        modo = script.GetVar('depotMode')
    except:
        modo = 0
    if not script.IsInShop() or modo != 2:
        # Fora de contexto de retirada; para rechecagens
        dropper_wait_menu_recheck_scheduled = False
        return
    # Tenta um novo DepotGoNext leve e mantém aguardando menu
    try:
        debug_log('SOLTADOR', 'Recheck aguardando menu: chamando DepotGoNext()', 'DEBUG')
    except:
        pass
    try:
        script.DepotGoNext()
    except:
        pass
    # Reagenda próxima rechecagem
    try:
        script.RunEvent('dropper_wait_menu_recheck', WAITING_MENU_RECHECK_MS)
        dropper_wait_menu_recheck_scheduled = True
    except:
        pass

########################################
# Seção: Handler de AddItemToBackpack (retirada)
########################################
def dropper_on_add_item_to_backpack(slot, itemId):
    """Acelera o ciclo de retirada quando um item entra na mochila em modo retirada.

    Similar ao método simples do script clássico, reagenda o ciclo de retirada
    em curto prazo. Se a mochila ficar cheia, o fluxo normal cuidará da entrega
    parcial na próxima iteração.
    """
    modo = 0
    try:
        modo = script.GetVar('depotMode')
    except:
        modo = 0
    if modo != 2:
        return
    # Se estamos aguardando checagem de nome para este item, pausar storage para evitar processamento paralelo
    try:
        global name_check_pending, name_check_backpack_slot
        if name_check_pending and int(slot) == int(name_check_backpack_slot):
            try:
                debug_log('SOLTADOR', 'AddItemToBackpack(slot observado). Pausando storage e aguardando descrição.', 'DEBUG')
            except:
                pass
            try:
                script.PauseStorage(True)
            except:
                pass
            # Não reemite Look; aguarda onReceiveItemDescription* ou timeout
    except:
        pass
    # Reagenda o ciclo de retirada rapidamente
    try:
        script.RunEvent('dropper_retrieve_cycle', 300)
    except:
        pass

# Alias compatível com ambiente que chame diretamente o evento do cliente
def onReceiveAddItemToBackpack(slot, itemId):
    try:
        dropper_on_add_item_to_backpack(slot, itemId)
    except:
        pass

########################################
# Seção: Verificação de nome (callbacks de descrição)
########################################

def _dropper_name_check_timeout():
    """Timeout brando: se ainda pendente, reemite Look no slot para tentar receber a descrição."""
    global name_check_pending, name_check_backpack_slot, name_check_timeout_armed, name_check_attempts
    if not name_check_pending:
        name_check_timeout_armed = False
        return
    try:
        name_check_attempts = int(name_check_attempts) + 1
    except:
        name_check_attempts = 1
    # Se já tentamos 3 vezes olhar e não recebemos descrição, devolver por segurança
    if name_check_attempts >= 3:
        try:
            debug_log('SOLTADOR', 'Timeout nome (3 tentativas). Devolvendo item sem descrição para evitar travar.', 'WARNING')
        except:
            pass
        _dropper_return_rejected_item_fallback()
        return
    try:
        debug_log('SOLTADOR', 'Timeout nome: reemitindo LookAtBackPackSlot(' + str(name_check_backpack_slot) + ')', 'DEBUG')
        script.LookAtBackPackSlot(name_check_backpack_slot)
    except:
        pass
    try:
        script.RunEvent('dropper_name_check_timeout', 1500)
        name_check_timeout_armed = True
    except:
        pass

def onReceiveItemDescriptionBackpack(itemId, name, slot):
    """Valida o nome do item retirado. Se não bater com o esperado, devolve ao depósito
    no mesmo slot de origem e marca blacklist para não tentar de novo.
    """
    global name_check_pending, name_check_expected, name_check_depot_type, name_check_depot_id, name_check_depot_slot, name_check_backpack_slot, name_check_timeout_armed
    if not name_check_pending:
        return
    try:
        if int(slot) != int(name_check_backpack_slot):
            return
    except:
        # Se não conseguir comparar, tenta mesmo assim
        pass
    # Cancelar timeout em andamento
    try:
        script.CancelEvent('dropper_name_check_timeout')
    except:
        pass
    name_check_timeout_armed = False
    name_check_attempts = 0
    try:
        debug_log('SOLTADOR', 'Descrição mochila recebida: slot=' + str(slot) + ' itemId=' + str(itemId) + ' name="' + str(name) + '" esperado="' + str(name_check_expected) + '"', 'INFO')
    except:
        pass
    # Compara nome insensitive
    try:
        expected = str(name_check_expected).strip().lower()
    except:
        expected = None
    found_ok = False
    try:
        if expected is not None and str(name).strip().lower() == expected:
            found_ok = True
    except:
        found_ok = False
    if found_ok:
        # Nome confere: contabiliza retirada e segue ciclo
        name_check_pending = False
        try:
            dropper_retrieved_increment = 1
        except:
            dropper_retrieved_increment = 1
        try:
            # Usa variável global segura
            global dropper_retrieved
            dropper_retrieved += dropper_retrieved_increment
        except:
            pass
        try:
            debug_log('SOLTADOR', 'Nome confere: "' + str(name) + '". Slot mochila=' + str(slot) + ' origem dp slot=' + str(name_check_depot_slot), 'INFO')
        except:
            pass
        try:
            script.RunEvent('dropper_retrieve_cycle', 350)
        except:
            pass
        try:
            script.PauseStorage(False)
        except:
            pass
        return
    # Nome não confere: devolver item ao depósito no slot de origem
    try:
        debug_log('SOLTADOR', 'Nome divergente: esperado="' + str(name_check_expected) + '" obtido="' + str(name) + '". Devolvendo ao slot ' + str(name_check_depot_slot), 'WARNING')
    except:
        pass
    _dropper_return_rejected_item_fallback()
    return

def onReceiveItemDescription(itemId, name):
    """Fallback quando a plataforma não envia o evento *_Backpack. Tenta resolver pelo último slot olhado."""
    global name_check_pending, name_check_backpack_slot
    if not name_check_pending:
        return
    # Reutiliza a mesma lógica usando o último slot conhecido
    try:
        onReceiveItemDescriptionBackpack(itemId, name, name_check_backpack_slot)
    except:
        pass

def _dropper_return_rejected_item_fallback():
    """Tenta devolver o item rejeitado ao depósito e agenda novo ciclo."""
    global name_check_pending, name_check_depot_type, name_check_depot_id, name_check_depot_slot, name_check_backpack_slot
    # Garantir que estamos no depot antes de tentar devolver (reentrar se necessário)
    if not script.IsInShop():
        try:
            debug_log('SOLTADOR', 'Reentrando no depot para devolver item rejeitado', 'DEBUG')
        except:
            pass
        try:
            script.EnterShop()
        except:
            pass
    # Tentar devolver no slot de origem
    try:
        debug_log('SOLTADOR', 'StoreSlotInDepotSlot(from=' + str(name_check_backpack_slot) + ', to=' + str(name_check_depot_slot) + ')', 'DEBUG')
    except:
        pass
    try:
        returned = script.StoreSlotInDepotSlot(name_check_backpack_slot, name_check_depot_slot)
    except:
        returned = False
    if not returned:
        # fallback: qualquer slot livre
        try:
            debug_log('SOLTADOR', 'Fallback StoreSlotInDepot(from=' + str(name_check_backpack_slot) + ')', 'DEBUG')
        except:
            pass
        try:
            returned = script.StoreSlotInDepot(name_check_backpack_slot)
        except:
            returned = False
    if returned:
        try:
            debug_log('SOLTADOR', 'Item rejeitado devolvido com sucesso', 'INFO')
        except:
            pass
    else:
        try:
            debug_log('SOLTADOR', 'Falha ao devolver item rejeitado ao depot', 'ERROR')
        except:
            pass
    # Marca blacklist do slot de origem para não tentar novamente
    try:
        transfer_mark_rejected_slot(name_check_depot_type, name_check_depot_id, name_check_depot_slot)
    except:
        pass
    # Limpar pendência e seguir ciclo (se ainda no depot)
    name_check_pending = False
    try:
        delay_next = 500
        if not script.IsInShop():
            delay_next = 900
        script.RunEvent('dropper_retrieve_cycle', delay_next)
    except:
        pass
