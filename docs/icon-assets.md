# Dusk PC — cross-platform application icon

The approved Dusk-themed icon lives in \`assets/icons/dusk-icon-master.webp\`.
It is **raster artwork** (not a vector SVG). It is stored as optimized WebP to
keep the Git repository small. Other images are **derived**, never manually edited.

Generate all platform assets using Pillow >= 10:

\`\`\`sh
python -m pip install "Pillow>=10,<13"
python tools/generate_icons.py
\`\`\`

### Platforms

- **Windows**: \`generated/windows/dusk.ico\` contains sizes 16, 24, 32, 48,
  64, 128, 256. The owner playtest workflow embeds it into the Go GUI launcher
  with MinGW \`windres\`; \`generated/windows/window-icon.bmp\` is included in the
  authenticated game package and loaded with \`SDL_SetWindowIcon\`.
- **Linux**: hicolor PNGs and an example \`.desktop\` entry. Installation of a
  real native Linux port is a separate project milestone.
- **macOS**: \`generated/macos/dusk.icns\` for a future \`.app\` bundle.
- **Android**: mdpi–xxxhdpi fallback images plus adaptive foreground,
  background and monochrome themed layer; integrate in an Android project
  when the Android port exists.

The Windows player should use the new owner playtest EXE, not the ROM-free
presentation prototype. Windows packaging never alters original ROM bytes or
player saves. Use the validated Windows EXE and check both Explorer and the
SDL3 game window's taskbar icon. The icon artwork must remain optional when
NDSRecomp is used for any other title.

### Maintenance

Edit the source artwork, regenerate everything and run the ROM-free icon tests.
An icon change should not change the original game's timing or rendering.
