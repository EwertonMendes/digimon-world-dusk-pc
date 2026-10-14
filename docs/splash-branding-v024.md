# Recompiled v0.24: identidade e abertura

**Produto:** Digimon World Dusk Recompiled  
**Crédito:** Recompiled by Tblack  
**Versão de playtest:** v0.24  
**EXE:** `Digimon-World-Dusk-Recompiled-v0.24-Windows.exe`

## Abertura nativa

A ferramenta `tools/generate_splash.py` cria um bitmap RGB 1280 × 720,
composição azul/roxo/ciano, a arte aprovada do ícone e crédito ao autor.
O workflow Windows gera o asset antes da compilação, valida dimensões e
inclui `dusk-splash.bmp` no arquivo ZIP autenticado embutido no único EXE.

No primeiro arranque, o launcher extrai o BMP para o diretório de runtime
por versão e fornece `NDS_DUSK_SPLASH_PATH`. O frontend SDL3 fixa um
quadro inicial por 2,6 s, com fade de 300 ms e letterbox correto.
Teclado, clique do mouse ou botão do controle pulam a animação.
Fechar a janela nessa etapa encerra a inicialização. A emulação não executa
quadros da ROM durante a splash.

A implementação fica isolada em
`tools/patches/ndsrecomp-dusk-recompiled-splash.patch`. Nenhuma imagem de
ROM, memória de jogo, música do jogo ou recurso de rede são introduzidos.

## Identidade e perfil

- `tools/branding.py`: nome, versão, nome de artefato e crédito usados
  para recursos gerados e testes de consistência.
- `tools/generate_icons.py`: ícone + VERSIONINFO Windows, Linux desktop
  entry e nome de aplicativo Android preparado para um port futuro.
- `native-launcher/desktop/save_data.go`: runtime `v0.24` separado,
  sem trocar o perfil persistente em `userdata/A6RE`.
- O `CMakeLists.txt` mantém o protótipo gráfico sem ROM identificado
  explicitamente como **PRESENTATION-PROTOTYPE**. Ele não é o jogo.

Para gerar o jogo completo use o workflow privado
`dusk-native-windows-playtest.yml`, com `approve_game_bundle=true`.
Um repack rápido de executáveis v0.23 não seria seguro para a nova splash,
por isso v0.24 exige reconstrução do runner SDL3. Não publique uma versão
como validada antes de confirmar build, abertura, controles e saves.
