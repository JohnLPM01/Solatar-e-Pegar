# -*- coding: utf-8 -*-
########################################
# V3 - Sistema de Debug e Cache (migrado do v2, sem uso de os)
########################################

import time
import sys

########################################
# Configurações do Sistema de Debug Otimizado
########################################
DEBUG_ENABLED = True
# Caminho ajustado para o projeto atual (Transfer)
DEBUG_FILE_PATH = 'c:\\Users\\Jonatha Lopes\\Documents\\Tibiame\\Tibime New\\Utilidades\\Pega e Soltar\\logs\\transfer_debug.log'
DEBUG_LEVEL = 'SMART'  # ALL, SMART, INFO, WARNING, ERROR
MAX_LOG_SIZE = 500000  # 500KB em bytes
AUTO_CLEAR_ON_START = True

# Configurações de otimização
DEBUG_SMART_MODE = True
DEBUG_LOCATION_THROTTLE = 10.0
DEBUG_STORAGE_THROTTLE = 2.0
DEBUG_MAX_REPEATED_LOGS = 3

# Controles internos de throttling
_last_location_log = 0
_last_storage_log = 0
_repeated_log_count = {}
_last_log_content = ''

########################################
# Cache de Validação de Itens (compartilhado com núcleo)
########################################
_item_validation_cache = {}
_cache_timestamp = {}
CACHE_TTL = 30.0

_empty_slots_cache = set()
_last_empty_slots_check = 0
EMPTY_SLOTS_CHECK_INTERVAL = 5.0

_advanced_throttle = {}
ADVANCED_THROTTLE_INTERVAL = 10.0

########################################
# Funções do Sistema de Debug
########################################
def inicializar_debug(script_name='Script Desconhecido'):
    try:
        if AUTO_CLEAR_ON_START:
            limpar_log_debug()
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        cabecalho = '=' * 60 + '\n'
        cabecalho += 'DEBUG LOG INICIADO - ' + script_name + '\n'
        cabecalho += 'Timestamp: ' + timestamp + '\n'
        cabecalho += 'Sistema de Debug Ativo\n'
        cabecalho += '=' * 60 + '\n\n'
        f = open(DEBUG_FILE_PATH, 'a')
        try:
            f.write(cabecalho)
        finally:
            f.close()
        debug_log('SISTEMA', 'Debug inicializado para: ' + script_name)
        return True
    except Exception as e:
        try:
            script.StatusMessage('ERRO ao inicializar debug: ' + str(e))
        except:
            pass
        return False

def deve_logar_nivel(nivel):
    if DEBUG_LEVEL == 'ALL':
        return True
    elif DEBUG_LEVEL == 'SMART':
        return nivel in ['WARNING', 'ERROR'] or DEBUG_SMART_MODE
    elif DEBUG_LEVEL == 'WARNING' and nivel in ['WARNING', 'ERROR']:
        return True
    elif DEBUG_LEVEL == 'ERROR' and nivel == 'ERROR':
        return True
    return False

def verificar_tamanho_log():
    # Sem uso de os: usa file.tell() para obter tamanho e truncar quando necessário
    try:
        f = open(DEBUG_FILE_PATH, 'a+')
        try:
            f.seek(0, 2)  # fim
            size = f.tell()
        finally:
            f.close()
        if size > MAX_LOG_SIZE:
            g = open(DEBUG_FILE_PATH, 'w')
            try:
                g.write('=== LOG REINICIADO - LIMITE EXCEDIDO ===\n')
            finally:
                g.close()
            # registra pequeno aviso após truncar
            h = open(DEBUG_FILE_PATH, 'a')
            try:
                h.write('[INFO] [SISTEMA] Log foi truncado por tamanho.\n')
            finally:
                h.close()
    except:
        pass

def debug_log(categoria, mensagem, nivel='INFO'):
    global _last_log_content, _repeated_log_count
    if not DEBUG_ENABLED:
        return
    if not deve_logar_nivel(nivel):
        return

    if DEBUG_SMART_MODE and nivel == 'INFO':
        log_key = categoria + ':' + mensagem
        current_time = time.time()
        if categoria == 'FUNCAO' and 'onChangeLocation_Modulo' in mensagem:
            global _last_location_log
            if current_time - _last_location_log < DEBUG_LOCATION_THROTTLE:
                return
            _last_location_log = current_time
        if categoria in ['STORAGE', 'VARIAVEL'] and ('slot' in mensagem.lower() or 'item=0' in mensagem.lower() or 'nada para' in mensagem.lower()):
            global _last_storage_log
            if current_time - _last_storage_log < DEBUG_STORAGE_THROTTLE:
                return
            _last_storage_log = current_time
        if log_key in _repeated_log_count:
            _repeated_log_count[log_key] += 1
            if _repeated_log_count[log_key] > DEBUG_MAX_REPEATED_LOGS:
                return
        else:
            _repeated_log_count[log_key] = 1

    try:
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        linha_log = '[{0}] [{1}] {2}: {3}\n'.format(timestamp, nivel, categoria, mensagem)
        verificar_tamanho_log()
        f = open(DEBUG_FILE_PATH, 'a')
        try:
            f.write(linha_log)
        finally:
            f.close()
        try:
            if nivel == 'ERROR':
                script.StatusMessage('[DEBUG-ERROR] ' + categoria + ': ' + mensagem)
            elif nivel == 'WARNING':
                script.StatusMessage('[DEBUG-WARN] ' + categoria + ': ' + mensagem)
        except:
            pass
    except Exception as e:
        try:
            script.StatusMessage('ERRO no debug_log: ' + str(e))
        except:
            pass

def debug_funcao_inicio(nome_funcao, parametros=''):
    mensagem = 'INICIO - ' + nome_funcao
    if parametros:
        mensagem += ' | Params: ' + str(parametros)
    debug_log('FUNCAO', mensagem)

def debug_funcao_fim(nome_funcao, resultado=''):
    mensagem = 'FIM - ' + nome_funcao
    if resultado:
        mensagem += ' | Resultado: ' + str(resultado)
    debug_log('FUNCAO', mensagem)

def debug_evento(evento, detalhes=''):
    mensagem = evento
    if detalhes:
        mensagem += ' | ' + str(detalhes)
    debug_log('EVENTO', mensagem)

def debug_erro(funcao, erro, detalhes=''):
    mensagem = 'ERRO em ' + funcao + ': ' + str(erro)
    if detalhes:
        mensagem += ' | Detalhes: ' + str(detalhes)
    debug_log('ERRO', mensagem, 'ERROR')

def debug_variavel(nome_var, valor, contexto=''):
    mensagem = nome_var + ' = ' + str(valor)
    if contexto:
        mensagem = contexto + ' | ' + mensagem
    debug_log('VARIAVEL', mensagem)

def debug_condicional(condicao, resultado, contexto=''):
    resultado_str = 'TRUE' if resultado else 'FALSE'
    mensagem = condicao + ' = ' + resultado_str
    if contexto:
        mensagem = contexto + ' | ' + mensagem
    debug_log('CONDICIONAL', mensagem)

def debug_performance_inicio(operacao):
    inicio = time.time()
    debug_log('PERFORMANCE', 'INICIO medição: ' + operacao)
    return inicio

def debug_performance_fim(operacao, inicio):
    fim = time.time()
    duracao = fim - inicio
    debug_log('PERFORMANCE', 'FIM medição: ' + operacao + ' | Duração: {:.3f}s'.format(duracao))

def limpar_log_debug():
    try:
        f = open(DEBUG_FILE_PATH, 'w')
        try:
            f.write('')
        finally:
            f.close()
        return True
    except Exception as e:
        try:
            script.StatusMessage('ERRO ao limpar log: ' + str(e))
        except:
            pass
        return False

def toggle_debug(ativar=None):
    global DEBUG_ENABLED
    if ativar is None:
        DEBUG_ENABLED = not DEBUG_ENABLED
    else:
        DEBUG_ENABLED = ativar
    status = 'ATIVADO' if DEBUG_ENABLED else 'DESATIVADO'
    try:
        script.StatusMessage('Sistema de Debug: ' + status)
    except:
        pass
    if DEBUG_ENABLED:
        debug_log('SISTEMA', 'Debug ativado manualmente')

def reset_debug_throttling():
    global _last_location_log, _last_storage_log, _repeated_log_count
    _last_location_log = 0
    _last_storage_log = 0
    _repeated_log_count.clear()
    debug_log('SISTEMA', 'Contadores de throttling resetados')

def set_debug_level(nivel):
    global DEBUG_LEVEL
    niveis_validos = ['ALL', 'SMART', 'INFO', 'WARNING', 'ERROR']
    if nivel in niveis_validos:
        DEBUG_LEVEL = nivel
        debug_log('SISTEMA', 'Nível de debug alterado para: ' + nivel)
        try:
            script.StatusMessage('Debug level: ' + nivel)
        except:
            pass
        return True
    else:
        debug_erro('set_debug_level', 'Nível inválido', 'Níveis válidos: ' + str(niveis_validos))
        return False

def get_debug_stats():
    stats = {
        'enabled': DEBUG_ENABLED,
        'level': DEBUG_LEVEL,
        'smart_mode': DEBUG_SMART_MODE,
        'repeated_logs': len(_repeated_log_count),
        'location_throttle': DEBUG_LOCATION_THROTTLE,
        'storage_throttle': DEBUG_STORAGE_THROTTLE
    }
    debug_log('SISTEMA', 'Stats: ' + str(stats))
    return stats

def debug_quick_info():
    try:
        info = 'Debug: {0} | Logs repetidos: {1} | Throttling ativo'.format(DEBUG_LEVEL, len(_repeated_log_count))
        script.StatusMessage(info)
        debug_log('INFO', info)
    except:
        pass

def debug_enable_verbose():
    set_debug_level('ALL')
    script.StatusMessage('Debug verboso ativado!')

def debug_enable_smart():
    global DEBUG_SMART_MODE
    DEBUG_SMART_MODE = True
    set_debug_level('SMART')
    script.StatusMessage('Debug inteligente ativado!')

def debug_disable_smart():
    global DEBUG_SMART_MODE
    DEBUG_SMART_MODE = False
    set_debug_level('SMART')
    script.StatusMessage('Debug inteligente desativado!')

def debug_disable():
    global DEBUG_ENABLED
    DEBUG_ENABLED = False
    script.StatusMessage('Debug desativado!')

def debug_clear_log():
    if limpar_log_debug():
        reset_debug_throttling()
        script.StatusMessage('Log de debug limpo!')
    else:
        script.StatusMessage('Erro ao limpar log!')

def debug_clear_console():
    try:
        script.ClearScriptChat()
        debug_log('SISTEMA', 'Console do script limpo')
        script.StatusMessage('Console do script limpo!')
    except Exception as e:
        debug_erro('debug_clear_console', str(e), 'Erro ao limpar console')

def debug_status():
    try:
        stats = get_debug_stats()
        # ShowCollectionStatus será carregado pelo núcleo
        try:
            ShowCollectionStatus()
        except:
            pass
        debug_quick_info()
    except Exception as e:
        script.StatusMessage('Erro ao mostrar status: ' + str(e))

########################################
# Gestão de Cache (compartilhado com núcleo)
########################################
def clear_validation_cache():
    global _item_validation_cache, _cache_timestamp, _empty_slots_cache, _advanced_throttle
    _item_validation_cache.clear()
    _cache_timestamp.clear()
    _empty_slots_cache.clear()
    _advanced_throttle.clear()
    script.StatusMessage('[CACHE] Cache de validação limpo')

def cleanup_expired_cache():
    current_time = time.time()
    expired_keys = []
    for key, ts in _cache_timestamp.items():
        if current_time - ts > CACHE_TTL:
            expired_keys.append(key)
    for key in expired_keys:
        if key in _item_validation_cache:
            del _item_validation_cache[key]
        if key in _cache_timestamp:
            del _cache_timestamp[key]
    if expired_keys:
        debug_log('CACHE', 'Removidas {0} entradas expiradas do cache'.format(len(expired_keys)))

def get_cache_stats():
    current_time = time.time()
    valid_entries = 0
    expired_entries = 0
    for ts in _cache_timestamp.values():
        if current_time - ts < CACHE_TTL:
            valid_entries += 1
        else:
            expired_entries += 1
    stats = {
        'total_entries': len(_item_validation_cache),
        'valid_entries': valid_entries,
        'expired_entries': expired_entries,
        'empty_slots_cached': len(_empty_slots_cache),
        'throttle_entries': len(_advanced_throttle)
    }
    script.StatusMessage('[CACHE] Entradas: {0} | Válidas: {1} | Expiradas: {2}'.format(
        stats['total_entries'], stats['valid_entries'], stats['expired_entries']))
    return stats

def debug_cache_info():
    stats = get_cache_stats()
    script.StatusMessage('[CACHE] === Estatísticas do Cache ===')
    script.StatusMessage('[CACHE] Total de entradas: {0}'.format(stats['total_entries']))
    script.StatusMessage('[CACHE] Entradas válidas: {0}'.format(stats['valid_entries']))
    script.StatusMessage('[CACHE] Entradas expiradas: {0}'.format(stats['expired_entries']))
    script.StatusMessage('[CACHE] Slots vazios em cache: {0}'.format(stats['empty_slots_cached']))
    script.StatusMessage('[CACHE] Entradas de throttling: {0}'.format(stats['throttle_entries']))
    script.StatusMessage('[CACHE] TTL do cache: {0}s'.format(CACHE_TTL))

def auto_cleanup_cache():
    if len(_item_validation_cache) > 100:
        cleanup_expired_cache()
        if len(_item_validation_cache) > 150:
            clear_validation_cache()
            debug_log('CACHE', 'Cache limpo automaticamente - limite excedido')

def debug_cache_clear():
    clear_validation_cache()
    script.StatusMessage('[CACHE] Cache limpo manualmente!')

def debug_cache_cleanup():
    cleanup_expired_cache()
    script.StatusMessage('[CACHE] Limpeza de cache executada!')


