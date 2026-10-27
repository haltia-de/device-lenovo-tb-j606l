#!/usr/bin/env python3
"""Give a DTB dummy targets for every label the stock Lenovo DTBO fixes up.

ABL applies the stock overlay to whatever base DTB it boots. Mainline DTBs
carry no __symbols__, so the overlay fails and ABL refuses to boot. This adds
/haltia-overlay-sink with one empty child per label and a __symbols__ node
that points only at those children: the overlay lands there and the real
nodes stay untouched."""
import subprocess, sys
dtc, src, labels, dst = sys.argv[1:5]
dts = subprocess.run([dtc, '-q', '-I', 'dtb', '-O', 'dts', src], capture_output=True, text=True, check=True).stdout
names = [l.strip() for l in open(labels) if l.strip()]
sink = '\thaltia-overlay-sink {\n\t\tstatus = "disabled";\n' + ''.join(f'\t\t{n} {{ }};\n' for n in names) + '\t};\n'
syms = '\t__symbols__ {\n' + ''.join(f'\t\t{n} = "/haltia-overlay-sink/{n}";\n' for n in names) + '\t};\n'
i = dts.rindex('};')
dts = dts[:i] + sink + syms + dts[i:]
subprocess.run([dtc, '-q', '-I', 'dts', '-O', 'dtb', '-o', dst, '-'], input=dts, text=True, check=True)
