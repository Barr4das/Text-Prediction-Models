#!/usr/bin/env bash

set -euo pipefail

# Verificação dos argumentos da função
if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <source_dir> <target_dir>" >&2
    exit 1
fi

SOURCE_DIR="$1"
TARGET_DIR="$2"

# Verificação das ferramentas necessárias
for cmd in ebook-convert pdftotext; do
    if ! command -v "$cmd" >/dev/null; then
        echo "Missing command '$cmd'." >&2
        exit 1
    fi
done

# Verificação da pasta de origem
if [[ ! -d "$SOURCE_DIR" ]]; then
    echo "Directory '$SOURCE_DIR' not found." >&2
    exit 1
fi

mkdir -p "$TARGET_DIR"

# Iteração sobre os conteúdos da pasta de origem (incluindo subpastas, como ocr/) e conversão
while IFS= read -r -d '' book; do
    name="$(basename "$book")"
    title="${name%.*}"
    extension="${name##*.}"
    relative_dir="$(dirname "${book#"$SOURCE_DIR"/}")"
    mkdir -p "$TARGET_DIR/$relative_dir"
    target="$TARGET_DIR/$relative_dir/$title.txt"

    case "${extension,,}" in
        epub|mobi) ok=$(ebook-convert "$book" "$target" --txt-output-encoding utf-8 >/dev/null 2>&1 && echo 1 || echo 0) ;;
        pdf) ok=$(pdftotext -enc UTF-8 "$book" "$target" 2>/dev/null && echo 1 || echo 0) ;;
        *) echo "SKIPPED  $name"; continue ;;
    esac

    if [[ "$ok" == 1 ]]; then echo "OK $name"; else echo "ERROR $name"; fi
done < <(find "$SOURCE_DIR" -type f -print0 | sort -z)
