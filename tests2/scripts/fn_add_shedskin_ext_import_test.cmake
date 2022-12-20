
function(add_shedskin_test sys_modules)

    get_filename_component(name ${CMAKE_CURRENT_SOURCE_DIR} NAME_WLE)

    set(PYEXT ${name})
    set(basename_py "${PYEXT}.py")

    set(translated_files
        ${PROJECT_BINARY_DIR}/${PYEXT}.cpp
        ${PROJECT_BINARY_DIR}/${PYEXT}.hpp
    )

    add_custom_command(OUTPUT ${translated_files}
        COMMAND shedskin --nomakefile -o ../build -e "${basename_py}"
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
        DEPENDS "${basename_py}"
        COMMENT "translating ${basename_py}"
        VERBATIM
    )

    add_custom_target(shedskin_ext_import_${PYEXT} DEPENDS ${translated_files})

    list(PREPEND sys_modules builtin)

    foreach(mod ${sys_modules})
        # special case os and os.path
        if(mod STREQUAL "os")
            list(APPEND module_list "${SHEDSKIN_LIB}/os/__init__.cpp")
            list(APPEND module_list "${SHEDSKIN_LIB}/os/__init__.hpp")            
        elseif(mod STREQUAL "os.path")
            list(APPEND module_list "${SHEDSKIN_LIB}/os/path.cpp")
            list(APPEND module_list "${SHEDSKIN_LIB}/os/path.hpp")
        else()
            list(APPEND module_list "${SHEDSKIN_LIB}/${mod}.cpp")
            list(APPEND module_list "${SHEDSKIN_LIB}/${mod}.hpp")
        endif()
    endforeach()

    if(ARGV1)
        set(app_modules ${ARGV0})
    else()
        set(app_modules)
    endif()
    foreach(mod ${app_modules})
        list(APPEND app_module_list "${PROJECT_BINARY_DIR}/${mod}.cpp")
        list(APPEND app_module_list "${PROJECT_BINARY_DIR}/${mod}.hpp")            
    endforeach()

    if(DEBUG)
        message("-------------------------------------------------------------")
        message("name:" ${name})
        foreach(mod ${app_module_list})
            get_filename_component(mod_name ${mod} NAME)
            message("app_module: ${mod_name}") 
        endforeach()
        foreach(mod ${sys_module_list})
            get_filename_component(mod_name ${mod} NAME)
            message("sys_module: ${mod_name}") 
        endforeach()
    endif()

    add_library(${PYEXT} MODULE
        ${PROJECT_BINARY_DIR}/${PYEXT}.cpp
        ${PROJECT_BINARY_DIR}/${PYEXT}.hpp
        ${app_module_list}        
        ${sys_module_list}
    )

    set_target_properties(${PYEXT} PROPERTIES
        PREFIX ""
    )


    target_include_directories(${PYEXT} PUBLIC
        ${Python_INCLUDE_DIRS}    
        /usr/local/include
        ${SHEDSKIN_LIB}
        ${CMAKE_SOURCE_DIR}
    )

    target_compile_options(${PYEXT} PUBLIC
        "-fPIC"
        "-D__SS_BIND"
        "-Wno-unused-result"
        "-Wsign-compare"
        "-Wunreachable-code"
        "-DNDEBUG"
        "-g"
        "-fwrapv"
        "-O3"
        "-Wall"
    )


    target_link_options(${PYEXT} PUBLIC
        "-undefined"
        "dynamic_lookup"
        "-Wno-unused-result"
        "-Wsign-compare"
        "-Wunreachable-code"
        "-fno-common"
        "-dynamic"
    )

    target_link_libraries(${PYEXT} PUBLIC
        "-lgc"
        "-lgccpp"
        "-lpcre"
    )

    add_test(NAME ${PYEXT} 
             COMMAND ${Python_EXECUTABLE} -c "import ${PYEXT}; ${PYEXT}.test_all()")

endfunction()
