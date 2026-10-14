# Recompiled v0.25: identidade e abertura

**Produto:** Digimon World Dusk Recompiled  
**Crédito:** Recompiled by Tblack  
**Versão de playtest:** v0.25  
**EXE:** `Digimon-World-Dusk-Recompiled-v0.25-Windows.exe`

## Abertura nativa

A ferramenta `tools/generate_splash.py` cria um bitmap RGB 1280 × 720,
composição azul/roxo/ciano, a arte aprovada do ícone e crédito ao autor.
O workflow Windows gera o asset antes da compilação, valida dimensões e
inclui `dusk-splash.bmp` no arquivo ZIP autenticado embutido no único EXE.

No primeiro arranque, o launcher extrai o BMP para o diretório de runtime
por versão e fornece `NDS_DUSK_SPLASH_PATH`. O frontend SDL3 fixa um
quadro inicial por 5 s, com fade de 300 ms e letterbox correto.
A tela aparece por cinco segundos sem ser pulada por entradas involuntárias. Pressionar P congela a abertura e pressionar P novamente continua a contagem. A duração é configurável no launcher sem alterar o runner.
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
- `native-launcher/desktop/save_data.go`: runtime `v0.25` separado,
  sem trocar o perfil persistente em `userdata/A6RE`.
- O `CMakeLists.txt` mantém o protótipo gráfico sem ROM identificado
  explicitamente como **PRESENTATION-PROTOTYPE**. Ele não é o jogo.

Para gerar o jogo completo use o workflow privado
`dusk-native-windows-playtest.yml`, com `approve_game_bundle=true`.
Um repack rápido de executáveis v0.23 não seria seguro para a nova splash,
por isso v0.25 exige reconstrução do runner SDL3. Não publique uma versão
como validada antes de confirmar build, abertura, controles e saves.

## Builds rápidas após a v0.25

O build completo recompila o NDSRecomp/ARM e faz link do runner. A primeira
v0.24 fez 250 compilações sem cache anterior, por isso levou ~20 minutos.
O workflow `dusk-recompiled-fast-repack.yml` recompila apenas o launcher
Go e os recursos cosméticos (ícones/splash) e reutiliza o último runner
cujo EXE e artefato são fixados por SHA-256 em
`tools/native-windows-runtime-pin.json`.

`tools/native_runtime_pin.py` verifica que nenhum arquivo em
`tools/patches/` ou gerador de código nativo foi alterado. Se algo divergir,
o caminho rápido falha explicitamente e requer build nativa.
O SHA do executável original é verificado antes de extrair
ROM/runner/dependências de um pacote já autenticado.

O título SDL3 e duração passam a vir de variáveis de ambiente do launcher,
permitindo versões futuras e tempos cosméticos novos sem novo compilador C++.
Não misturar recurso gráfico novo com runtime antigo sem a validação de pin.

## Revisão visual da arte

O CI público disponibiliza o PNG `Tblack-Splash-PREVIEW-PNG`, renderizado
pelo mesmo `tools/generate_splash.py` que produz o BMP do jogo.
Revisar o PNG e aprovar a composição antes de solicitar nova build jogável
evita recompilações caras durante iterações puramente visuais.
