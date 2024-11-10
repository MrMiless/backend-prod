import os
import subprocess

def compile_code(source_code, source_file, executable, compiler, dialect):
    try:
        with open(source_file, 'w') as file:
            file.write(source_code)

        gcc_command = [compiler, dialect, '-ggdb', '-O0', '-fno-omit-frame-pointer', '-o', executable, 'main.cpp']
        compilation_result = subprocess.run(gcc_command, 
                                            capture_output=True, 
                                            text=True)
    finally:
        if os.path.exists(source_file):
            os.remove(source_file)

    return compilation_result
    