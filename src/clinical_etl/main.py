"""Clinical ETL CLI entry point."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from clinical_etl.config import configure_logging, get_logger, get_settings
from clinical_etl.extract import LabCSVExtractor
from clinical_etl.transform import CodeValidator, PatientMatcher, PHIMasker
from clinical_etl.utils import HIPAAAuditLogger

app = typer.Typer(name="clinical_etl", help="Clinical ETL CLI", no_args_is_help=True)
console = Console()
logger = get_logger(__name__)


def _bootstrap() -> None:
    s = get_settings()
    configure_logging(s.log_level, s.log_format)


@app.command()
def run(
    source: str = typer.Option("sample", help="Source (sample|fhir|oracle|edi|all)"),
) -> None:
    """Run the demo pipeline."""
    _bootstrap()
    console.print(f"[cyan]Running Clinical ETL pipeline with source: {source}[/]")

    pkg_dir = Path(__file__).resolve().parent.parent.parent
    sample_csv = pkg_dir / "data" / "sample" / "lab_patients.csv"
    if not sample_csv.exists():
        sample_csv = Path("data/sample/lab_patients.csv")

    extractor = LabCSVExtractor()
    masker = PHIMasker()
    validator = CodeValidator()
    audit = HIPAAAuditLogger()

    masked_records = []
    for candidate in extractor.extract(sample_csv):
        audit.log(
            actor="cli_demo",
            action="READ",
            resource_type="Patient",
            resource_id=candidate.source_id,
            purpose="OPERATIONS",
            source=candidate.source.value,
        )
        masked = masker.mask_patient_record(candidate.model_dump())
        masked_records.append(masked)

    # Show summary
    table = Table(title=f"Clinical ETL — {len(masked_records)} patient records processed")
    table.add_column("source_id", style="cyan")
    table.add_column("first_name_hash", style="dim")
    table.add_column("dob_year", justify="right")
    table.add_column("zip3", style="yellow")
    table.add_column("gender")
    for r in masked_records[:10]:
        table.add_row(
            r.get("source_id", "-"),
            (r.get("first_name_hash") or "")[:10] + "…",
            str(r.get("dob_year") or "-"),
            r.get("zip3") or "-",
            r.get("gender") or "-",
        )
    console.print(table)

    # Validate sample codes
    icd_codes = ["I10", "E119", "XYZ123", "J45"]
    cpt_codes = ["99213", "85025", "ABCDE", "71046"]
    diagnoses, procedures = validator.validate_batch(icd_codes, cpt_codes)
    console.print("\n[bold]Code validation:[/]")
    for d in diagnoses:
        sym = "✓" if d.is_valid else "✗"
        console.print(f"  {sym} ICD {d.code}: {d.description or 'unknown'}")
    for p in procedures:
        sym = "✓" if p.is_valid else "✗"
        console.print(f"  {sym} CPT {p.code}: {p.description or 'unknown'}")


@app.command()
def demo_fhir(fixture: str = typer.Option(..., "--fixture", "-f")) -> None:
    """Decode a single FHIR Patient JSON fixture and show the masked candidate."""
    _bootstrap()
    from clinical_etl.extract.fhir_extractor import FHIRPatientExtractor

    data = json.loads(Path(fixture).read_text())
    candidate = FHIRPatientExtractor._to_candidate(data)
    masker = PHIMasker()
    masked = masker.mask_patient_record(candidate.model_dump())
    console.print_json(data=masked)


if __name__ == "__main__":
    app()
