# Recompilação do Digimon World Dusk (ARM original)

Última atualização: 14/10/2026. A v0.16 usa NDSRecomp fixado em
`3a57236bb23d25dcb4caad7d58d733311062ff5e` (licença PolyForm
Noncommercial 1.0.0).

## Arquitetura e limites

O runtime privado Windows executa código do jogo original ARM9/ARM7
**estaticamente recompilado para código nativo**, mantendo o fallback
Tier3 para caminhos que ainda não possuem geração AOT comprovadamente segura.
Não se devem substituir batalhas, menus ou a campanha por implementações
manuais de alto nível.

O despacho nativo de overlay depende de (CPU ARM9/ARM7, modo ARM/Thumb,
endereço, geração e bytes verificados no momento da execução).
Nunca misture páginas diferentes apenas porque compartilham um endereço RAM.

## Montagem do upstream e integração

1. Faça checkout do NDSRecomp na revisão fixada, com submódulos.
2. Execute a integração **determinística** em checkout novo:

```sh
python tools/apply_dusk_patches.py --upstream upstream --component desktop
```

O script valida a revisão upstream e aplica cada patch na ordem contratada
pelos testes públicos. Ele **não remove a dívida técnica de alterações
sucessivas em frontend.cpp**; a refatoração completa do frontend específico
Dusk depende de compilação e equivalência demonstrada no runner privado.

## Cobertura privada v0.16

Arquivos fornecidos pelo proprietário (quatro sessões, Oct 13–14):

- `game-coverage-*.json`: capturas RAM de código, com blocos de 4KiB,
  SHA1 e raízes ARM/Thumb; contém **bytes derivados do jogo**.
- `performance-*.jsonl`: contadores Tier3, FPS por segundo, underruns
  e tempos do runtime.
- `hostprof-*.ndshp`: amostras binárias do host e cabeçalhos com caminhos
  locais. **Jamais publicar arquivos brutos**.

Para produzir um relatório **sem bytes de código nem caminhos pessoais**:

```sh
python tools/analyze_v016_sessions.py \
  --perf PRIVATE/performance-*.jsonl \
  --coverage PRIVATE/game-coverage-*.json \
  --hostprof PRIVATE/hostprof-*.ndshp \
  --out PRIVATE/v016-safe-report.json
```

Para consolidar gerações de código idênticas sem misturar overlays:

```sh
python tools/merge_verified_profiles.py PRIVATE/game-coverage-*.json \
  --out PRIVATE/v017-merged-coverage.json
```

A união dos bitmaps `root_arm/root_thumb` ocorre **apenas se CPU, endereço
e SHA1 dos 4096 bytes forem idênticos**. Somente o endereço de raiz não
identifica a geração. O relatório derivado em
[research/2026-10-14-v016-owner-sessions-safe.md](research/2026-10-14-v016-owner-sessions-safe.md)
registra 197 gerações únicas, 173 pares CPU/endereço e 16 pares com versões
diferentes de bytes.

## Promoção AOT e validação

1. Identificar os spans Tier3 realmente executados, com `promote_tier3_spans.py`.
2. Associar cada root a uma geração RAM capturada e ao banco original extraído
   da ROM privada, **comparando o conteúdo byte a byte**.
3. Verificar overlays elegíveis com `refresh_shipped_overlays.py`;
   overlays não observados/validados permanecem como pendência.
4. Executar o compilador pinado para gerar novos bancos privados.
5. Usar o despacho com `--validate-live-bytes` nos bancos produzidos.
6. Comparar crescimento do despacho baseline/candidato
   (`verified_dispatch_rows.py`) e testar novamente as rotas curtas
   disponíveis sem alterar a velocidade DS (~59,826 Hz).
7. Comparar FPS, tempo de CPU/Tier3 e audio underruns **no mesmo cenário**.
   Só promova uma melhoria com evidência, sem perda de comportamento.

**Não é possível reconstruir o runner privado completo somente a partir dos
JSONs de cobertura:** é necessária a ROM original, o conjunto de bancos
privados já validados, o compilador NDSRecomp e as dependências de runtime.
O CI público não possui esses arquivos, intencionalmente.

## Empacotamento

O jogo final para testes Windows precisa ser
`tools/pack_native_private.py` + launcher Go + runner Windows ARM
recompilado + SDL3 + ROM validada, resultando em EXE de um clique.
A apresentação GDI pública **não é uma build do jogo**.
Veja [windows-oneclick.md](windows-oneclick.md).
