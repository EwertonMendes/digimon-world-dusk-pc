# Ícones do Digimon World Dusk PC

A arte aprovada está em `assets/icons/dusk-icon-master.webp`. Ela é uma
imagem raster, não um SVG vetorial. A versão de origem possui um fundo preto
apenas nos cantos arredondados. O gerador remove **somente o matte externo**
e preserva todos os detalhes escuros internos.

O único fluxo oficial para exportar ícones é:

```sh
python -m pip install "Pillow==11.3.0"
python tools/generate_icons.py
python -m unittest discover -s tests -p test_icon_assets.py -v
```

A imagem de saída `assets/icons/generated/dusk-icon-transparent.png` tem canal
alfa verdadeiro. Todos os formatos são derivados dela e jamais devem
receber manualmente um fundo preto ou branco.

## Arquivos por plataforma

- **Windows:** `windows/dusk.ico` contém 16, 24, 32, 48, 64, 128 e 256 px
  com transparência real. O GitHub Actions compila o ICO como recurso Win32
  no launcher Go usando `windres`.
- **Janela SDL3:** `windows/window-icon.rgba` contém exatamente 128 × 128 × 4
  bytes RGBA32; o launcher verifica e instala o recurso no pacote autenticado,
  e o runtime nativo cria a superfície com `SDL_CreateSurfaceFrom` e aplica
  `SDL_SetWindowIcon`. Não requer SDL_image e não descarta o canal alfa.
- **Linux:** PNGs hicolor de 16 a 512 px e exemplo `.desktop`.
- **macOS:** `macos/dusk.icns` para um futuro bundle `.app`.
- **Android:** PNGs mdpi–xxxhdpi e camadas adaptativas de primeiro plano,
  fundo e monochrome/themed icon.

Linux, macOS e Android possuem recursos prontos, mas **não** builds do jogo
nessas plataformas. A integração ficará para os respectivos ports.

## Validação de versão Windows

A compilação privada v0.23 deve usar o workflow
`dusk-native-windows-playtest.yml`, nunca o protótipo ROM-free. Verificar:

1. ICO correto no Explorador de Arquivos, atalhos e na barra de tarefas.
2. Cantos transparentes no ícone da **janela do jogo**, não somente no launcher.
3. O arquivo `--verify-bundle` e os saves EEPROM mantêm o comportamento anterior.

Os testes automáticos validam o alfa nos formatos ICO, PNG, ICNS e no
recurso RGBA32. Não dependemos de aplicações externas de manipulação de
imagem na máquina do jogador.
