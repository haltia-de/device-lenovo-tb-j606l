"""Bounded FDT structure parser for offline compiled-output policy checks."""
import struct

def fdt(blob):
    if len(blob) < 40:
        raise ValueError('Short FDT.')
    magic, total, off_struct, off_strings, off_mem, version, lastver, cpu, strings_size, struct_size = struct.unpack_from('>10I', blob)
    if magic != 0xd00dfeed or total > len(blob) or off_struct+struct_size > total or off_strings+strings_size > total:
        raise ValueError('FDT header/bounds invalid.')
    strings = blob[off_strings:off_strings+strings_size]
    p, end, stack, nodes = off_struct, off_struct+struct_size, [], {}
    while p+4 <= end:
        token = struct.unpack_from('>I', blob, p)[0]
        p += 4
        if token == 1:
            stop = blob.index(0, p, end)
            stack.append(blob[p:stop].decode())
            p = (stop+4)&~3
            path = '/'+('/'.join(stack[1:]))
            if path in nodes:
                raise ValueError('Duplicate FDT path.')
            nodes[path] = {}
        elif token == 2:
            if not stack:
                raise ValueError('FDT nesting invalid.')
            stack.pop()
        elif token == 3:
            if not stack or p+8 > end:
                raise ValueError('FDT property header invalid.')
            size, nameoff = struct.unpack_from('>2I', blob, p)
            p += 8
            if p+size > end or nameoff >= len(strings):
                raise ValueError('FDT property bounds invalid.')
            stop = strings.index(0, nameoff)
            name = strings[nameoff:stop].decode()
            props = nodes['/'+('/'.join(stack[1:]))]
            if name in props:
                raise ValueError('Duplicate FDT property.')
            props[name] = blob[p:p+size]
            p = (p+size+3)&~3
        elif token == 4:
            pass
        elif token == 9:
            if stack:
                raise ValueError('Unclosed FDT node.')
            return total, nodes
        else:
            raise ValueError('Unknown FDT token.')
    raise ValueError('FDT end token missing.')
