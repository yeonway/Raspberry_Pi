cmake_minimum_required(VERSION 3.22.1)

project(phone_ai_bridge_native LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_C_FLAGS_DEBUG "${CMAKE_C_FLAGS_DEBUG} -O3")
set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG} -O3")
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_COMMON OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_TOOLS OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_SERVER OFF CACHE BOOL "" FORCE)
set(GGML_OPENMP OFF CACHE BOOL "" FORCE)
set(GGML_LLAMAFILE OFF CACHE BOOL "" FORCE)
set(GGML_NATIVE OFF CACHE BOOL "" FORCE)

add_subdirectory(llama.cpp)

foreach(target_name llama ggml ggml-base ggml-cpu)
    if(TARGET ${target_name})
        target_compile_options(${target_name} PRIVATE -O3)
    endif()
endforeach()

add_library(phone_ai_llama SHARED llama_bridge.cpp)
target_compile_options(phone_ai_llama PRIVATE -O3)

target_include_directories(phone_ai_llama PRIVATE
        llama.cpp/include
        llama.cpp/ggml/include
)

target_link_libraries(phone_ai_llama
        llama
        android
        log
)
