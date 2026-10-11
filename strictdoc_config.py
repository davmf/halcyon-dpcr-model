"""StrictDoc project configuration: reads the SysML v2 model directly."""

from strictdoc.backend.sysml.sysml_format import SysMLFormat
from strictdoc.core.project_config import ProjectConfig


def create_config() -> ProjectConfig:
    return ProjectConfig(
        project_title="Halcyon dPCR-24",
        formats=[*ProjectConfig.default_formats(), SysMLFormat()],
        # Link JUnit results (build/results) to requirements through the
        # @relation markers in verification/*.py.
        project_features=["REQUIREMENT_TO_SOURCE_TRACEABILITY"],
        include_doc_paths=["/model/**", "/build/results/**"],
        source_root_path=".",
    )
