# Arquitetura real — Digimon World Dusk PC

_Atualizado em 14/10/2026. Não confundir o protótipo gráfico público com o runner privado._

## Dois alvos distintos no repositório

1. **Protótipo público**: `dusk_pc.exe` (Win32/GDI, quadros sintéticos),
   `dusk_rom_info`, geometria, testes C++ e validações Python.
   Ele não executa Digimon World Dusk.
2. **Jogo privado Windows**: launcher Go em `native-launcher/desktop`,
   runner recompilado ARM9/ARM7/overlays no NDSRecomp fixado, SDL3,
   ROM incorporada ao pacote e perfil de save separado da instalação.

## Fluxo de execução real

```text
Pacote EXE de um clique autenticado por SHA-256
 ├─ launcher: verifica ROM/runner/DLL e pasta de instalação versionada
 ├─ userdata/A6RE: firmware identity + EEPROM 64KiB + backups
 └─ NDSRecomp Windows x64: CPU ARM9/ARM7, scheduler, GPU, áudio
      ├─ dispatch de bancos AOT ARM/Thumb verificado por bytes
      ├─ overlays ARM9 conforme código realmente observado
      └─ Tier3 para caminhos ainda não convertidos
           └─ SDL3: telas, PiP, toque, entrada e PC Options
```

### Regras de equivalência

- O código de negócio/jogo permanece ARM original recompilado, não lógica
  manual de batalha, evolução ou roteiro.
- **CPU, modo, endereço, bytes e geração** condicionam despacho AOT para
  evitar que overlays diferentes sejam confundidos.
- A simulação usa o clock original DS (~59,826 Hz), independentemente
  da apresentação escolhida.
- O overlay PC Options é uma interface host SDL3; não está inserido
  nos menus de código ARM do cartucho.
- O gerenciador Go guarda a EEPROM em perfil estável A6RE fora de v0.16/v0.17,
  com mutex entre processos e backup pré-jogo. Não há save states.
- Layout `16:9 FILL` estica os pixels: não muda a câmera do DS.

### Fronteira de modularização

Hoje os patches da interface SDL3 são aplicados sequencialmente em
`upstream/runner/src/frontend.cpp`. O objetivo v0.17 é reduzir esse
acoplamento com componentes Dusk isolados e uma camada de integração
pequena, **sem alterar a semântica do core original**. Não descrever
essa refatoração como concluída até o runner completo ser recompilado
e testado na variante privada.

## Caminhos e responsabilidades

- `native-launcher/desktop/*.go`: launcher privado, perfis, recuperação de saves.
- `tools/prepare_dusk_recomp.py`: extração/configuração privada de bancos.
- `tools/merge_verified_profiles.py`: coleta de gerações RAM; união segura de roots.
- `tools/promote_tier3_spans.py`: promoção de spans comprovados.
- `tools/pack_native_private.py`: ZIP autenticado no executável Windows.
- `tools/analyze_v016_sessions.py`: sumários seguros de sessões reais.
- `tools/patches/`: integração temporária no NDSRecomp pinado.
- `.github/workflows/build.yml`: testes sem ROM, nunca build final de campanha.

Ver [roadmap](roadmap.md) e [evidência real de v0.16](research/2026-10-14-v016-owner-sessions-safe.md).
