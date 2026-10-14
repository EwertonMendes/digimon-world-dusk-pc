# Windows — executar jogo ou desenvolver

## Para jogar

Use o **executável privado do jogo completo**, fornecido pelo
responsável pelo projeto. Dois cliques, sem WSL/ROM externa/compilação.
O pacote v0.16 tem tela nativa SDL3, PC Options, gamepad e save de EEPROM
original. O pacote v0.17 ainda deve ser reconstruído e testado.

Os downloads da aba Actions chamados `dusk-pc-windows-presentation-prototype`
são testes de um **protótipo sintético**, não o jogo.

## Para desenvolver ou validar o código público

No Windows 10/11 x64, instale Git, CMake 3.20+ e Visual Studio C++ Build
Tools (apenas no PC de desenvolvimento):

```powershell
cmake -S . -B build -DDUSK_BUILD_TESTS=ON
cmake --build build --config Release
ctest --test-dir build -C Release --output-on-failure
```

O repositório público testa a geometria e o parsing de ROM; o jogo real
requer uma compilação privada dos bancos ARM9/ARM7 derivados, SDL3 e
ROM autenticada, descrita em [recompilation.md](recompilation.md).

## Perfis persistentes

O save oficial do cartucho fica em
`%LOCALAPPDATA%\\DuskNativePC\\userdata\\A6RE\\saves\\dusk.sav`.
Não apague ou sobrescreva manualmente; utilize as opções de backup da
build apropriada. O gamepad, PiP e demais configurações host são
independentes do save original.

Consulte [windows-oneclick.md](windows-oneclick.md).
