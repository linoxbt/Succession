"""Succession — the property layer for agent memory.

Public surface:

    from succession import export_tenant, import_package, open_tenant

Everything else is reachable through the submodules: :mod:`succession.smp` for
the package format, :mod:`succession.merkle` for the integrity scheme,
:mod:`succession.valuation`, :mod:`succession.dataroom`, :mod:`succession.seal`,
and :mod:`succession.certificate`.
"""

from .canonical import canonical_bytes, canonical_json
from .export import ExportResult, build_package, export_tenant, read_all
from .importer import ImportResult, IntegrityMismatch, import_package, verify_package
from .memory.sibyl import SibylMemory, open_tenant
from .merkle import MerkleTree, build_tree, to_hex, verify_proof
from .provenance import SignatureError, sign_header, verify_header
from .redaction import Disclosure, Sensitivity, mark, read_disclosure
from .smp import DATA_CATEGORIES, SMP_CATEGORIES, SMP_VERSION, SMPPackage

__version__ = "0.1.0"

__all__ = [
    "DATA_CATEGORIES",
    "SMP_CATEGORIES",
    "SMP_VERSION",
    "Disclosure",
    "ExportResult",
    "ImportResult",
    "IntegrityMismatch",
    "MerkleTree",
    "SMPPackage",
    "Sensitivity",
    "SibylMemory",
    "SignatureError",
    "build_package",
    "build_tree",
    "canonical_bytes",
    "canonical_json",
    "export_tenant",
    "import_package",
    "mark",
    "open_tenant",
    "read_all",
    "read_disclosure",
    "sign_header",
    "to_hex",
    "verify_header",
    "verify_package",
    "verify_proof",
]
