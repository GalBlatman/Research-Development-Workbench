import re

from domain.sources import SourceAnchor, SourceVersion, digest


def anchors(version: SourceVersion) -> tuple[SourceAnchor, ...]:
    """Exact Unicode codepoint offsets, 1-based lines; preserve all source bytes/text."""
    if version.text is None:
        return ()
    text = version.text
    boundaries = [0]
    if version.media_type == "text/markdown":
        offset = 0
        fence: tuple[str, int] | None = None
        for line in text.splitlines(keepends=True):
            marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
            if marker:
                kind = marker.group(1)[0]
                if fence is None:
                    fence = (kind, len(marker.group(1)))
                elif (
                    kind == fence[0]
                    and len(marker.group(1)) >= fence[1]
                    and not line[marker.end() :].strip()
                ):
                    fence = None
            elif fence is None and re.match(r"^#{1,6}[ \t]+", line) and offset != 0:
                boundaries.append(offset)
            offset += len(line)
    boundaries.append(len(text))
    output = []
    for start, end in zip(boundaries, boundaries[1:]):
        quoted = text[start:end]
        quote_hash = digest(quoted.encode("utf-8"))
        identifier = digest(
            f"{version.document.document_id}:{version.document.version}:{start}:{end}:{quote_hash}".encode()
        )
        output.append(
            SourceAnchor(
                anchor_id=identifier,
                document_id=version.document.document_id,
                version=version.document.version,
                start=start,
                end=end,
                line_start=text.count("\n", 0, start) + 1,
                line_end=text.count("\n", 0, max(start, end - 1)) + 1,
                quoted_text_sha256=quote_hash,
            )
        )
    return tuple(output)


def validate_anchor(anchor: SourceAnchor, version: SourceVersion) -> None:
    if (anchor.document_id, anchor.version) != (
        version.document.document_id,
        version.document.version,
    ):
        raise ValueError("Anchor belongs to a different document version")
    if version.text is not None:
        if (
            anchor.end > len(version.text)
            or digest(version.text[anchor.start : anchor.end].encode("utf-8"))
            != anchor.quoted_text_sha256
        ):
            raise ValueError("Anchor does not resolve to the recorded source text")
        if anchor not in anchors(version):
            raise ValueError("Anchor location is not a stable section from this parser version")
