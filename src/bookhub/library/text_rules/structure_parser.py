from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


BRACKET_TYPE_PAIRS: dict[str, tuple[tuple[str, str], ...]] = {
    "square": (("[", "]"), ("［", "］")),
    "round": (("(", ")"), ("（", "）")),
    "chinese_square": (("【", "】"),),
    "corner": (("「", "」"), ("『", "』")),
    "book_title": (("《", "》"),),
    "angle": (("<", ">"), ("＜", "＞")),
}
BRACKET_PAIR_CODES: dict[str, tuple[str, str]] = {
    "[]": ("[", "]"),
    "［］": ("［", "］"),
    "【】": ("【", "】"),
    "()": ("(", ")"),
    "（）": ("（", "）"),
    "<>": ("<", ">"),
    "＜＞": ("＜", "＞"),
    "《》": ("《", "》"),
    "「」": ("「", "」"),
    "『』": ("『", "』"),
}
BRACKET_SCOPES = {"outer", "all", "inner"}
STRUCTURE_SEPARATORS = (" -- ", " - ", " by ", "／", "/", "|", "_", "-", " ")


@dataclass(frozen=True, slots=True)
class BracketBlock:
    bracket_type: str
    start: int
    end: int
    content_start: int
    content_end: int
    depth: int
    open_char: str
    close_char: str

    def content(self, value: str) -> str:
        return value[self.content_start : self.content_end]


@dataclass(frozen=True, slots=True)
class StructureSignature:
    bracket_sequence: tuple[str, ...]
    separator_sequence: tuple[str, ...]
    slot_count: int
    extension: str
    shape: str


@dataclass(frozen=True, slots=True)
class StructureSample:
    value: str
    signature: StructureSignature


@dataclass(frozen=True, slots=True)
class StructureGroup:
    signature: StructureSignature
    count: int
    samples: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StructureReport:
    total: int
    groups: tuple[StructureGroup, ...]
    dominant_group: StructureGroup | None
    consistency_score: float
    outlier_samples: tuple[str, ...]


def bracket_pairs_for_type(bracket_type: str) -> tuple[tuple[str, str], ...]:
    if bracket_type == "all":
        pairs: list[tuple[str, str]] = []
        for value in BRACKET_TYPE_PAIRS.values():
            pairs.extend(value)
        return tuple(pairs)
    pairs = BRACKET_TYPE_PAIRS.get(bracket_type)
    if pairs is None:
        raise ValueError(f"Unsupported bracket type: {bracket_type}")
    return pairs


def parse_bracket_blocks(value: str) -> list[BracketBlock]:
    open_lookup: dict[str, tuple[str, str]] = {}
    close_lookup: dict[str, str] = {}
    for bracket_type, pairs in BRACKET_TYPE_PAIRS.items():
        for open_char, close_char in pairs:
            open_lookup[open_char] = (bracket_type, close_char)
            close_lookup[close_char] = open_char

    stack: list[tuple[str, str, int, str]] = []
    blocks: list[BracketBlock] = []
    for index, char in enumerate(value):
        if char in open_lookup:
            bracket_type, close_char = open_lookup[char]
            stack.append((bracket_type, close_char, index, char))
            continue
        if char not in close_lookup:
            continue

        match_index = -1
        for stack_index in range(len(stack) - 1, -1, -1):
            if stack[stack_index][1] == char:
                match_index = stack_index
                break
        if match_index < 0:
            continue

        bracket_type, close_char, start_index, open_char = stack[match_index]
        del stack[match_index:]
        blocks.append(
            BracketBlock(
                bracket_type=bracket_type,
                start=start_index,
                end=index + 1,
                content_start=start_index + len(open_char),
                content_end=index,
                depth=match_index,
                open_char=open_char,
                close_char=close_char,
            )
        )
    return sorted(blocks, key=lambda block: (block.start, block.end, block.depth))


def filter_bracket_blocks(
    blocks: list[BracketBlock],
    *,
    bracket_type: str = "all",
    scope: str = "outer",
    pair: tuple[str, str] | None = None,
) -> list[BracketBlock]:
    if scope not in BRACKET_SCOPES:
        raise ValueError(f"Unsupported bracket scope: {scope}")
    if bracket_type != "all" and bracket_type not in BRACKET_TYPE_PAIRS:
        raise ValueError(f"Unsupported bracket type: {bracket_type}")

    selected = [
        block
        for block in blocks
        if (bracket_type == "all" or block.bracket_type == bracket_type)
        and (pair is None or (block.open_char, block.close_char) == pair)
    ]
    if scope == "all":
        return selected
    if scope == "outer":
        return [block for block in selected if block.depth == 0]
    return [
        block
        for block in selected
        if not any(other.start > block.start and other.end < block.end for other in blocks)
    ]


def bracket_blocks_for_pair(value: str, pair_code: str, *, scope: str = "outer") -> list[BracketBlock]:
    pair = BRACKET_PAIR_CODES.get(pair_code)
    if pair is None:
        raise ValueError(f"Unsupported bracket pair: {pair_code}")
    return filter_bracket_blocks(parse_bracket_blocks(value), scope=scope, pair=pair)


def structure_signature(
    value: str,
    separators: tuple[str, ...] | None = None,
) -> StructureSignature:
    text = str(value or "")
    active_separators = separators or STRUCTURE_SEPARATORS
    extension = Path(text).suffix.lower()
    stem = text[: -len(extension)] if extension else text
    outer_blocks = filter_bracket_blocks(parse_bracket_blocks(stem), scope="outer")
    bracket_sequence = tuple(block.bracket_type for block in outer_blocks)
    separator_sequence = tuple(_outside_separators(stem, outer_blocks, active_separators))
    token_count = max(len(bracket_sequence), len(separator_sequence) + 1 if stem.strip() else 0)
    shape_parts: list[str] = []
    cursor = 0
    for block in outer_blocks:
        if stem[cursor : block.start].strip():
            shape_parts.append("text")
        shape_parts.append(block.bracket_type)
        cursor = block.end
    if stem[cursor:].strip():
        shape_parts.append("text")
    if not shape_parts:
        shape_parts.append("empty")
    return StructureSignature(
        bracket_sequence=bracket_sequence,
        separator_sequence=separator_sequence,
        slot_count=token_count,
        extension=extension,
        shape="_".join(shape_parts),
    )


def build_structure_report(
    values: list[str] | tuple[str, ...],
    *,
    separators: tuple[str, ...] | None = None,
    max_samples: int = 80,
    outlier_limit: int = 5,
) -> StructureReport:
    samples = [str(value) for value in values[:max_samples] if str(value or "").strip()]
    grouped: dict[StructureSignature, list[str]] = {}
    for value in samples:
        signature = structure_signature(value, separators)
        grouped.setdefault(signature, []).append(value)

    groups = tuple(
        StructureGroup(signature=signature, count=len(items), samples=tuple(items[:3]))
        for signature, items in sorted(
            grouped.items(),
            key=lambda item: (-len(item[1]), item[0].shape, item[0].separator_sequence, item[0].extension),
        )
    )
    dominant = groups[0] if groups else None
    consistency = (dominant.count / len(samples) * 100.0) if dominant and samples else 0.0
    outliers: list[str] = []
    if dominant is not None:
        for value in samples:
            if structure_signature(value, separators) != dominant.signature:
                outliers.append(value)
                if len(outliers) >= outlier_limit:
                    break
    return StructureReport(
        total=len(samples),
        groups=groups,
        dominant_group=dominant,
        consistency_score=consistency,
        outlier_samples=tuple(outliers),
    )


def format_structure_signature(signature: StructureSignature) -> str:
    bracket_text = ",".join(signature.bracket_sequence) if signature.bracket_sequence else "text"
    separator_text = "".join(signature.separator_sequence) if signature.separator_sequence else "none"
    extension_text = signature.extension or "none"
    return f"{signature.shape}; brackets={bracket_text}; separators={separator_text}; parts={signature.slot_count}; ext={extension_text}"


def _outside_separators(value: str, blocks: list[BracketBlock], candidates: tuple[str, ...]) -> list[str]:
    ranges = [(block.start, block.end) for block in blocks]
    separators: list[str] = []
    cursor = 0
    for start, end in ranges:
        separators.extend(_scan_separators(value[cursor:start], candidates))
        cursor = end
    separators.extend(_scan_separators(value[cursor:], candidates))
    return separators


def _scan_separators(value: str, candidates: tuple[str, ...]) -> list[str]:
    separators: list[str] = []
    index = 0
    sorted_candidates = [item for item in sorted(candidates, key=len, reverse=True) if item]
    while index < len(value):
        for separator in sorted_candidates:
            if value.startswith(separator, index):
                separators.append(separator)
                index += len(separator)
                break
        else:
            index += 1
    return separators
