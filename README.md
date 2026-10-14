# Digimon World Dusk PC — recompilação nativa

Projeto de recompilação estática do **Digimon World Dusk (Nintendo DS)**,
preservando o código ARM9/ARM7 original. Não é uma reescrita de batalhas,
menus ou campanha em linguagem de alto nível.

## Estado verificável — 14/10/2026

- **v0.16**: build privada Windows x64 jogável, com SDL3 nativo, Focus + PiP,
  janela/tela cheia, PC Options, teclado, mouse, gamepad e save de cartucho
  EEPROM 64 KiB. Os testes do proprietário continuam durante o gameplay;
  não há alegação de campanha inteira certificada.
- **v0.17 (em desenvolvimento)**: consolidação segura de cobertura AOT,
  telemetria de sessões reais, retenção e restauração de saves, documentação
  e melhorias progressivas de arquitetura. Consulte a [PR #17](../../pull/17)
  e [roadmap](docs/roadmap.md) para itens aprovados e pendentes.
- O `dusk_pc.exe` produzido no CI público é **somente a demonstração
  gráfica sintética**, não o jogo completo.
- O GitHub público não publica o executável com ROM nem código ARM derivado.
  A ferramenta de empacotamento privada cria um **Windows EXE de um clique**,
  com runtime SDL3 e ROM verificada já incluídos, sem WSL ou compilação no
  computador de quem joga.

## Como jogar uma build privada Windows

Execute o pacote Windows x64 entregue pelo responsável pelo projeto.
O launcher verifica os arquivos, configura o runtime local e abre o jogo.
Não é necessário selecionar ROM, abrir navegador, instalar compiladores
ou executar comandos.

Seus dados são persistidos entre versões em:

```text
%LOCALAPPDATA%\DuskNativePC\userdata\A6RE\saves\dusk.sav
```

O salvamento utiliza o menu original do jogo, **não save states**.
Em builds v0.17 com o novo launcher, `--manage-saves` abre o diálogo
de backup/restauração antes do jogo; use apenas quando o jogo estiver fechado.

Controles e PC Options: [interface v0.16](docs/native-immersive-ui-v016.md).
[Guia de pacote Windows](docs/windows-oneclick.md).

## Arquitetura

```text
Dusk original ARM9/ARM7 + overlays
  -> bancos AOT com verificação de bytes em tempo de execução
  -> NDSRecomp fixado + fallback Tier3 para código não coberto
  -> SDL3 (vídeo, áudio, controles e PC Options)
  -> launcher Windows de um clique + EEPROM persistente
```

O relógio simulado do Nintendo DS permanece em aproximadamente **59,826 Hz**.
O seletor de apresentação 30/60 FPS não acelera nem desacelera a simulação.
`16:9 FILL` estica a imagem original: não expande a câmera do jogo.

Documentos: [arquitetura](docs/architecture.md),
[recompilação](docs/recompilation.md),
[pesquisa v0.16 segura](docs/research/2026-10-14-v016-owner-sessions-safe.md).

## Desenvolvimento e testes

O CI público testa o núcleo C++20, layouts, controles sintéticos, ferramentas
Python, regras do NDSRecomp fixado e o launcher Go **sem ROM**.
Um runner com o jogo completo só pode ser montado no ambiente privado que
possui a ROM, bancos derivados e DLLs corretas. **Um CI verde não prova
que uma build completa do jogo foi gerada.**

```sh
cmake -S . -B build -DDUSK_BUILD_TESTS=ON
cmake --build build --config Release
ctest --test-dir build -C Release --output-on-failure
```

Para testar o launcher Windows em CI, use `cd native-launcher/desktop && go test ./...`
em Windows; para compilar sem executá-lo, pode-se usar cross-compilation Go.

## Código e distribuição

O upstream [NDSRecomp](https://github.com/RetroPortingToolKit/ndsrecomp)
na revisão fixada `3a57236bb23d25dcb4caad7d58d733311062ff5e`
usa **PolyForm Noncommercial 1.0.0**. É necessária a observância também
dos direitos associados ao jogo original, independentemente da licença do
código do launcher. Evite publicar aqui ROMs, BIOS, código extraído,
bancos ARM gerados, perfis completos de RAM, saves ou pacotes privados.

Veja [AGENTS.md](AGENTS.md) para as regras de contribuição.
