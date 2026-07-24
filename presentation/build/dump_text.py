import re
import zipfile

z = zipfile.ZipFile(r"D:\Domain Appliucation Project\presentation\DublinBikes_Presentation.pptx")
slides = sorted([n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)],
                key=lambda n: int(re.search(r"\d+", n).group()))
print(f"{len(slides)} slides")
for n in slides:
    xml = z.read(n).decode("utf-8")
    texts = re.findall(r"<a:t>([^<]*)</a:t>", xml)
    print(f"\n=== {n} ===")
    print(" | ".join(t for t in texts if t.strip())[:700])
media = [n for n in z.namelist() if n.startswith("ppt/media/")]
print(f"\nmedia parts: {len(media)}")
