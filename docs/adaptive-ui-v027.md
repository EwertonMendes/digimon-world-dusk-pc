# Dusk Material UI v0.28 — revisão após teste visual

A v0.27 foi rejeitada pelo teste visual: utilizava `SDL_RenderDebugText`,
rotulagem de fonte bitmap, valores recortados e painéis pouco adequados ao toque.

## Nova camada

- O compositor SDL3 agora chama `dusk_material::panel/pip/corner`.
- `dusk_font_atlas.hpp`: cobertura antialias pré-rasterizada de
  **Inter Display Regular/Semibold**, 64 px, compactada e renderizada em
  textura GPU; sem SDL_ttf, font fallback do sistema ou fontes raster
  de depuração. A fonte Inter é distribuída sob **SIL Open Font License 1.1**;
  a versão deste projeto contém os glifos renderizados, não o arquivo de fonte.
- `dusk_ui_font.hpp`: medidas proporcionais, interpolação linear,
  reticências para textos longos e coloração por estado; a textura é criada
  somente uma vez para cada renderer SDL.
- `dusk_material_renderer.hpp`: componentes arredondados, paleta
  índigo/violeta Dusk, acentos ciano, cartões de layouts, cabeçalhos, abas,
  seleção evidente, legenda dos controles, rolagem isolada e limites
  exatos de desenho. Não confundir a aparência do menu com a pixel art do jogo.
- `dusk_modern_ui.hpp`: layout com dimensionamento em escala lógica,
  3 colunas no desktop, 2 colunas onde couberem no mobile, rolagem
  por toque e teclado/controle. No gameplay, a tela inferior do DS continua
  utilizando o mesmo mapeamento de toque original.

## Compilação

O fluxo completo v0.27 falhou em restaurar o cache de objetos. A v0.28
usa chaves estáveis por branch com fallback para o cache antigo. O próprio
ccache valida os conteúdos de fontes, includes, flags e toolchain; uma
mudança de UI não implica recompilar todas as unidades de ARM.

O cache atualizado é salvo **imediatamente após** o runner compilar,
mesmo quando uma etapa posterior de empacotamento tiver problemas.
Não há cache de ROM, dados pessoais ou saves.

O CI ROM-free compila o renderer/material/font atlas isoladamente via
`tests/material_ui_smoke.cpp`, evitando esperar por todo o NDSRecomp
para descobrir erros sintáticos no menu.

Nenhuma alteração no scheduler, ROM, áudio ou save.
O Windows ainda depende de build real para validar a integração. A futura
interface Android compartilhará os controles SDL3, mas uma versão APK não
é considerada testada até termos um runner Android funcional.
