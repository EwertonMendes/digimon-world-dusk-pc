# Solução de problemas

## Que executável estou usando?

- `dusk_pc.exe` baixado do Actions público: **protótipo de imagens
  sintéticas**, não o jogo; não suporta Save/Continue original.
- `Digimon-Dusk-PC-Windows-v0.16.exe` empacotado privadamente:
  launcher da experiência nativa real, com ROM e SDL3 inclusos.
- `v0.17` em desenvolvimento: a PR pública inclui código do launcher
  mas não o runner completo nem build jogável até empacotamento privado.

## Jogo não abre

Verifique o aviso nativo Windows exibido pelo launcher.
Não instale WSL ou compiladores no computador do jogador.
Se disser que o pacote não corresponde à ROM/runner esperado, o launcher
bloqueou dados inconsistentes por segurança. Se disser que já há outra
instância aberta, feche o outro jogo antes de tentar novamente.

## Saves e backups

O save de cartucho é `%LOCALAPPDATA%\\DuskNativePC\\userdata\\A6RE\\saves\\dusk.sav`
e deve ter 65.536 bytes. **Não** substitua arquivo diferente à força.
v0.17 incorpora backup deduplicado e gerenciador inicial via
`--manage-saves` quando houver executável privado correspondente.
Caso apareça um arquivo `.restore-rollback`, preserve-o e examine o
aviso do launcher antes de qualquer intervenção manual.

## Imagem, teclado ou toque

Abra `Esc/F10` para PC Options. O modo `16:9 FILL` faz stretching
do frame original, não é widescreen nativo do mapa. Use `F11` para
alternar modo janela/tela cheia. Caso o PiP não apareça, verifique
`AUXILIARY SCREEN` e `MAIN DISPLAY`.

## Quedas de FPS e áudio

Registre o horário aproximado e mantenha localmente os arquivos
`performance-*.jsonl`, `game-coverage-*.json` e `hostprof-*.ndshp`.
**Não envie os arquivos brutos ao repositório público**; coverage contém
código RAM do jogo e hostprof pode conter caminhos de usuário.
A análise segura é feita por `tools/analyze_v016_sessions.py`.
O overlay do PC Options não garante pausar a simulação DS na v0.16.

Veja [docs/research/2026-10-14-v016-owner-sessions-safe.md](research/2026-10-14-v016-owner-sessions-safe.md).
