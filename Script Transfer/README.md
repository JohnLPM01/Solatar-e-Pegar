# Transfer V3 🔄

Sistema automatizado de transferência de itens entre personagens no Tibia ME usando Mindee-BOT.

## 📋 Visão Geral

O **Transfer V3** é um sistema robusto e automatizado que permite a transferência eficiente de itens entre dois personagens no jogo Tibia ME. O sistema implementa uma arquitetura cliente-servidor onde um personagem **Coletor** solicita itens e um personagem **Soltador** os fornece através de um protocolo de comunicação via mensagens privadas.

## ✨ Características Principais

- 🤖 **Automação Completa**: Sistema totalmente automatizado com detecção de papéis
- 🔄 **Protocolo Robusto**: Comunicação confiável via mensagens privadas
- 📦 **Gestão Inteligente**: Controle automático de estoque e capacidade
- 🛡️ **Validação de Itens**: Sistema de verificação por nome com blacklist
- 🔧 **Sistema de Debug**: Logs detalhados e cache para troubleshooting
- ⚡ **Performance Otimizada**: Throttling e otimizações para eficiência

## 🏗️ Arquitetura

```
Script Transfer/
├── script_principal_transfer_v3.py     # Ponto de entrada principal
├── modulo_transfer_v3.py               # Agregador de módulos
├── core_transfer_state_v3.py           # Gerenciamento de estado
├── core_transfer_protocol_v3.py        # Protocolo de comunicação
├── core_transfer_collector_v3.py       # Lógica do coletor
├── core_transfer_dropper_v3.py         # Lógica do soltador
└── debug/
    └── debug_and_cache_v3.py           # Sistema de debug
```

## 🚀 Como Funciona

### Personagem Coletor
1. **Inicialização**: Posiciona-se no tile de drop e abre depot
2. **Medição**: Calcula slots livres disponíveis na página configurada
3. **Solicitação**: Envia comando `PEDIR id_item qtd` via PM
4. **Coleta**: Aguarda itens no chão e os coleta automaticamente
5. **Depósito**: Armazena itens no depot na página correta
6. **Repetição**: Continua o ciclo até esgotar capacidade ou estoque

### Personagem Soltador
1. **Preparação**: Abre depot e navega para página do item
2. **Confirmação**: Responde com `CONFIRMAR qtd` informando disponibilidade
3. **Retirada**: Remove itens do depot com validação por nome
4. **Entrega**: Solta itens no tile de drop
5. **Finalização**: Confirma entrega com `CONCLUIDO qtd`

## 📋 Pré-requisitos

- **Mindee-BOT** instalado e configurado
- **Python** (compatível com Mindee-BOT)
- Dois personagens no Tibia ME
- Acesso ao depot para ambos os personagens

## ⚙️ Configuração

### 1. Configuração de Personagens

Edite o arquivo `core_transfer_state_v3.py` para configurar os itens:

```python
PERSONAGEM_ITEMS = {
    'NomePersonagem1': [
        {
            'item_id': 2606,           # ID do item no jogo
            'pagina_coletor': 3,       # Página do depot do coletor
            'max_por_pagina': 28,      # Máximo de itens por página
            'nome': 'Breathnut'        # Nome do item para validação
        },
    ],
    'NomePersonagem2': [
        {
            'item_id': 6584,
            'pagina_coletor': 3,
            'max_por_pagina': 14,
            'nome': 'Spider crystal'
        },
    ]
}
```

### 2. Configuração de Tiles

Configure as posições no arquivo de estado:

```python
# Tile onde os itens são dropados/coletados
TILE_DROP = {'x': 1000, 'y': 1000, 'z': 7}

# Tile do depot
TILE_DEPOT = {'x': 1001, 'y': 1001, 'z': 7}
```

## 🎮 Como Usar

### 1. Preparação
- Posicione ambos os personagens próximos ao depot
- Certifique-se de que ambos têm acesso ao tile de drop configurado
- Verifique se os itens estão nas páginas corretas do depot

### 2. Execução
1. Carregue o script em ambos os personagens via Mindee-BOT
2. O sistema detectará automaticamente os papéis (Coletor/Soltador)
3. Inicie a transferência usando os comandos do protocolo

### 3. Comandos Disponíveis

**Comandos do Coletor:**
- `PEDIR id_item qtd` - Solicita quantidade específica de um item
- `ACK 1` - Confirma recebimento de item
- `FIM_ITEM` - Finaliza transferência do item atual
- `FIM_SESSAO` - Encerra sessão completa

**Comandos do Soltador:**
- `CONFIRMAR qtd` - Confirma quantidade disponível
- `CONCLUIDO qtd` - Informa quantidade entregue
- `SEM_ESTOQUE qtd` - Informa falta de estoque

## 🔧 Funcionalidades Avançadas

### Sistema de Validação
- **Verificação por Nome**: Valida itens retirados comparando nomes
- **Sistema de Blacklist**: Evita slots com itens incorretos
- **Fallback Inteligente**: Devolve itens incorretos ao depot

### Sistema de Debug
- **Logs Detalhados**: Rastreamento completo de operações
- **Cache de Validação**: Otimização de verificações repetidas
- **Throttling**: Controle de performance e rate limiting

### Recuperação de Erros
- **Timeouts Configuráveis**: Controle de tempo limite para operações
- **Retry Automático**: Tentativas automáticas em caso de falha
- **Estados de Sessão**: Controle robusto do fluxo de execução

## 📊 Estados do Sistema

- `IDLE` - Sistema inativo
- `PREPARANDO_LOTE` - Preparando transferência
- `ENTREGANDO` - Soltador entregando itens
- `AGUARDANDO` - Aguardando confirmação
- `DEPOSITANDO` - Coletor depositando itens
- `CONCLUIDO` - Transferência finalizada

## 🐛 Troubleshooting

### Problemas Comuns

**Sistema não detecta papel:**
- Verifique se os nomes dos personagens estão corretos na configuração
- Confirme se os itens estão configurados para o personagem correto

**Itens não são encontrados:**
- Verifique se o `item_id` está correto
- Confirme se os itens estão na página correta do depot
- Verifique se o nome do item está exato (case-insensitive)

**Timeouts frequentes:**
- Ajuste os valores de timeout no arquivo de configuração
- Verifique a latência da conexão
- Confirme se os tiles estão acessíveis

### Logs de Debug

Ative o debug no arquivo `debug_and_cache_v3.py`:

```python
DEBUG_ENABLED = True
DEBUG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR
```

## 📄 Licença

Este projeto é fornecido "como está" para uso educacional e pessoal. Use por sua própria conta e risco.

## 🤝 Contribuição

Contribuições são bem-vindas! Sinta-se livre para:
- Reportar bugs
- Sugerir melhorias
- Submeter pull requests
- Melhorar a documentação

## ⚠️ Aviso Legal

Este script é destinado para uso educacional e pessoal. O uso de bots em jogos online pode violar os termos de serviço. Use por sua própria responsabilidade.

---

**Desenvolvido para Tibia ME com Mindee-BOT** 🎮