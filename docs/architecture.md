# Architecture — phase 1

```
      user-supplied local .nds (never uploaded)
                    |
              dusk_rom_info
       metadata / checksum / optional private extraction
                    |
            future Dusk bank generator
                    |
        NDSRecomp runtime integration (NOT DONE)
                    |
            frame/audio/input adapter
                    |
   core layout & input mapping -> Win32 presentation layer
```

`include/dusk/Rom.hpp` and `src/Rom.cpp` validate DS headers, static code segments, FAT entries and overlay locations. `Layout` computes non-distorted rectangles for five modes. `screenToTouch` performs deterministic coordinate mapping; actual DS routing and touchscreen event dispatch are not implemented. `Config` manages per-user UI preferences. `apps/win32_main.cpp` uses Win32/GDI as a dependency-free presentation baseline. A future renderer abstraction could add SDL3 or GPU acceleration without changing layout math.

There is **no DS runtime or execution** inside this source tree yet. Do not confuse frame composition with game emulation or native recompilation.
