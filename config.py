import os

class Config:
    TIMEOUT_SECONDS = 5

    SOURCE_FILE = 'main.cpp'
    EXECUTABLE = 'main'

    CXX = 'g++'
    DIALECT = '-std=c++11'

    SUCCESS = 0
    COMPILATION_ERROR = 1
    RUNTIME_ERROR = 2
    TIME_LIMIT_EXCEEDED = 3

    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB limit
    VALID_FILE_EXTENSIONS = ['.cpp', '.txt']

    SNIPPET_FILES_DIR = 'app/cpp_snippets/'
    SNIPPET_FILES = {
    }
    