# Windows x64 — pacote privado de um clique (v0.16 / v0.17)

## Jogador: sem preparação nem compilação

O executável de jogo completo é criado **em ambiente privado** com o runner
NDSRecomp ARM9/ARM7 recompilado, a ROM de Dusk verificada e SDL3. Basta dar
dois cliques. Não é necessário abrir navegador, instalar WSL, instalar
ferramentas de desenvolvimento nem selecionar uma ROM externa.

O executável público `dusk_pc.exe` produzido pelo CMake/CI **é apenas
uma demonstração de apresentação**, não o jogo verdadeiro.

## Instalador e persistência

- v0.16 já possui uma build privada Windows x64 testada pelo jogador.
- v0.17 está em desenvolvimento na PR #17. Mudanças no launcher não produzem
  automaticamente uma build nova do runner ARM com as mesmas alterações.
- Cada nova versão instala o runtime em
  `%LOCALAPPDATA%\\DuskNativePC\\v0.XX`.
- O **save original de 64 KiB** permanece em
  `%LOCALAPPDATA%\\DuskNativePC\\userdata\\A6RE\\saves\\dusk.sav`.
- Identidade de firmware, dados pessoais e backups ficam no perfil estável
  `userdata/A6RE`, não no diretório do executável.
- O launcher verifica assinatura SHA-256 do arquivo zip incorporado e a
  variante correta do jogo, recusando pacotes incompatíveis.

### Novos backups v0.17

O launcher evita backups idênticos em aberturas repetidas, mantém 20 versões
automáticas distintas e recusa restaurações cujo hash ou tamanho de EEPROM
esteja incorreto. O processo exige exclusividade de acesso ao perfil.

O comando `Digimon-Dusk-PC-Windows-v0.17.exe --manage-saves` abre um
pequeno diálogo nativo Windows para restaurar o backup **mais recente** ou
abrir a pasta com backups antigos. Isso **ainda não é uma tela integrada
ao PC Options** e só estará disponível após empacotamento privado v0.17.

## Criar pacote privado (máquina de desenvolvimento)

O repositório público contém o empacotador, mas **não** a ROM, arquivos
ARM derivados ou o runtime Windows completo. Exemplo:

```sh
python tools/pack_native_private.py \
  --launcher /private/launcher-v017.exe \
  --runner /private/runner.exe \
  --sdl /private/SDL3.dll \
  --rom /private/game.nds \
  --output /private/Digimon-Dusk-PC-Windows-v0.17.exe \
  --baseline-dispatch /private/v016_dispatch \
  --candidate-dispatch /private/v017_dispatch
```

O empacotador valida ROM, formato de executáveis, dependência de SDL3 e
integridade do despacho se fornecidos os dois diretórios. A geração AOT
exige acesso à ROM original e aos bancos validados da build anterior.

**Não** anexar ROM, jogo empacotado, código gerado ou saves ao workflow
público por padrão. Direitos do jogo original e a PolyForm Noncommercial
1.0.0 do NDSRecomp são obrigações independentes.

## Controles

Consultar [PC Options v0.16](native-immersive-ui-v016.md).
`Esc/F10` abre o menu do host; `F11` alterna fullscreen; teclado,
mouse e gamepad controlam o jogo, incluindo touchscreen virtual e PiP.

## Erros

Consultar [resolução de problemas](troubleshooting.md) e os diagnósticos
sob a pasta de instalação versionada em `%LOCALAPPDATA%`.
