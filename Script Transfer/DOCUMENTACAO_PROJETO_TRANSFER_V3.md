# Documentação do Projeto Transfer V3

## Visão Geral

O **Transfer V3** é um sistema automatizado de transferência de itens entre personagens no jogo Tibia ME, desenvolvido em Python para funcionar com o bot Mindee-BOT. O sistema implementa uma arquitetura cliente-servidor onde dois personagens trabalham em conjunto: um **Coletor** e um **Soltador**.

## Arquitetura do Sistema

### Estrutura de Arquivos

```
Script Transfer/
├── script_principal_transfer_v3.py     # Ponto de entrada principal
├── modulo_transfer_v3.py               # Agregador que carrega todos os módulos
├── core_transfer_state_v3.py           # Gerenciamento de estado e configurações
├── core_transfer_protocol_v3.py        # Protocolo de comunicação via PM
├── core_transfer_collector_v3.py       # Lógica do personagem coletor
├── core_transfer_dropper_v3.py         # Lógica do personagem soltador
└── debug/
    └── debug_and_cache_v3.py           # Sistema de debug e cache
```

## Componentes Principais

### 1. Script Principal (`script_principal_transfer_v3.py`)

**Função**: Ponto de entrada que carrega o sistema completo e atua como bridge entre o bot e o sistema Transfer.

**Características**:
- Carrega o módulo principal via `execfile()`
- Implementa todas as funções de callback do bot (onScriptActivation, onReceivePrivateMessage, etc.)
- Cada callback redireciona para a função correspondente no sistema Transfer
- Tratamento de erros robusto com try/catch em todas as funções

### 2. Módulo Agregador (`modulo_transfer_v3.py`)

**Função**: Carrega todos os submódulos em um namespace global unificado.

**Características**:
- Carrega módulos na ordem correta: debug → state → protocol → collector → dropper
- Implementa funções bridge que redirecionam eventos para o módulo apropriado baseado no papel do personagem
- Detecta automaticamente se o personagem é Coletor ou Soltador
- Gerencia contexto do depot e eventos do jogo

### 3. Gerenciamento de Estado (`core_transfer_state_v3.py`)

**Função**: Centraliza configurações, estado da sessão e dados dos personagens.

**Características Principais**:
- **Configuração de Personagens**: Mapeamento detalhado de itens por personagem
- **Papéis Dinâmicos**: Sistema que detecta automaticamente Coletor vs Soltador
- **Estados da Sessão**: IDLE, PREPARANDO_LOTE, ENTREGANDO, AGUARDANDO, DEPOSITANDO, CONCLUIDO
- **Configurações de Itens**: ID, página do depot, quantidade máxima por página, nomes

**Configuração de Exemplo**:
```python
PERSONAGEM_ITEMS = {
    'Nywk': [
        {'item_id': 2606, 'pagina_coletor': 3, 'max_por_pagina': 28, 'nome': 'Breathnut'},
        {'item_id': 6584, 'pagina_coletor': 3, 'max_por_pagina': 14, 'nome': 'Spider crystal'},
    ],
    'Johmartins': [
        {'item_id': 6406, 'pagina_coletor': 10, 'nome': 'Crystal stinger'},
    ]
}
```

### 4. Protocolo de Comunicação (`core_transfer_protocol_v3.py`)

**Função**: Define o protocolo de mensagens privadas entre Coletor e Soltador.

**Comandos do Coletor para Soltador**:
- `PEDIR id_item qtd` - Solicita quantidade específica de um item
- `ACK 1` - Confirma recebimento de item no chão
- `FIM_ITEM` - Finaliza transferência do item atual
- `FIM_SESSAO` - Encerra sessão completa

**Comandos do Soltador para Coletor**:
- `CONFIRMAR qtd` - Confirma quantidade disponível para entrega
- `CONCLUIDO qtd` - Informa quantidade entregue
- `SEM_ESTOQUE qtd` - Informa falta de estoque

### 5. Lógica do Coletor (`core_transfer_collector_v3.py`)

**Função**: Implementa o comportamento do personagem que coleta itens.

**Fluxo Principal**:
1. **Inicialização**: Vai para tile de drop, abre depot
2. **Medição**: Conta slots livres na página configurada
3. **Solicitação**: Envia PM "PEDIR" para o Soltador
4. **Coleta**: Aguarda itens no chão e os pega
5. **Depósito**: Armazena itens coletados no depot
6. **Repetição**: Continua até esgotar capacidade ou estoque

**Características Técnicas**:
- Navegação inteligente entre páginas do depot
- Controle de timeouts para ACK
- Medição precisa de slots livres
- Tratamento de erros e recuperação automática

### 6. Lógica do Soltador (`core_transfer_dropper_v3.py`)

**Função**: Implementa o comportamento do personagem que fornece itens com controles avançados de segurança e robustez.

**Fluxo Principal**:
1. **Recebimento**: Aguarda PM "PEDIR" do Coletor
2. **Confirmação**: Verifica estoque e responde com "CONFIRMAR"
3. **Retirada**: Retira itens do depot para a mochila
4. **Entrega**: Solta itens no tile de drop
5. **Confirmação**: Aguarda ACK do Coletor
6. **Repetição**: Continua até completar quantidade solicitada

**Características Técnicas Avançadas**:

**Sistema de Validação por Nome**:
- Verifica automaticamente o nome do item retirado via `onReceiveItemDescriptionBackpack`
- Comparação insensível a maiúsculas/minúsculas entre nome esperado e obtido
- Devolve itens incorretos de volta ao depot no slot de origem usando `StoreSlotInDepotSlot`
- Fallback para qualquer slot livre do depot se o slot original falhar
- Sistema de blacklist (`REJECTED_DEPOT_SLOTS`) para evitar retentar slots com itens errados
- Timeout de 1.2s com até 3 tentativas de verificação por `LookAtBackPackSlot`

**Controle de ACK e Watchdog**:
- Timeout de 10s aguardando ACK do Coletor (`ACK_TIMEOUT_MS`)
- Máximo de 3 timeouts antes de finalizar parcialmente (`ACK_MAX_TIMEOUTS`)
- Verificação dupla: por PM e por contador de itens
- Sistema de watchdog para detectar falhas de comunicação

**Navegação Inteligente no Depot**:
- Varredura automática entre páginas com `DepotGoNext()`
- Controle de páginas visitadas para evitar loops infinitos
- Timeout máximo de busca para evitar travamentos
- Reposicionamento automático no tile de drop ao sair do depot

**Controle de Sessão e Estado**:
- Variável `dropper_session_active` para controlar sessões ativas
- Modo depot (`depotMode`): 0=idle, 2=retirada
- Controle de flags de espera (`dropper_waiting_menu`, `dropper_waiting_ack`)
- Reset automático de estado entre sessões

**Sistema de Retry e Recuperação**:
- Retry automático em falhas de retirada (800ms)
- Retry em falhas de drop (600ms)
- Reposicionamento automático em caso de falha de `EnterShop`
- Entrega parcial quando mochila fica cheia ou timeout

**Otimizações de Performance**:
- Delays otimizados entre operações (200-600ms)
- Aceleração do ciclo via `onReceiveAddItemToBackpack`
- Pausar storage durante verificação de nome
- Cancelamento de eventos desnecessários

**Logs e Debug**:
- Sistema de logs detalhado com níveis (INFO, WARNING, DEBUG)
- Rastreamento de tentativas e timeouts
- Monitoramento de páginas visitadas e itens processados

### 7. Sistema de Debug (`debug_and_cache_v3.py`)

**Função**: Fornece logging detalhado e cache para otimização.

**Características**:
- **Níveis de Log**: ALL, SMART, INFO, WARNING, ERROR
- **Throttling**: Evita spam de logs repetitivos
- **Cache de Validação**: Otimiza verificações de itens
- **Rotação de Logs**: Limita tamanho do arquivo de log
- **Performance Tracking**: Mede tempo de operações

## Fluxo de Funcionamento

### Cenário Típico de Transferência

1. **Inicialização**:
   - Ambos personagens ativam o script
   - Sistema detecta papéis automaticamente
   - Coletor vai para tile de drop e abre depot

2. **Ciclo de Transferência**:
   ```
   Coletor: Mede slots livres (ex: 09 slots)
   Coletor → Soltador: "PEDIR 2606 09"
   Soltador: Verifica estoque de Breathnut
   Soltador → Coletor: "CONFIRMAR 09"
   Soltador: Retira 09 Breathnut do depot
   Soltador: Solta 1 Breathnut no chão
   Coletor: Pega item e envia "ACK 1"
   Soltador: Solta próximo item
   ... (repete até 09 itens)
   Coletor: Deposita todos os itens no depot
   ```

3. **Finalização**:
   - Coletor envia "FIM_ITEM" quando página estiver cheia
   - Sistema pode continuar com próximo item da lista
   - Ou enviar "FIM_SESSAO" para encerrar

## Configuração e Uso

### Pré-requisitos
- Mindee-BOT configurado
- Dois personagens no mesmo local
- Acesso ao depot configurado

### Configuração Inicial

1. **Editar Caminhos**: Ajustar `CAMINHO_MODULO_TRANSFER_V3` no script principal
2. **Configurar Personagens**: Adicionar personagens e itens em `PERSONAGEM_ITEMS`
3. **Definir Tile de Drop**: Configurar `DROP_TILE_X/Y/Z` para localização de transferência
4. **Configurar Papéis**: Definir `COLETOR_NOME` e `SOLTADOR_NOME`

### Execução

1. Ativar script no personagem Coletor
2. Ativar script no personagem Soltador
3. Sistema inicia automaticamente a transferência

## Características Avançadas

### Detecção Automática de Papéis
O sistema identifica automaticamente se o personagem é Coletor ou Soltador baseado no nome configurado.

### Navegação Inteligente
- Suporte a múltiplas páginas do depot
- Navegação otimizada com fallback para métodos alternativos
- Controle de retry em caso de falhas

### Tolerância a Falhas
- Timeouts configuráveis para todas as operações
- Sistema de retry automático
- Recuperação de estado em caso de erros

### Sistema de Cache
- Cache de validação de itens para performance
- Throttling de logs para evitar spam
- Limpeza automática de cache expirado

## Limitações e Considerações

### Limitações Técnicas
- Máximo de 9 itens por lote (`LOTE_MAX = 9`)
- Dependente da API do Mindee-BOT
- Requer coordenação manual inicial dos personagens

### Considerações de Segurança
- Validação por nome de item no Soltador
- Timeouts para evitar travamentos
- Logs detalhados para auditoria

### Performance
- Otimizado para transferências em lote
- Cache para reduzir chamadas de API
- Throttling para evitar sobrecarga do servidor

## Manutenção e Troubleshooting

### Logs de Debug
- Arquivo: `transfer_debug.log`
- Níveis configuráveis de verbosidade
- Rotação automática por tamanho

### Problemas Comuns
1. **Personagem não reconhecido**: Verificar configuração de nomes
2. **Timeout de ACK**: Ajustar `ACK_TIMEOUT_MS`
3. **Falha na navegação**: Verificar páginas configuradas
4. **Itens não encontrados**: Validar IDs e nomes dos itens

### Monitoramento
- Status messages no chat do jogo
- Logs detalhados de todas as operações
- Contadores de performance e estatísticas

## Conclusão

O Transfer V3 representa uma solução robusta e automatizada para transferência de itens entre personagens, com arquitetura modular, tolerância a falhas e sistema de debug avançado. O design permite fácil manutenção e extensão para novos recursos.