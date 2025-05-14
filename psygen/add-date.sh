#!/bin/bash

# Normalize function to handle weird characters and formatting
normalize() {
    echo "$1" | \
    sed -e "s/[’‘]/'/g" \
        -e "s/[“”]/\"/g" \
        -e "s/[：﹕]/:/g" \
        -e "s/[｜¦|]/|/g" \
        -e "s#[⧸／/]# - #g" \
        -e "s/[—–‐‑]/-/g" \
        -e "s/[？﹖]/?/g" \
        -e "s/[＊*]/-/g" \
        -e "s/[＂\"]/\"/g" \
        -e "s/　/ /g" \
        -e "s/[ ]/ /g" \
        -e "s/ \+/ /g" \
        -e "s/^ *//" \
        -e "s/ *$//" | \
    iconv -f UTF-8 -t ASCII//TRANSLIT 2>/dev/null | \
    tr -cd '[:alnum:] \n|:/?.'"'"'-_()[]{}' | \
    tr -s ' '
}

declare -A title_to_date

# Step 1: Build mapping from normalized title → date
while IFS= read -r line; do
    [[ "$line" =~ ^([0-9]{4}-[0-9]{2}-[0-9]{2})[[:space:]]*\|[[:space:]]*(.*)$ ]] || continue
    date="${BASH_REMATCH[1]}"
    title="${BASH_REMATCH[2]}"
    norm_title="$(normalize "$title")"
    title_to_date["$norm_title"]="$date"
done < full_list.txt

# Step 2: Loop over actual files
for file in *; do
    [[ -f "$file" ]] || continue

    # Skip files that already start with a date
    if [[ "$file" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}\ \| ]]; then
        continue
    fi

    base="${file%.txt}"
    ext="${file##*.}"
    norm_file="$(normalize "$base")"

    match_date="${title_to_date["$norm_file"]}"

    if [[ -n "$match_date" ]]; then
        new_name="$match_date | $base.txt"
        echo "Renaming: $file → $new_name"
        mv -i -- "$file" "$new_name"
    else
        echo "No match found for: $file"
    fi
done

