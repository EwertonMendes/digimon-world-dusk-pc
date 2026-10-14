cmake_minimum_required(VERSION 3.20)
project(DigimonWorldDuskRecompiled VERSION 0.24.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(DUSK_BUILD_TESTS "Build unit tests" ON)

add_library(dusk_core STATIC
  src/Rom.cpp
  src/Layout.cpp
  src/Config.cpp
)
target_include_directories(dusk_core PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/include")
if(MSVC)
  target_compile_options(dusk_core PRIVATE /W4 /permissive-)
else()
  target_compile_options(dusk_core PRIVATE -Wall -Wextra -Wpedantic -Wconversion)
endif()

add_executable(dusk_rom_info apps/rom_info.cpp)
target_link_libraries(dusk_rom_info PRIVATE dusk_core)

if(WIN32)
  add_executable(dusk_pc WIN32 apps/win32_main.cpp)
  target_link_libraries(dusk_pc PRIVATE dusk_core user32 gdi32 shell32)
  set_target_properties(dusk_pc PROPERTIES OUTPUT_NAME "Digimon-World-Dusk-Recompiled-v0.24-PRESENTATION-PROTOTYPE")
  target_compile_definitions(dusk_pc PRIVATE UNICODE _UNICODE WIN32_LEAN_AND_MEAN NOMINMAX)
endif()

if(DUSK_BUILD_TESTS)
  include(CTest)
  add_executable(dusk_tests tests/core_tests.cpp)
  target_link_libraries(dusk_tests PRIVATE dusk_core)
  add_test(NAME dusk_core_tests COMMAND dusk_tests)
endif()
