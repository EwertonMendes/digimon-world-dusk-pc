# Digimon World Dusk Recompiled — recompilação nativa

Projeto de recompilação estática do **Digimon World Dusk (Nintendo DS)**,
preservando o código ARM9/ARM7 original. Não é uma reescrita de batalhas,
menus ou campanha em linguagem de alto nível.

## Versão pública de testes — 17/10/2026

**v0.1.0 (Windows x64, playtest)** é a primeira identificação pública do projeto.
O jogo e o launcher apresentam `v0.1.0` na splash, nas configurações,
no título da janela, no nome do executável e nos metadados do Windows.
A tradução ainda é parcial e a campanha completa não foi certificada;
esta versão é destinada à coleta de feedback dos testadores.
O perfil de salvamento original permanece compartilhado entre versões.

## Histórico de desenvolvimento — 14/10/2026

- **v0.23**: versão integrada anterior, com ícone de janela e EXE sem cantos
  pretos, interface SDL3 nativa, salvamento EEPROM estável e gameplay em
  acompanhamento pelo responsável.
- **v0.29 (identificação interna anterior)**: nome **Digimon World Dusk Recompiled**,
  versão nos metadados e artefatos, splash host SDL3 de 2,6 segundos
  **“RECOMPILED BY TBLACK”**, pulável por teclado, mouse ou controle.
  A ROM, o áudio, a emulação ARM e os saves não são modificados.
  A versão só deve ser considerada jogável após build privada e teste real.
- **Histórico v0.16–v0.22**: etapas de recompilação/AOT, interface e
  estabilidade; consulte o histórico de PRs e os relatórios em `docs/research/`.
- O `dusk_pc.exe` produzido no CI público é **somente a demonstração
  gráfica sintética**, não o jogo completo.
- A distribuição de testes `v0.1.0` disponibiliza um **Windows EXE de um clique**
  como asset de um pré-lançamento no GitHub, contendo runtime SDL3 e a ROM
  previamente validada pelo responsável. Não requer WSL, compiladores nem
  configuração manual de ROM no computador de quem joga.

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

### Gerar novas builds Windows sem instalar ferramentas

O workflow **[Dusk native Windows game (owner playtest)](https://github.com/EwertonMendes/digimon-world-dusk-pc/actions/workflows/dusk-native-windows-playtest.yml)**
faz a compilação real ARM9/ARM7 + SDL3 e entrega o EXE de teste em
*Artifacts* quando executado com autorização explícita.
O pacote é um candidato de testes; os overlays não convertidos continuam
usando o interpretador Tier3. Ver [instruções completas](docs/windows-native-build.md).

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

## Identidade visual do aplicativo

O ícone oficial e a nova tela de abertura reutilizam uma única [arte aprovada](assets/icons/dusk-icon-master.webp)
para Windows, Linux, macOS e Android por `tools/generate_icons.py`.
O launcher Windows e a janela SDL3 do jogo recebem seus respectivos ícones
nas builds privadas; a splash é gerada por `tools/generate_splash.py` e integrada na **v0.29**. Os ports Linux/macOS/Android ainda exigem
integração e compilação próprias. Consulte [recursos e instruções](docs/icon-assets.md).

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
