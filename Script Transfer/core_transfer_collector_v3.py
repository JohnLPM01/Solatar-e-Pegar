# -*- coding: utf-8 -*-
########################################
# V3 - Lado Coletor (MVP)
########################################

import time
import sys

########################################
# Importa variáveis/funcões do estado e protocolo (mesmo namespace via execfile)
########################################

def _coletor_log(msg):
    try:
        script.StatusMessage('[COLETOR] ' + str(msg))
    except:
        pass
    try:
        debug_log('COLETOR', str(msg), 'INFO')
    except:
        pass

########################################
# Temporizadores e flags de navegação
########################################
MENU_RECHECK_MS = 1100  # Rechecagem de menu ao navegar entre páginas do depot
coletor_waiting_menu = False
coletor_wait_menu_recheck_scheduled = False
PM_SEND_DELAY_MS = 200  # Pequeno atraso antes de enviar PM para evitar colisões

# Navegação entre páginas do depot (prioriza SwitchDepotPage + fallback Next/Prev)
NAV_MAX_DIRECT_RETRIES = 3
nav_retry_count = 0

########################################
# Utilidades internas
########################################

def _as_int(value, default):
    """
    Converte um valor para int de forma segura.

    Args:
        value: Valor possivelmente string/None retornado por API do Mindee-BOT.
        default: Valor padrão se conversão falhar.

    Returns:
        int: Valor convertido ou default.
    """
    try:
        return int(value)
    except:
        return default

########################################
# Inicialização
########################################

def collector_on_activation():
    global sessao_estado, sessao_item_atual
    transfer_reset_state()
    sessao_item_atual = ITEM_ALVO_ID
    _coletor_log('Ativado. Item alvo: ' + str(sessao_item_atual) + ' | Página: ' + str(ITEM_PAGINA_COLETOR))
    _coletor_log('Tile de drop: ' + str(DROP_TILE_X) + ',' + str(DROP_TILE_Y) + ',' + str(DROP_TILE_Z))
    script.RunEvent('collector_iniciar_fluxo', 500)

########################################
# Fluxo principal do coletor
########################################

def _coletor_ir_para_tile_drop():
    try:
        script.GoToLocationEx(DROP_TILE_X, DROP_TILE_Y, DROP_TILE_Z)
    except:
        pass

def _coletor_abrir_depot():
    try:
        return script.EnterShop()
    except:
        return False

coletor_medindo_slots = False
coletor_depositando = False
deposito_tick_guard = False
coletor_next_steps_remaining = 0

def _coletor_contar_slots_livres():
    try:
        return script.GetFreeDepotSlotCount()
    except:
        return 0

def _coletor_info_slots_livres():
    """
    Retorna uma visão robusta de espaços livres na página atual do depot.

    Returns:
        tuple: (qtd_livre_aproximada, slot_livre_indice)
            - qtd_livre_aproximada: int >=0 quando conhecido; -1 quando desconhecido
            - slot_livre_indice: índice de um slot livre ou 255 se nenhum encontrado
    """
    qtd = -1
    livre_idx = 255
    try:
        qtd = script.GetFreeDepotSlotCount()
    except:
        qtd = -1
    try:
        livre_idx = script.GetFreeDepotSlot()
    except:
        livre_idx = 255
    try:
        debug_log('COLETOR', 'Info livres: count=' + str(qtd) + ' livre_idx=' + str(livre_idx), 'DEBUG')
    except:
        pass
    return (qtd, livre_idx)

def _coletor_fechar_depot():
    try:
        script.LeaveShop()
    except:
        pass
    # Sempre reposiciona no tile de drop após sair do depot
    try:
        script.GoToLocationEx(DROP_TILE_X, DROP_TILE_Y, DROP_TILE_Z)
    except:
        pass

def _collector_start_measuring_current_item():
    """Garante entrada no depot e ativa modo de medição para o item atual.

    - Entra no depot se ainda não estiver
    - Marca coletor_medindo_slots = True
    - Agenda rechecagem de menu e navegação via onDepotMenu
    """
    global coletor_medindo_slots
    # Entra no depot se necessário
    if not script.IsInShop():
        ok = False
        try:
            ok = _coletor_abrir_depot()
        except:
            ok = False
        if not ok:
            try:
                script.StatusMessage('[COLETOR] Falha ao abrir depot ao iniciar medição. Tentando novamente...')
            except:
                pass
            script.RunEvent('collector_iniciar_fluxo', 1200)
            return
    # Ativa medição e aguarda menus
    coletor_medindo_slots = True
    try:
        script.StatusMessage('[COLETOR] Aguardando menu do depot para medir slots da página ' + str(ITEM_PAGINA_COLETOR))
        debug_log('COLETOR', 'Iniciando medição para página ' + str(ITEM_PAGINA_COLETOR), 'INFO')
    except:
        pass
    try:
        _collector_nav_switch_to_target()
    except:
        pass

def _coletor_calcular_lote_a_pedir(slots_livres):
    if slots_livres <= 0:
        return 0
    # Aplica limite por página (cap) se configurado para o item ativo
    cap = None
    try:
        cap = ITEM_CAP_POR_PAGINA
    except:
        cap = None
    cap_restante = None
    if cap is not None:
        # Conta quantos itens do ITEM_ALVO_ID existem na página atual do depot
        try:
            itens_pagina = script.GetCurrentDepotItems()
        except:
            itens_pagina = None
        qtd_na_pagina = 0
        try:
            if itens_pagina is not None:
                for i in range(len(itens_pagina)):
                    if itens_pagina[i] == ITEM_ALVO_ID:
                        qtd_na_pagina += 1
        except:
            qtd_na_pagina = 0
        try:
            cap_restante = cap - qtd_na_pagina
            if cap_restante < 0:
                cap_restante = 0
        except:
            cap_restante = None
        # Log curto quando o cap for aplicado
        try:
            debug_log('COLETOR', 'Limite por página aplicado: ' + str(cap) + ' (restante: ' + str(cap_restante) + ')', 'INFO')
        except:
            pass
    if cap_restante is not None:
        return min(slots_livres, LOTE_MAX, cap_restante)
    return min(slots_livres, LOTE_MAX)

def _coletor_enviar_pm_soltador(texto):
    try:
        try:
            time.sleep(PM_SEND_DELAY_MS / 1000.0)
        except:
            pass
        script.SendPM(SOLTADOR_NOME, texto)
    except:
        pass

def _coletor_ack_pm():
    _coletor_enviar_pm_soltador(montar_ack())

def _coletor_tem_item_no_backpack():
    """
    Verifica rapidamente se existe ao menos um item alvo na mochila.
    """
    try:
        qtd = script.GetItemsCount(ITEM_ALVO_ID, False)
        if qtd is not None and int(qtd) > 0:
            return True
    except:
        pass
    return _coletor_buscar_slot_item_no_backpack() != 0

def collector_iniciar_fluxo():
    # 1) Vai para o tile de drop
    _coletor_ir_para_tile_drop()
    # 2) Entra no depot, vai à página e mede slots livres
    try:
        # Reinicia controle de rodada de medição por cap
        global medicao_round_item_ids
        medicao_round_item_ids = []
    except:
        pass
    _collector_start_measuring_current_item()

########################################
# Eventos do coletor
########################################

def collector_on_event(event_name):
    try:
        debug_log('COLETOR', 'on_event=' + str(event_name), 'DEBUG')
    except:
        pass
    if event_name == 'collector_iniciar_fluxo':
        collector_iniciar_fluxo()
    elif event_name == 'collector_timeout_ack':
        _coletor_timeout_ack_handler()
    elif event_name == 'collector_depositar' or event_name == 'collector_depositar_next':
        global deposito_tick_guard
        if deposito_tick_guard:
            try:
                debug_log('COLETOR', 'Tick ignorado (guard ativo) para ' + str(event_name), 'DEBUG')
            except:
                pass
            return
        deposito_tick_guard = True
        try:
            _coletor_executar_deposito()
        finally:
            # libera o guard logo após; o delay fica garantido pelos RunEvent
            deposito_tick_guard = False
    elif event_name == 'collector_wait_menu_recheck':
        _collector_wait_menu_recheck()
    elif event_name == 'collector_force_next':
        _collector_force_next_step()

def collector_on_add_item_to_depot(slot, itemId):
    """
    Evento disparado quando o depósito confirma que um item foi armazenado.
    Usamos isso como gatilho confiável para continuar o ciclo sem depender só de timers.
    """
    try:
        debug_log('COLETOR', 'on_add_item_to_depot slot=' + str(slot) + ' itemId=' + str(itemId), 'DEBUG')
    except:
        pass
    # Garantir que seguimos no modo de depósito
    global coletor_depositando
    coletor_depositando = True
    # Disparo imediato (com guard) + agendamento de reforço
    global deposito_tick_guard
    if not deposito_tick_guard:
        deposito_tick_guard = True
        try:
            _coletor_executar_deposito()
        finally:
            deposito_tick_guard = False
    # Reforço via evento
    try:
        script.StatusMessage('[COLETOR] on_add: agendando próximo depósito em 600ms')
    except:
        pass
    script.RunEvent('collector_depositar', 600)

def collector_on_pm(name, text):
    # Autoriza apenas o Soltador configurado
    try:
        if name != SOLTADOR_NOME:
            return
    except:
        pass
    # Recebe CONFIRMAR/CONCLUIDO/SEM_ESTOQUE do Soltador
    cmd = parse_mensagem(text)
    if cmd[0] == 'CONFIRMAR':
        _coletor_log('Soltador confirmou: ' + str(cmd[1]))
        try:
            debug_log('COLETOR', 'Recebido PM CONFIRMAR: ' + str(cmd[1]), 'INFO')
        except:
            pass
        _coletor_on_confirmar(cmd[1])
    elif cmd[0] == 'CONCLUIDO':
        _coletor_log('Lote concluído: ' + str(cmd[1]))
        try:
            debug_log('COLETOR', 'Recebido PM CONCLUIDO: ' + str(cmd[1]), 'INFO')
        except:
            pass
        _coletor_on_concluido(cmd[1])
    elif cmd[0] == 'SEM_ESTOQUE':
        _coletor_log('Soltador sem estoque. Entregue: ' + str(cmd[1]))
        try:
            debug_log('COLETOR', 'Recebido PM SEM_ESTOQUE: ' + str(cmd[1]), 'INFO')
        except:
            pass
        _coletor_on_sem_estoque(cmd[1])

def _coletor_on_sem_estoque(qtd_entregue):
    """
    Trata SEM_ESTOQUE: só abre o depot para depositar se houver algo na mochila.
    Caso contrário, finaliza o ciclo sem abrir depot desnecessariamente.
    """
    global sessao_estado, coletor_depositando
    if _coletor_tem_item_no_backpack():
        sessao_estado = ESTADO_DEPOSITANDO
        coletor_depositando = True
        if not _coletor_abrir_depot():
            _coletor_log('SEM_ESTOQUE: Falha ao abrir depot para depositar itens remanescentes. Tentando novamente...')
            script.RunEvent('collector_depositar', 1500)
            return
        _coletor_log('SEM_ESTOQUE: Depositando itens remanescentes do item ' + str(sessao_item_atual))
        # onReceiveDepotMenu cuidará do restante
    else:
        # Não há itens remanescentes na mochila. Marca este item como esgotado na rodada.
        try:
            global medicao_round_item_ids
        except:
            medicao_round_item_ids = []
        try:
            current_key = (ITEM_ALVO_ID, ITEM_PAGINA_COLETOR)
            if current_key not in medicao_round_item_ids:
                medicao_round_item_ids.append(current_key)
        except:
            pass
        # Verifica se todos os itens configurados foram marcados nesta rodada
        total_itens = 0
        try:
            nome = script.GetCharacterName()
            itens_cfg = transfer_get_items_for_character(nome)
            total_itens = 0 if itens_cfg is None else len(itens_cfg)
        except:
            total_itens = 0
        if total_itens > 0:
            try:
                if len(medicao_round_item_ids) >= total_itens:
                    _coletor_log('SEM_ESTOQUE: Todos os itens desta rodada sem estoque/capacidade. Finalizando rodada.')
                    sessao_estado = ESTADO_IDLE
                    return
            except:
                pass
        # Prossegue para o próximo item configurado e reinicia a medição.
        _coletor_log('SEM_ESTOQUE: Nenhum item na mochila. Alternando para próximo item e reiniciando fluxo.')
        try:
            transfer_advance_to_next_item()
        except:
            pass
        try:
            _collector_start_measuring_current_item()
        except:
            pass

def _coletor_on_concluido(qtd_entregue):
    # Após concluir lote, deposita itens coletados na página
    global sessao_estado, coletor_depositando
    sessao_estado = ESTADO_DEPOSITANDO
    coletor_depositando = True
    if not _coletor_abrir_depot():
        _coletor_log('Falha ao abrir depot para depositar. Reposicionando no tile e tentando novamente...')
        try:
            _coletor_ir_para_tile_drop()
        except:
            pass
        script.RunEvent('collector_depositar', 1500)
        return
    _coletor_log('Abrindo depot para depositar itens do item ' + str(sessao_item_atual))
    # onReceiveDepotMenu cuidará de navegar e executar depósito

def _coletor_on_confirmar(qtd):
    # Inicia ciclo de coleta 1-a-1
    global sessao_estado, sessao_lote_confirmado
    if sessao_estado != ESTADO_PREPARANDO_LOTE:
        return
    sessao_lote_confirmado = max(0, int(qtd))
    if sessao_lote_confirmado <= 0:
        return
    _coletor_log('Iniciando sincronização 1-a-1 para ' + str(sessao_lote_confirmado) + ' itens')
    global ack_timeouts_consecutivos
    ack_timeouts_consecutivos = 0
    sessao_estado = ESTADO_ENTREGANDO
    # Aguarda drops do Soltador (eventos de chão)
    script.RunEvent('collector_timeout_ack', int(ACK_TIMEOUT_S * 1000))

def _coletor_timeout_ack_handler():
    global ack_timeouts_consecutivos
    if sessao_estado != ESTADO_ENTREGANDO:
        return
    ack_timeouts_consecutivos += 1
    if ack_timeouts_consecutivos >= ACK_MAX_TIMEOUTS:
        _coletor_log('ACK timeout x' + str(ack_timeouts_consecutivos) + ' - abortando lote parcial')
        try:
            debug_log('COLETOR', 'ACK timeout limite atingido', 'WARNING')
        except:
            pass
        # Finaliza parcial do lote; Soltador enviará CONCLUIDO parcial e reiniciaremos
        return
    _coletor_log('ACK timeout (' + str(ack_timeouts_consecutivos) + '/' + str(ACK_MAX_TIMEOUTS) + ')')
    script.RunEvent('collector_timeout_ack', int(ACK_TIMEOUT_S * 1000))

def collector_on_item_ground(x, y, z, itemId):
    if sessao_estado != ESTADO_ENTREGANDO:
        return
    if itemId != sessao_item_atual:
        _coletor_log('Item inesperado no chão. Ignorando.')
        return
    # Move e coleta
    try:
        script.GoToLocationEx(x, y, z)
    except:
        pass
    resultado = ''
    try:
        resultado = script.LootItem()
    except:
        resultado = ''
    if resultado == '[ok]':
        global sessao_lote_entregue
        sessao_lote_entregue += 1
        _coletor_log('Coletado 1 (' + str(sessao_lote_entregue) + '/' + str(sessao_lote_confirmado) + ')')
        _coletor_ack_pm()
        if sessao_lote_entregue >= sessao_lote_confirmado:
            # Lote terminado do ponto de vista do coletor; aguardará CONCLUIDO do Soltador
            pass
        else:
            # Reagendar watchdog de ACK para o próximo item
            script.RunEvent('collector_timeout_ack', int(ACK_TIMEOUT_S * 1000))
    else:
        _coletor_log('Falha ao coletar item do chão: ' + str(resultado))

def collector_on_item_removed(x, y, z):
    # Não precisamos agir aqui; a confirmação é via PM ACK/CONCLUIDO
    pass

def collector_on_depot_menu(depot_name, depot_id, depot_type, slots):
    global coletor_medindo_slots
    global coletor_depositando
    # Qualquer menu recebido encerra estado de aguardo
    try:
        _collector_clear_waiting_menu()
    except:
        pass
    # Modo medição de slots para pedir lote
    if coletor_medindo_slots:
        try:
            debug_log('COLETOR', 'onDepotMenu medir: tipo=' + str(depot_type) + ' id=' + str(depot_id) + ' slots=' + str(slots), 'INFO')
        except:
            pass
        depot_type_i = _as_int(depot_type, -1)
        depot_id_i = _as_int(depot_id, -1)
        if depot_type_i != 2 or depot_id_i != ITEM_PAGINA_COLETOR:
            try:
                script.StatusMessage('[COLETOR] Medir: navegando via SwitchDepotPage(' + str(ITEM_PAGINA_COLETOR) + ')')
                debug_log('COLETOR', 'Medir: tipo/id fora. SwitchDepotPage primeiro; fallback Next/Prev', 'INFO')
            except:
                pass
            _collector_nav_switch_to_target()
            return
        livres = _coletor_contar_slots_livres()
        _coletor_log('Página ' + str(ITEM_PAGINA_COLETOR) + ' com ' + str(livres) + ' slots livres')
        coletor_medindo_slots = False
        # Calcula o lote AINDA dentro do depot (evita analisar fora do dp)
        lote = _coletor_calcular_lote_a_pedir(livres)
        if lote <= 0:
            # Proteção contra loop: se todos os itens do round já foram avaliados como cap 0, encerra ciclo
            try:
                global medicao_round_item_ids
            except:
                medicao_round_item_ids = []
            try:
                current_key = (ITEM_ALVO_ID, ITEM_PAGINA_COLETOR)
                if current_key not in medicao_round_item_ids:
                    medicao_round_item_ids.append(current_key)
            except:
                pass
            try:
                nome = script.GetCharacterName()
            except:
                nome = ''
            itens_cfg = transfer_get_items_for_character(nome)
            total_itens = 0 if itens_cfg is None else len(itens_cfg)
            if total_itens > 0 and len(medicao_round_item_ids) >= total_itens:
                _coletor_log('Nenhum item com cap restante nesta página. Finalizando rodada sem pedir lote.')
                try:
                    debug_log('COLETOR', 'Rodada completa: todos itens sem cap/estoque. Encerrando.', 'INFO')
                except:
                    pass
                coletor_medindo_slots = False
                # Opcional: resetar a marcação para uma nova rodada futura
                try:
                    medicao_round_item_ids = []
                except:
                    pass
                return
            # Avança automaticamente para o próximo item e reinicia o fluxo de medição
            try:
                transfer_advance_to_next_item()
                debug_log('COLETOR', 'Página cheia/cap=0. Avançando para o próximo item e navegando até a página alvo...', 'INFO')
            except:
                pass
            _collector_start_measuring_current_item()
            return
        _coletor_log('Pedindo lote de ' + str(lote) + ' itens')
        global sessao_estado, sessao_lote_pedido, sessao_lote_confirmado, sessao_lote_entregue
        sessao_estado = ESTADO_PREPARANDO_LOTE
        sessao_lote_pedido = lote
        sessao_lote_confirmado = 0
        sessao_lote_entregue = 0
        # Fecha o depot SOMENTE após definir o pedido
        _coletor_fechar_depot()
        _coletor_enviar_pm_soltador(montar_pedir(sessao_item_atual, lote))
        return
    # Modo depósito: navegar até a página e armazenar
    if coletor_depositando:
        try:
            debug_log('COLETOR', 'onDepotMenu depositar: tipo=' + str(depot_type) + ' id=' + str(depot_id) + ' slots=' + str(slots), 'INFO')
        except:
            pass
        depot_type_i = _as_int(depot_type, -1)
        depot_id_i = _as_int(depot_id, -1)
        if depot_type_i != 2 or depot_id_i != ITEM_PAGINA_COLETOR:
            try:
                script.StatusMessage('[COLETOR] Depositar: navegando via SwitchDepotPage(' + str(ITEM_PAGINA_COLETOR) + ')')
                debug_log('COLETOR', 'Depositar: tipo/id fora. SwitchDepotPage primeiro; fallback Next/Prev', 'INFO')
            except:
                pass
            _collector_nav_switch_to_target()
            return
        # Estamos na página correta: iniciar depósito (imediato + agendado)
        try:
            script.StatusMessage('[COLETOR] Página correta alcançada (' + str(depot_id) + '). Iniciando depósito...')
            script.StatusMessage('[COLETOR] Agendando collector_depositar em ' + str(STABILIZE_MS) + 'ms')
        except:
            pass
        try:
            _coletor_executar_deposito()
        except:
            pass
        script.RunEvent('collector_depositar', STABILIZE_MS)

def _coletor_buscar_slot_item_no_backpack():
    """
    Retorna o primeiro slot (1-based) do item alvo na mochila.
    Implementa duas estratégias:
      1) script.GetItemSlot(ITEM_ALVO_ID)
      2) Varredura de script.GetBackpackItems()
    """
    # 1) Tentativa via API direta
    try:
        slot = script.GetItemSlot(ITEM_ALVO_ID)
        if slot is not None and int(slot) > 0:
            return int(slot)
    except:
        pass
    # 2) Varredura dos itens
    try:
        items = script.GetBackpackItems()
        if items is None:
            return 0
        for i in range(len(items)):
            if items[i] == ITEM_ALVO_ID:
                return i + 1
    except:
        pass
    return 0

def _coletor_executar_deposito():
    # Pré-condições
    global coletor_depositando, sessao_estado
    try:
        debug_log('COLETOR', 'Executar depósito: inicio. InShop=' + str(script.IsInShop()), 'DEBUG')
        script.StatusMessage('[COLETOR] Executar depósito: InShop=' + str(script.IsInShop()))
    except:
        pass
    if not script.IsInShop():
        # Reposiciona e reabre caso tenha fechado
        try:
            _coletor_ir_para_tile_drop()
        except:
            pass
        ok = False
        try:
            ok = _coletor_abrir_depot()
        except:
            ok = False
        try:
            debug_log('COLETOR', 'Reabrir depot após reposicionamento -> ' + str(ok), 'DEBUG')
        except:
            pass
        if not ok:
            _coletor_log('Ainda não foi possível abrir o depot para depositar. Reagendando...')
            script.RunEvent('collector_depositar', 1500)
            return
        try:
            _collector_mark_waiting_menu()
        except:
            pass
        script.RunEvent('collector_depositar', 300)
        return
    # Garante que está na página correta
    try:
        tipo = _as_int(script.GetVar('depot_type'), -1)
        pagina = _as_int(script.GetVar('depot_id'), -1)
    except:
        tipo = 0
        pagina = 0
    try:
        debug_log('COLETOR', 'Contexto depot: tipo=' + str(tipo) + ' id=' + str(pagina), 'DEBUG')
        script.StatusMessage('[COLETOR] Contexto: tipo=' + str(tipo) + ' id=' + str(pagina))
    except:
        pass
    if tipo != 2 or pagina != ITEM_PAGINA_COLETOR:
        try:
            script.StatusMessage('[COLETOR] Ajuste de página: SwitchDepotPage(' + str(ITEM_PAGINA_COLETOR) + ')')
            debug_log('COLETOR', 'Ajuste de página: SwitchDepotPage antes de Next/Prev', 'DEBUG')
        except:
            pass
        _collector_nav_switch_to_target()
        script.RunEvent('collector_depositar', 300)
        return
    # Busca próximo slot do item
    # Resguardo: aguarda estabilização do inventário após entrada no depot
    time.sleep(0.6)
    try:
        items_dbg = script.GetBackpackItems()
        debug_log('COLETOR', 'Backpack slots lidos: ' + str(0 if items_dbg is None else len(items_dbg)), 'DEBUG')
        script.StatusMessage('[COLETOR] Backpack lido: ' + str(0 if items_dbg is None else len(items_dbg)) + ' slots')
    except:
        pass
    slot = _coletor_buscar_slot_item_no_backpack()
    # Garantir que não tentaremos o mesmo slot sem revalidar inventário
    # (se necessário, o delay acima e um novo ciclo corrigirão a seleção)
    try:
        script.StatusMessage('[COLETOR] Próximo slot do item alvo: ' + str(slot))
        debug_log('COLETOR', 'Slot candidato (1-based)=' + str(slot), 'DEBUG')
    except:
        pass
    if slot == 0:
        # Concluiu depósito do que havia na mochila. Aproveita que já está na página para calcular o próximo lote.
        livres_pos_deposito = _coletor_contar_slots_livres()
        try:
            debug_log('COLETOR', 'Depósito concluído. Slots livres pós-depósito: ' + str(livres_pos_deposito), 'DEBUG')
        except:
            pass
        proximo_lote = _coletor_calcular_lote_a_pedir(livres_pos_deposito)
        coletor_depositando = False
        if proximo_lote > 0:
            # Já sabemos quanto pedir. Sai do depot e solicita novo lote diretamente.
            try:
                debug_log('COLETOR', 'Solicitando novo lote direto: ' + str(proximo_lote), 'INFO')
            except:
                pass
            global sessao_estado, sessao_lote_pedido, sessao_lote_confirmado, sessao_lote_entregue
            sessao_estado = ESTADO_PREPARANDO_LOTE
            sessao_lote_pedido = proximo_lote
            sessao_lote_confirmado = 0
            sessao_lote_entregue = 0
            _coletor_fechar_depot()
            _coletor_enviar_pm_soltador(montar_pedir(sessao_item_atual, proximo_lote))
            return
        # Sem espaço suficiente para pedir novo lote agora:
        # marca este item na rodada e avança automaticamente para o próximo item configurado
        try:
            global medicao_round_item_ids
        except:
            medicao_round_item_ids = []
        try:
            current_key = (ITEM_ALVO_ID, ITEM_PAGINA_COLETOR)
            if current_key not in medicao_round_item_ids:
                medicao_round_item_ids.append(current_key)
        except:
            pass
        try:
            transfer_advance_to_next_item()
            debug_log('COLETOR', 'Sem espaço para novo lote. Avançando para o próximo item e reiniciando fluxo.', 'INFO')
        except:
            pass
        # Sai do modo de depósito e inicia medição do novo item ainda dentro do depot
        coletor_depositando = False
        _collector_start_measuring_current_item()
        return
    # Checa slots livres (contagem e tentativa de localizar um índice livre)
    livres = _coletor_contar_slots_livres()
    livre_hint = 255
    try:
        livre_hint = script.GetFreeDepotSlot()
    except:
        livre_hint = 255
    try:
        debug_log('COLETOR', 'Slots livres count=' + str(livres) + ' livre_hint=' + str(livre_hint), 'DEBUG')
        script.StatusMessage('[COLETOR] Livres: ' + str(livres) + ' | hint=' + str(livre_hint))
    except:
        pass
    if (livres == 0) and (livre_hint == 255):
        # Página sem espaço. Tenta o próximo item; se não houver mais itens, finaliza coleta de itens.
        proximo_slot_check = _coletor_buscar_slot_item_no_backpack()
        if proximo_slot_check == 0:
            # Marca este item e avança automaticamente para o próximo item, CONTINUANDO dentro do depot
            try:
                global medicao_round_item_ids
            except:
                medicao_round_item_ids = []
            try:
                current_key = (ITEM_ALVO_ID, ITEM_PAGINA_COLETOR)
                if current_key not in medicao_round_item_ids:
                    medicao_round_item_ids.append(current_key)
            except:
                pass
            _coletor_log('Mochila vazia para este item. Alternando para próximo item e reiniciando...')
            try:
                transfer_advance_to_next_item()
            except:
                pass
            coletor_depositando = False
            _collector_start_measuring_current_item()
            return
        _coletor_log('Página cheia. Tentando próximo item da mochila...')
        script.RunEvent('collector_depositar', 1200)
        return
    # Armazena um item (tenta método primário; se falhar, usa fallbacks focados no DEPOT atual)
    # Revalida o slot antes de tentar
    try:
        slot_item_id = script.GetItemInSlot(slot)
        if slot_item_id != ITEM_ALVO_ID:
            slot = _coletor_buscar_slot_item_no_backpack()
    except:
        pass
    ok = False
    try:
        debug_log('COLETOR', 'Tentando StoreSlotInDepot(slot=' + str(slot) + ')', 'DEBUG')
        script.StatusMessage('[COLETOR] Tentando armazenar do slot ' + str(slot) + ' (StoreSlotInDepot)')
        ok = script.StoreSlotInDepot(slot)
    except:
        ok = False
    if ok:
        _coletor_log('Item armazenado do slot ' + str(slot))
        try:
            debug_log('COLETOR', 'Armazenado slot ' + str(slot), 'INFO')
        except:
            pass
        # Não reagendar aqui; aguardaremos o onReceiveAddItemToDepot do client
    else:
        # Verifica se o menu ainda está estável na página certa antes do fallback
        try:
            tipo = _as_int(script.GetVar('depot_type'), -1)
            pagina = _as_int(script.GetVar('depot_id'), -1)
        except:
            tipo = -1
            pagina = -1
        if tipo != 2 or pagina != ITEM_PAGINA_COLETOR:
            try:
                debug_log('COLETOR', 'Contexto mudou durante depósito (tipo/id). Reagendando...', 'WARNING')
                script.StatusMessage('[COLETOR] Contexto mudou durante depósito. Reagendando...')
            except:
                pass
            script.RunEvent('collector_depositar', 500)
            return
        # Fallback 1: tentar StoreInDepot por itemId (mais resiliente)
        id_ok = False
        try:
            debug_log('COLETOR', 'Tentando StoreInDepot(itemId=' + str(ITEM_ALVO_ID) + ')', 'DEBUG')
            script.StatusMessage('[COLETOR] Tentando armazenar por itemId ' + str(ITEM_ALVO_ID))
            id_ok = script.StoreInDepot(ITEM_ALVO_ID)
        except:
            id_ok = False
        if id_ok:
            _coletor_log('Item armazenado (por itemId)')
            script.RunEvent('collector_depositar', 700)
            return
        # Fallback 2: encontrar slot livre explícito na página e usar StoreSlotInDepotSlot
        livre = livre_hint
        if livre == 255:
            try:
                livre = script.GetFreeDepotSlot()
            except:
                livre = 255
        try:
            debug_log('COLETOR', 'Fallback2: livre selecionado=' + str(livre), 'DEBUG')
            script.StatusMessage('[COLETOR] Fallback2: livre=' + str(livre))
        except:
            pass
        if livre != 255:
            alt_ok = False
            try:
                debug_log('COLETOR', 'Tentando StoreSlotInDepotSlot(slot=' + str(slot) + ', livre=' + str(livre) + ')', 'DEBUG')
                script.StatusMessage('[COLETOR] Tentando armazenar no slot livre ' + str(livre) + ' a partir do slot ' + str(slot))
                alt_ok = script.StoreSlotInDepotSlot(slot, livre)
            except:
                alt_ok = False
            if alt_ok:
                _coletor_log('Item armazenado (slot ' + str(livre) + ') do slot ' + str(slot))
                try:
                    debug_log('COLETOR', 'Armazenado em slot ' + str(livre) + ' a partir do slot ' + str(slot), 'INFO')
                except:
                    pass
                script.RunEvent('collector_depositar', 700)
                return
        _coletor_log('Falha ao armazenar do slot ' + str(slot) + '. Tentando novamente (recovery leve)...')
        try:
            debug_log('COLETOR', 'Fallbacks falharam para slot ' + str(slot) + '. Recovery leve acionado.', 'WARNING')
        except:
            pass
        # Recovery leve: fecha menus e aguarda um pequeno tempo antes do próximo ciclo
        try:
            script.ForceCloseMenus()
        except:
            pass
        script.RunEvent('collector_depositar', 1200)


########################################
# Rechecagem simples de menu (anti-trava)
########################################
def _collector_mark_waiting_menu():
    global coletor_waiting_menu, coletor_wait_menu_recheck_scheduled
    coletor_waiting_menu = True
    try:
        if not coletor_wait_menu_recheck_scheduled:
            script.RunEvent('collector_wait_menu_recheck', MENU_RECHECK_MS)
            coletor_wait_menu_recheck_scheduled = True
    except:
        pass

def _collector_clear_waiting_menu():
    global coletor_waiting_menu, coletor_wait_menu_recheck_scheduled
    coletor_waiting_menu = False
    coletor_wait_menu_recheck_scheduled = False

def _collector_wait_menu_recheck():
    global coletor_waiting_menu, coletor_wait_menu_recheck_scheduled, nav_retry_count
    if not coletor_waiting_menu:
        coletor_wait_menu_recheck_scheduled = False
        nav_retry_count = 0
        return
    # Apenas rechecagem se ainda no depot
    if not script.IsInShop():
        coletor_wait_menu_recheck_scheduled = False
        nav_retry_count = 0
        return
    # Estratégia: tentar SwitchDepotPage algumas vezes; depois fallback Next/Prev
    try:
        cur_id = int(script.GetVar('depot_id'))
    except:
        cur_id = -1
    try:
        cur_type = int(script.GetVar('depot_type'))
    except:
        cur_type = -1
    if nav_retry_count < NAV_MAX_DIRECT_RETRIES:
        try:
            debug_log('COLETOR', 'Recheck: SwitchDepotPage(' + str(ITEM_PAGINA_COLETOR) + ') tentativa #' + str(nav_retry_count + 1), 'DEBUG')
        except:
            pass
        try:
            script.SwitchDepotPage(ITEM_PAGINA_COLETOR)
        except:
            pass
        nav_retry_count += 1
    else:
        # Heurística simples de direção
        try:
            if cur_id == -1 or cur_id < ITEM_PAGINA_COLETOR:
                debug_log('COLETOR', 'Recheck fallback: DepotGoNext()', 'DEBUG')
                script.DepotGoNext()
            else:
                debug_log('COLETOR', 'Recheck fallback: DepotGoPrev()', 'DEBUG')
                script.DepotGoPrev()
        except:
            try:
                script.DepotGoNext()
            except:
                pass
    # Reagenda
    try:
        script.RunEvent('collector_wait_menu_recheck', MENU_RECHECK_MS)
        coletor_wait_menu_recheck_scheduled = True
    except:
        pass

def _collector_nav_switch_to_target():
    """Navega para a página alvo priorizando SwitchDepotPage com fallback.

    - Marca estado de espera por menu
    - Tenta SwitchDepotPage(ITEM_PAGINA_COLETOR)
    - Rechecagem periódica: repetirá Switch N vezes; depois usa Next/Prev
    """
    global nav_retry_count
    nav_retry_count = 0
    try:
        script.StatusMessage('[NAV] Tentando SwitchDepotPage(' + str(ITEM_PAGINA_COLETOR) + ')')
        debug_log('COLETOR', 'NAV: SwitchDepotPage inicial para página alvo', 'INFO')
    except:
        pass
    try:
        script.SwitchDepotPage(ITEM_PAGINA_COLETOR)
    except:
        pass
    _collector_mark_waiting_menu()

def _collector_force_next_step():
    """Força um único DepotGoNext quando estamos medindo, para seguir o ciclo 2->0->1->2."""
    if not coletor_medindo_slots:
        return
    try:
        script.DepotGoNext()
    except:
        pass