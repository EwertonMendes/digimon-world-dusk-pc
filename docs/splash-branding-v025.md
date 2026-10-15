# Digimon World Dusk Recompiled v0.26 — abertura cinematográfica

## Identidade
- Janela e executável: **Digimon World Dusk Recompiled | v0.26**
- Crédito: **Recompiled by Tblack**
- Progresso original mantido em `%LOCALAPPDATA%/DuskNativePC/userdata/A6RE/saves/dusk.sav`
- Fonte aprovada: `assets/splash/dusk-recompiled-art.webp` (versão não gravada na imagem; SHA-256 fixado no gerador)
- `tools/generate_splash.py` exporta BMP RGB24 **3840 × 2160** com interpolação Lanczos do original 1672 × 941, sem fabricar detalhes nativos 4K.

## Abertura SDL3
- A tela de 5 segundos usa o artwork 4K com fade-in de 300 ms. Teclas/acessos involuntários não a descartam; **P** pausa/retoma e fechar a janela sai.
- O renderer mantém a textura até o primeiro quadro realmente renderizado pela ROM. Durante os próximos **800 ms** a textura dissolve sobre o jogo em execução, eliminando frames intermediários pretos ou brancos.
- A versão é desenhada no canto pelo SDL3 a partir de `NDS_DUSK_SPLASH_VERSION`, sem estar gravada no bitmap.
- O fluxo não modifica CPU/ARM, ROM, FPS, áudio, contagem de quadros da emulação nem o save; apenas a composição visual do host.
- O modo `fast_repack` só é permitido se `tools/native_runtime_pin.py` aprovar a versão imutável do runner. Mudanças C++ requerem uma build completa antes do próximo repack rápido.

## Distribuição
O EXE real é um arquivo Windows único com launcher e payload SHA-256 autenticado. O Actions publica o artefato ZIP por padrão, mas a entrega ao testador pode ser um link direto para um `.exe` extraído desse artefato. Nenhum ZIP deve ser exigido para abrir o jogo.
