"""测试用最小 PDF 生成器：不引入 reportlab，直接拼 PDF 对象。"""

from __future__ import annotations


def make_pdf(text: str | None) -> bytes:
    """生成单页 PDF；text=None 时生成无文本层的“扫描件”占位。"""
    content = b""
    if text:
        escaped = text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        lines = escaped.split("\n")
        stream_parts = [b"BT /F1 12 Tf 72 720 Td"]
        for index, line in enumerate(lines):
            if index:
                stream_parts.append(b"0 -18 Td")
            stream_parts.append(f"({line}) Tj".encode("latin-1"))
        stream_parts.append(b"ET")
        content = b"\n".join(stream_parts)

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n"
        + content
        + b"\nendstream",
    ]

    output = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output += f"{index} 0 obj\n".encode("ascii") + obj + b"\nendobj\n"

    xref_offset = len(output)
    output += b"xref\n0 6\n0000000000 65535 f \n"
    for offset in offsets:
        output += f"{offset:010d} 00000 n \n".encode("ascii")
    output += b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n"
    output += str(xref_offset).encode("ascii") + b"\n%%EOF\n"
    return bytes(output)
