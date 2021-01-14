from __future__ import annotations

import re


def replace_type(item: dict, line) -> tuple[bytes, dict]:
    """
    Perform the type replacement for a line.
    """
    new_annotation = bytes(item['new_annotation'], encoding='utf-8')
    pattern = b'[^a-zA-Z](' + item['annotation'].encode(encoding='utf-8') + b')[^a-zA-Z]'
    match = re.search(pattern, line)
    line = line[: match.start(1)] + line[match.end(1) :]
    line = line[: match.start(1)] + new_annotation + line[match.start(1) :]
    return line


def fix_file(
    filename: str, futures: bool, native_types: list, imported_types: list, imports_to_delete: list
) -> None:
    """
    Changes the file's content and writes back to it.
    """
    with open(filename, mode='rb+') as file:
        content = file.readlines()

    for item in native_types:
        # New native types don't require us to do anything except
        # inplace replace the old values with the new
        content[item['line_number'] - 1] = replace_type(item, content[item['line_number'] - 1])

    new_import_statements: list[bytes] = []

    for item in imported_types:
        # These types require us to add a new import statement at the top of
        # the file in addition to the inplace replacement
        content[item['line_number'] - 1] = replace_type(item, content[item['line_number'] - 1])
        new_import_statements.append(
            f'from {item["import_from"]} import {item["new_annotation"]}\n'.encode(encoding='utf-8')
        )

    # Filter out repeated imports
    new_import_statements = list(set(new_import_statements))
    if futures:
        new_import_statements.insert(0, b'from __future__ import annotations\n\n')

    # Remove old imports
    for operation in imports_to_delete:
        ann, start, stop = operation['annotation'], operation['line_start'], operation['line_stop']
        counter = 0
        for line in content[start:stop]:
            if re.findall(f'[^a-zA-Z]{ann}[^a-zA-Z]'.encode(encoding='utf-8'), line):
                content = content[: start + counter] + content[start + counter + 1 :]
                break
            counter += 1
        else:
            Exception(f'Unable to find {ann}')

    content = new_import_statements + content
    with open(filename, 'wb') as file:
        file.writelines(content)


def map_imports_to_delete(new_imports: list[list], imports: dict):
    """
    This function handles creating a list of executable operations for deleting
    typing imports from the file we're handling.
    """
    operations = []
    counter = 0
    for _list in new_imports:
        for item in _list:
            if item['annotation'] in imports['names']:
                operations.append(
                    {
                        'annotation': item['annotation'],
                        'line_start': imports['lineno'],
                        'line_stop': imports['end_lineno'],
                    }
                )
                imports['end_lineno'] -= 1
                imports['names'].remove(item['annotation'])
                counter += 1
                continue
    return operations