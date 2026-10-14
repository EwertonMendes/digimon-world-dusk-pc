# Roadmap — status confirmado (14/10/2026)

## Base v0.16 (privada, testada pelo proprietário)

- [x] Execução Windows x64 do jogo original recompilado e SDL3.
- [x] Focus + PiP, modo fullscreen, troca de telas, PC Options no host,
  mapeamento touchscreen e suporte inicial a gamepad.
- [x] EEPROM 64KiB original no perfil estável A6RE, sem save states.
- [x] Cobertura AOT parcialmente validada, incluindo sete overlays ARM9.
- [ ] Finalização de toda a campanha comprovada automaticamente (adiada
  a pedido do proprietário, que segue jogando normalmente).
- [ ] Eliminar picos observados de FPS/áudio e cobrir caminhos Tier3 restantes.

## v0.17 — em implementação na PR #17

- [x] Análise inicial dos quatro perfis de gameplay da v0.16: cerca de
  73 minutos de amostras, 222 underruns, 197 gerações distintas,
  16 pares CPU/endereço com gerações diferentes.
- [x] Correção da união dos bitmaps ARM/Thumb quando CPU/endereço/SHA1
  da página são idênticos, com teste de regressão ROM-free.
- [x] Ferramenta local para relatórios agregados sem vazar bytes do jogo.
- [x] Código de retenção de 20 backups distintos, restauração protegida
  e recuperação após interrupção (sob revisão e validação CI).
- [x] Gerenciador inicial de backups no launcher Windows via opção dedicada
  (sob revisão; ainda não integrado ao overlay PC Options).
- [x] Atualização dos documentos principais para o estado real.
- [ ] Recompilar bancos AOT privados com as quatro capturas novas e validar
  delta contra o banco v0.16; exige ROM local e toolchain privada.
- [ ] Investigar a origem dos 204 underruns da sessão 23:56 e os picos
  de frametime, usando símbolos e amostras privadas.
- [ ] Modularização completa do `frontend.cpp` NDSRecomp e remoção segura
  de patches sequenciais, sem regressão do runner real.
- [ ] PC Options: remapeamento abrangente, mixer, acessibilidade e pausa
  segura que preserve relógios e áudio do DS.
- [ ] Empacotar e testar um novo executável privado de um clique com runner
  recompilado v0.17; nenhum pacote final está no CI público.

## Posterior

- Linux/Steam Deck, macOS, Android, iOS apenas após base de runtime
  portátil e verificação real de builds por plataforma.
- Maior cobertura de gameplay baseada em uso real, sem impor campanha
  de QA ao proprietário.

Os jobs públicos validam ferramentas, launcher e geometria sem ROM.
Eles **não** equivalem a jogar a campanha nem fornecem um EXE real do jogo.
