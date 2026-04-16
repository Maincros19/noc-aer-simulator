cmake_minimum_required(VERSION 3.15)
project(NoCAERSimulatorC VERSION 1.0)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

# Directorio de las fuentes
set(SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/src)

# Archivos fuente
file(GLOB_RECURSE CORE_SOURCES
    "${SOURCE_DIR}/*.cpp"
)
list(REMOVE_ITEM CORE_SOURCES "${SOURCE_DIR}/pybind_interface.cpp")


# Incluir directorios
include_directories(${SOURCE_DIR})
find_package(Python 3.11 COMPONENTS Interpreter Development REQUIRED)
include_directories(${Python_INCLUDE_DIRS})


# Añadir la librería del simulador
add_library(noc_simulator_core STATIC ${CORE_SOURCES})
set_target_properties(noc_simulator_core PROPERTIES POSITION_INDEPENDENT_CODE ON)
target_include_directories(noc_simulator_core PRIVATE ${pybind11_INCLUDE_DIRS})

# Configurar pybind11
find_package(pybind11 CONFIG REQUIRED)
pybind11_add_module(noc_simulator_pybind src/pybind_interface.cpp)
target_include_directories(noc_simulator_pybind PRIVATE ${pybind11_INCLUDE_DIRS})

target_link_libraries(noc_simulator_pybind PRIVATE noc_simulator_core pybind11::embed)
