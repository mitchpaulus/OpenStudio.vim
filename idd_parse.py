import sys
import re

class TokenTypes:
    GROUP = 1
    OBJECT_TYPE = 2
    OBJECT_FIELD = 3
    OBJECT_FIELD_PROP = 4
    EOF = 5
    COMMENT = 6
    BLANK = 7

class Tokenizer:
    def __init__(self, lines) -> None:
        self.lines = lines
        self.idx = 0
        self.tokens = []
        self.token_index = 0

    def tokenize(self):
        while True:
            token = self.next()
            self.tokens.append(token)
            if token[0] == TokenTypes.EOF:
                break

    def token_type(self, line_input):
        line = line_input.strip()
        if not line:
            return TokenTypes.BLANK
        elif line.startswith("\\group"):
            return TokenTypes.GROUP
        elif line.startswith("\\"):
            return TokenTypes.OBJECT_FIELD_PROP
        elif re.match("[AN]\\d+ *[,;]", line):
            return TokenTypes.OBJECT_FIELD
        elif line.endswith(','):
            return TokenTypes.OBJECT_TYPE
        elif line.startswith('!'):
            return TokenTypes.COMMENT
        else:
            raise Exception(f'Unknown token type for line: {line}')

    def next(self):
        if self.idx >= len(self.lines):
            token = (TokenTypes.EOF, "")
            return token

        line = self.lines[self.idx].strip()
        token_type = self.token_type(line)

        # Ignore comments/blanks
        if token_type == TokenTypes.COMMENT or token_type == TokenTypes.BLANK:
            self.idx += 1
            return self.next()

        token = (token_type, line)
        self.idx += 1
        return token

    def print_tokens(self):
        for token in self.tokens:
            print(token)

    def consume(self):
        if self.token_index >= len(self.tokens):
            raise Exception('No more tokens to consume')

        token = self.tokens[self.token_index]
        self.token_index += 1
        return token

    def peek(self, n=0):
        if self.token_index + n >= len(self.tokens):
            return self.tokens[-1]

        return self.tokens[self.token_index + n]

class Parser:
    def __init__(self, tokenizer) -> None:
        self.tokenizer = tokenizer

    def match(self, expected: int) -> tuple[int, str]:
        token = self.tokenizer.consume()
        if token[0] != expected:
            raise Exception(f'Expected {expected} but got {token[0]}: {token[1]}')
        return token

    def parse_file(self) -> list['IddGroup']:
        idd_groups = []

        while self.tokenizer.peek()[0] != TokenTypes.EOF:
            idd_group = self.parse_group()
            idd_groups.append(idd_group)

        return idd_groups

    def parse_group(self):
        group = self.match(TokenTypes.GROUP)

        idd_objects = []
        while self.tokenizer.peek()[0] != TokenTypes.GROUP and self.tokenizer.peek()[0] != TokenTypes.EOF:
            idd_obj = self.parse_object()
            idd_objects.append(idd_obj)

        return IddGroup(group, idd_objects)

    def parse_object(self):
        object_type_token = self.match(TokenTypes.OBJECT_TYPE)
        object_type_name = object_type_token[1].split(',')[0].strip()

        object_fields = []
        object_type_props = []

        while self.tokenizer.peek()[0] == TokenTypes.OBJECT_FIELD_PROP:
            object_type_props.append(self.match(TokenTypes.OBJECT_FIELD_PROP))

        while self.tokenizer.peek()[0] == TokenTypes.OBJECT_FIELD:
            field_header = self.match(TokenTypes.OBJECT_FIELD)
            field_props = []

            while self.tokenizer.peek()[0] == TokenTypes.OBJECT_FIELD_PROP:
                field_props.append(self.match(TokenTypes.OBJECT_FIELD_PROP)[1])

            idd_field = IddField(field_header[1], field_props)

            object_fields.append(idd_field)

        return IddObject(object_type_name, object_fields, object_type_props)


class IddGroup:
    def __init__(self, group_name, group_objects: list['IddObject']) -> None:
        self.group_name = group_name
        self.group_objects = group_objects

    def __str__(self) -> str:
        lines = []
        lines.append(f'Group: {self.group_name}')
        for obj in self.group_objects:
            lines.append(str(obj))
        return '\n'.join(lines)

    def __repr__(self) -> str:
        return self.__str__()


class IddObject:
    def __init__(self, object_type: str, object_fields: list['IddField'], object_type_props: list[str]) -> None:
        self.object_type = object_type
        self.object_fields = object_fields
        self.object_type_props = object_type_props

    def __str__(self) -> str:
        lines = []
        lines.append(f'Object Type: {self.object_type}')
        for field in self.object_fields:
            lines.append(str(field))

        return '\n'.join(lines)

    def obj_name(self):
        return self.object_type.split(',')[0].strip()

    def __repr__(self) -> str:
        return self.__str__()


class IddField:
    def __init__(self, field_header: str, field_props: list[str]) -> None:
        self.field_header = field_header
        self.field_props = field_props

    def __str__(self) -> str:
        lines = []
        lines.append(f'Field: {self.field_header}')
        for prop in self.field_props:
            lines.append(f'  {prop}')
        return '\n'.join(lines)

    def __repr__(self) -> str:
        return self.__str__()


def main():
    # idd_contents = sys.stdin.read().splitlines()
    with open('os.idd', encoding='utf-8') as file:
        idd_contents = file.read().splitlines()

    tokenizer = Tokenizer(idd_contents)
    tokenizer.tokenize()
    # tokenizer.print_tokens()
    parser = Parser(tokenizer)
    idd_groups = parser.parse_file()

    reference_map = {} # Mapping from reference key to list of objects
    obj_list_map = {} # Mapping from object to list of references

    for group in idd_groups:
        for obj in group.group_objects:
            for field in obj.object_fields:
                for prop in field.field_props:
                    if prop.startswith('\\reference'):
                        ref = prop.split()[1]
                        reference_map.setdefault(ref, []).append(obj.obj_name())
                    elif prop.startswith('\\object-list'):
                        ref = prop.split()[1]
                        obj_list_map.setdefault(obj.obj_name(), []).append(ref)

    all_references = set()
    for refs in reference_map.keys():
        all_references.update(refs)
    for refs in obj_list_map.values():
        all_references.update(refs)

    reference_dot_decl = []
    for ref in all_references:
        reference_dot_decl.append(f'{ref.replace(":", "").replace("-", "")} [label="{ref}"]')

    pointers = set()
    obj_declarations = set()
    for obj_name, refs in obj_list_map.items():
        # Print as dot format
        obj_decl = f'{obj_name.replace(":", "").replace("-", "")} [shape=box, label="{obj_name}"]'
        obj_declarations.add(obj_decl)
        for ref in refs:
            paired_objs = reference_map.get(ref, [])
            for paired_obj in paired_objs:
                line = f'{obj_name.replace(":", "").replace("-", "")} -> {paired_obj.replace(":", "").replace("-", "")}'
                pointers.add(line)

    print('digraph G {')
    print('  rankdir=LR;')
    for obj_decl in obj_declarations:
        print(f'  {obj_decl};')
    for pointer in pointers:
        print(f'  {pointer};')
    print('}')


if __name__ == "__main__":
    main()
