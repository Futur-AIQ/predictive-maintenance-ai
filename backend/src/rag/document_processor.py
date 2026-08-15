import json
import re
from pathlib import Path
from typing import List, Tuple

from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from loguru import logger


# ---------------------------------------------------------------------------
# Equipment-type detection helpers
# ---------------------------------------------------------------------------

def _detect_equipment_type(text: str, filename: str = "") -> str:
    """Return 'turbofan', 'pump', 'compressor', or 'unknown' based on heuristics."""
    combined = text + " " + filename
    if re.search(r"turbofan|Engine", combined):
        return "turbofan"
    if re.search(r"pump|Pump", combined):
        return "pump"
    if re.search(r"compressor|Comp", combined, re.IGNORECASE):
        return "compressor"
    return "unknown"


# ---------------------------------------------------------------------------
# Metadata extraction helpers
# ---------------------------------------------------------------------------

_FAULT_CODE_PATTERN = re.compile(r"[FCPfcp]\d{3}")
_SEVERITY_LEVELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def _extract_fault_codes(text: str) -> List[str]:
    """Return a deduplicated list of fault codes found in *text*."""
    found = _FAULT_CODE_PATTERN.findall(text)
    # Normalise to uppercase so 'f001' and 'F001' unify
    return list(dict.fromkeys(code.upper() for code in found))


def _extract_severities(text: str) -> List[str]:
    """Return a deduplicated list of severity keywords found in *text*."""
    upper = text.upper()
    return [sev for sev in _SEVERITY_LEVELS if sev in upper]


def _build_metadata(
    source_file: str,
    equipment_type: str,
    chunk_type: str,
    text: str,
) -> dict:
    return {
        "source_file": source_file,
        "equipment_type": equipment_type,
        "chunk_type": chunk_type,
        "fault_codes_mentioned": _extract_fault_codes(text),
        "severity_mentioned": _extract_severities(text),
    }


# ---------------------------------------------------------------------------
# DocumentProcessor
# ---------------------------------------------------------------------------


class DocumentProcessor:
    """
    Converts raw data files into LangChain Document objects ready for
    vector-store ingestion.

    - Equipment manuals  → RecursiveCharacterTextSplitter (chunk=1024, overlap=200),
                           pre-split on section headers.
    - fault_code_reference.txt → one Document per pipe-delimited data row.
    - maintenance_logs.jsonl   → one Document per JSON line.
    """

    def __init__(self) -> None:
        # Primary splitter used after header-based pre-splitting of manuals
        self._char_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1024,
            chunk_overlap=200,
            separators=["##", "#", "\n\n", "\n", " ", ""],
        )

        # Header-level splitter: splits on Markdown-style headers first.
        # We keep a generous chunk size so full sections survive as units
        # before the character splitter refines them.
        self._section_splitter = RecursiveCharacterTextSplitter(
            chunk_size=4096,
            chunk_overlap=0,
            separators=["##", "#", "\n\n"],
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_manual(self, file_path: str) -> List[Document]:
        """
        Process a plain-text equipment manual.

        Strategy:
          1. Split the full text on section headers ("##", "#", "\\n\\n") to
             obtain logical sections.
          2. Feed each section through RecursiveCharacterTextSplitter
             (chunk_size=1024, chunk_overlap=200) to produce the final chunks.
        """
        path = Path(file_path)
        logger.info(f"Processing manual: {path.name}")

        text = path.read_text(encoding="utf-8")
        source_file = path.name
        equipment_type = _detect_equipment_type(text, source_file)

        # Step 1 – coarse section split
        sections = self._section_splitter.split_text(text)
        logger.debug(f"  {path.name}: {len(sections)} sections after header split")

        # Step 2 – fine-grained character split within each section
        documents: List[Document] = []
        for section in sections:
            section = section.strip()
            if not section:
                continue
            chunks = self._char_splitter.split_text(section)
            for chunk in chunks:
                chunk = chunk.strip()
                if not chunk:
                    continue
                metadata = _build_metadata(
                    source_file=source_file,
                    equipment_type=equipment_type,
                    chunk_type="manual",
                    text=chunk,
                )
                documents.append(Document(page_content=chunk, metadata=metadata))

        logger.info(f"  {path.name}: produced {len(documents)} chunks")
        return documents

    def process_fault_codes(self, file_path: str) -> List[Document]:
        """
        Parse a pipe-delimited fault-code reference file.

        The first row is the header; every subsequent non-empty row becomes
        exactly one Document.  Rows are never split.

        Expected columns: CODE|EQUIPMENT_TYPE|DESCRIPTION|SEVERITY|
                          RECOMMENDED_ACTION|RESPONSE_TIME_HOURS
        """
        path = Path(file_path)
        logger.info(f"Processing fault code reference: {path.name}")

        lines = path.read_text(encoding="utf-8").splitlines()
        if not lines:
            logger.warning(f"  {path.name} is empty – skipping")
            return []

        header_line = lines[0]
        columns = [col.strip() for col in header_line.split("|")]
        documents: List[Document] = []

        for lineno, line in enumerate(lines[1:], start=2):
            line = line.strip()
            if not line:
                continue

            parts = [p.strip() for p in line.split("|")]
            # Build a readable text representation of the row
            row_dict: dict = {}
            for idx, col in enumerate(columns):
                row_dict[col] = parts[idx] if idx < len(parts) else ""

            # Human-readable content keeps the original pipe-delimited form
            # so BM25 / vector search can match on any field value.
            content = (
                f"Fault Code: {row_dict.get('CODE', '')}\n"
                f"Equipment Type: {row_dict.get('EQUIPMENT_TYPE', '')}\n"
                f"Description: {row_dict.get('DESCRIPTION', '')}\n"
                f"Severity: {row_dict.get('SEVERITY', '')}\n"
                f"Recommended Action: {row_dict.get('RECOMMENDED_ACTION', '')}\n"
                f"Response Time (hours): {row_dict.get('RESPONSE_TIME_HOURS', '')}"
            )

            raw_eq_type = row_dict.get("EQUIPMENT_TYPE", "")
            equipment_type = _detect_equipment_type(content, raw_eq_type)

            metadata = _build_metadata(
                source_file=path.name,
                equipment_type=equipment_type,
                chunk_type="fault_code",
                text=content,
            )
            # Ensure the fault code itself is always in fault_codes_mentioned
            code = row_dict.get("CODE", "").upper()
            if code and code not in metadata["fault_codes_mentioned"]:
                metadata["fault_codes_mentioned"].insert(0, code)

            documents.append(Document(page_content=content, metadata=metadata))

        logger.info(f"  {path.name}: produced {len(documents)} fault code documents")
        return documents

    def process_maintenance_logs(self, file_path: str) -> List[Document]:
        """
        Parse a JSONL maintenance log file.

        Each JSON line becomes exactly one Document.  Lines are never split.
        The page_content is a human-readable textual rendering of the log entry.
        """
        path = Path(file_path)
        logger.info(f"Processing maintenance logs: {path.name}")

        documents: List[Document] = []
        with path.open(encoding="utf-8") as fh:
            for lineno, raw_line in enumerate(fh, start=1):
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    entry: dict = json.loads(raw_line)
                except json.JSONDecodeError as exc:
                    logger.warning(f"  Skipping malformed JSON at line {lineno}: {exc}")
                    continue

                # Render a readable string so both the vector model and BM25
                # can work on natural language.
                parts_replaced = entry.get("parts_replaced", [])
                parts_str = (
                    ", ".join(parts_replaced) if parts_replaced else "None"
                )
                content = (
                    f"Timestamp: {entry.get('timestamp', '')}\n"
                    f"Equipment ID: {entry.get('equipment_id', '')}\n"
                    f"Technician: {entry.get('technician', '')}\n"
                    f"Fault Code: {entry.get('fault_code', '')}\n"
                    f"Description: {entry.get('description', '')}\n"
                    f"Action Taken: {entry.get('action_taken', '')}\n"
                    f"Resolution Time (hours): {entry.get('resolution_time_hours', '')}\n"
                    f"Work Order ID: {entry.get('work_order_id', '')}\n"
                    f"Parts Replaced: {parts_str}\n"
                    f"Cost (USD): {entry.get('cost_usd', '')}"
                )

                equipment_id = entry.get("equipment_id", "")
                equipment_type = _detect_equipment_type(content, equipment_id)

                metadata = _build_metadata(
                    source_file=path.name,
                    equipment_type=equipment_type,
                    chunk_type="log",
                    text=content,
                )

                documents.append(Document(page_content=content, metadata=metadata))

        logger.info(f"  {path.name}: produced {len(documents)} log documents")
        return documents

    def process_all(
        self, raw_data_dir: str
    ) -> Tuple[List[Document], List[Document]]:
        """
        Walk *raw_data_dir* and process every recognised file.

        Returns
        -------
        technical_docs : List[Document]
            Equipment manuals + fault-code reference rows.
        maintenance_history : List[Document]
            Maintenance log entries.
        """
        data_dir = Path(raw_data_dir)
        if not data_dir.exists():
            raise FileNotFoundError(f"Raw data directory not found: {data_dir}")

        technical_docs: List[Document] = []
        maintenance_history: List[Document] = []

        # Collect and sort files for deterministic ordering
        all_files = sorted(data_dir.iterdir())

        for file_path in all_files:
            if not file_path.is_file():
                continue

            name = file_path.name.lower()

            if name.endswith(".txt") and "fault_code" in name:
                docs = self.process_fault_codes(str(file_path))
                technical_docs.extend(docs)

            elif name.endswith(".txt") and (
                "manual" in name or "equipment" in name
            ):
                docs = self.process_manual(str(file_path))
                technical_docs.extend(docs)

            elif name.endswith(".jsonl"):
                docs = self.process_maintenance_logs(str(file_path))
                maintenance_history.extend(docs)

            else:
                logger.debug(f"Skipping unrecognised file: {file_path.name}")

        logger.info(
            f"process_all complete – "
            f"technical_docs={len(technical_docs)}, "
            f"maintenance_history={len(maintenance_history)}"
        )
        return technical_docs, maintenance_history
