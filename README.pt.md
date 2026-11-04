# MyLight Systems

> Fork mantido por [azman0101](https://github.com/azman0101/hassio_mylight_integration), baseado no projeto de [Pierre-Emmanuel Mercier (@acesyde)](https://github.com/acesyde/hassio_mylight_integration). A licença MIT e os créditos originais são preservados; consulte [NOTICE.md](NOTICE.md).

🌐 [English](README.en.md) | [Français](README.md) | **Português** | [Deutsch](README.de.md) | [Español](README.es.md)

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]

_Integração para conectar ao [MyLight Systems][mylight_systems]._

> [!Warning]
>
> Esta integração suporta atualmente apenas a área de cliente **MyHome**. Para suporte ao **MyLight150**, uma extensão dedicada está disponível em [Racailloux/mylight150_ha](https://github.com/Racailloux/mylight150_ha).

**Esta integração irá configurar as seguintes plataformas.**

## Entidades fornecidas

### Sensores

| ID da entidade                                  | Descrição                                         | Unidade | Classe de estado   |
| ----------------------------------------------- | ------------------------------------------------- | ------- | ------------------ |
| `sensor.total_solar_production`                 | Energia acumulada produzida pelos painéis solares | Wh      | `total_increasing` |
| `sensor.total_grid_consumption`                 | Energia consumida da rede (com bateria virtual)   | Wh      | `total_increasing` |
| `sensor.total_grid_without_battery_consumption` | Energia consumida da rede (sem bateria virtual)   | Wh      | `total_increasing` |
| `sensor.total_autonomy_rate`                    | % do consumo coberto por solar + bateria          | %       | `measurement`      |
| `sensor.total_self_conso`                       | % da produção solar consumida localmente          | %       | `measurement`      |
| `sensor.total_msb_charge`                       | Energia acumulada carregada na Smart Battery      | Wh      | `total_increasing` |
| `sensor.total_msb_discharge`                    | Energia acumulada descarregada da Smart Battery   | Wh      | `total_increasing` |
| `sensor.total_green_energy`                     | Energia solar consumida diretamente pela sua casa | Wh      | `total_increasing` |
| `sensor.battery_state`                          | Energia atualmente armazenada na Smart Battery    | kWh     | `measurement`      |
| `sensor.grid_returned_energy`                   | Energia solar exportada para a rede               | Wh      | `total_increasing` |
| `sensor.water_heater_energy` | Energia acumulada do aquecedor; desativado por predefinição | Wh | `total_increasing` |
| `sensor.electric_power_capacity` | Potência elétrica contratada, quando fornecida pelo perfil | kVA | `measurement` |
| `sensor.grid_power` | Potência de rede: positiva importação, negativa exportação | W | `measurement` |
| `sensor.grid_import_power` | Potência importada de toda a casa | W | `measurement` |
| `sensor.grid_export_power` | Potência exportada para a rede | W | `measurement` |
| `sensor.water_heater_energy_today` | Energia de hoje do contador dedicado ao aquecedor (desde 0.11.0) | Wh | `total_increasing` |
| `sensor.water_heater_power` | Potência medida do aquecedor de água (desde 0.11.0) | W | `measurement` |
| `sensor.water_heater_green_play` | Estado do programa GreenPlay: `enabled` ou `disabled` (desde 0.11.0) | — | — |

### Potência da rede — desde 0.12.0

Três sensores só de leitura quando existe um único contador compatível. Leituras ausentes ou antigas permanecem desconhecidas. O intervalo de consulta não muda. Ver [origem e limites](docs/GRID_POWER.md).

### Aquecedor de água e GreenPlay — desde 0.11.0

Os IDs de entidade na tabela são exemplos baseados nas chaves dos sensores. Os IDs reais dependem do idioma, do nome da integração e de alterações de nome. Consulte a página do dispositivo antes de os usar numa automação.

Os três novos sensores só são criados se for encontrado exatamente um contador dedicado do tipo `cmp` ou `gmd`, com `deviceTypeId=water_heater`, ao iniciar a integração. A energia e a potência vêm do contador. O programa GreenPlay e o próximo comando vêm do relé de controlo identificado separadamente. Se o relé estiver ausente ou a identificação for ambígua, o estado GreenPlay permanece desconhecido.

`water_heater_energy_today` reinicia diariamente no fuso horário do Home Assistant. O sensor acumulativo existente `water_heater_energy` mantém o ID e o significado; continua desativado por predefinição e pode estar desconhecido se a API não fornecer esse total. Dados ausentes e leituras de potência antigas não são substituídos por zero.

GreenPlay é um sensor enum, não um interruptor. Os atributos incluem `green_play_ranges`, `next_command`, `power_measured_at`, `effective_report_period`, `discovery` e `controller_discovery`. Um programa ativo não significa que o relé esteja ligado; um relé ligado não prova que a resistência esteja a consumir energia.

O intervalo de consulta configurado não muda (15 minutos por predefinição). Reinicie o Home Assistant depois de atualizar pelo HACS. Se a descoberta estiver temporariamente indisponível ao iniciar, recarregue a integração quando a ligação recuperar. Consulte os limites e as verificações de leitura na [documentação detalhada](docs/WATER_HEATER_READ_ONLY.md), em inglês.

### Interruptores

| ID da entidade        | Descrição                                   | Notas                                             |
| --------------------- | ------------------------------------------- | ------------------------------------------------- |
| `switch.master_relay` | Controla o relé principal da sua instalação | Disponível apenas quando um relé está emparelhado |

## Instalação

## Automática

[![Abra a sua instância do Home Assistant e abra um repositório no Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=azman0101&repository=hassio_mylight_integration&category=integration)

## Manual

1. Abra o diretório da sua configuração do HA (onde se encontra o `configuration.yaml`).
2. Se não tiver um diretório `custom_components`, crie-o.
3. Dentro de `custom_components`, crie uma nova pasta chamada `mylight_systems`.
4. Baixe _todos_ os arquivos do diretório `custom_components/mylight_systems/` deste repositório.
5. Coloque os arquivos baixados na nova pasta criada.
6. Reinicie o Home Assistant.
7. Na interface do HA, vá em "Configuração" → "Integrações", clique em "+" e pesquise por "MyLight Systems".

## A configuração é feita pela interface

## Arquitetura

Consulte [ARCHITECTURE.md](ARCHITECTURE.md) para o diagrama completo de componentes e o fluxo de dados.

## Solução de problemas

### "O interruptor de relé está ausente"

A entidade `switch.master_relay` só é criada quando um relé (`sw`) está emparelhado à sua instalação. Se não tiver um relé, esta entidade não aparecerá.

### "Os valores dos sensores estão parados / não atualizam"

O coordenador consulta a API a cada 15 minutos. Se os valores pararem de atualizar:

1. Abra **Configurações → Dispositivos e Serviços → MyLight Systems** e verifique se há um aviso de erro.
2. Ative o log de depuração e verifique os logs do Home Assistant:

```yaml
# configuration.yaml
logger:
  default: warning
  logs:
    custom_components.mylight_systems: debug
```

3. Procure por entradas `CommunicationError` ou `UpdateFailed` — indicam um problema de rede ou uma mudança na API.

### "Falha de autenticação" após alteração de senha

Se você alterou sua senha do MyLight externamente, a integração exibirá um erro de autenticação. Vá em **Configurações → Dispositivos e Serviços → MyLight Systems** e use a opção **Re-autenticar** para inserir suas novas credenciais.

## Contribuições são bem-vindas!

Se quiser contribuir, leia as [diretrizes de contribuição](CONTRIBUTING.md).

---

[mylight_systems]: https://www.mylight-systems.com/
[commits-shield]: https://img.shields.io/github/commit-activity/y/azman0101/hassio_mylight_integration.svg?style=for-the-badge
[commits]: https://github.com/azman0101/hassio_mylight_integration/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/azman0101/hassio_mylight_integration.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-azman0101-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/azman0101/hassio_mylight_integration.svg?style=for-the-badge
[releases]: https://github.com/azman0101/hassio_mylight_integration/releases
