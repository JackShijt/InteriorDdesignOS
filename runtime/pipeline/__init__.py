"""runtime.pipeline · 流水线包（Phase 8 §1）。

- core           : 旧版 Parser→Design 流水线（Phase 3.5 / 4 / 5），保留向后兼容。
- pipeline_runner: Phase 8 端到端设计流水线编排（Layout→Geometry→Drawing→CAD Mock）。
"""
from .core import (  # noqa: F401
    SUPPORTED_STAGES,
    TERMINAL_STAGE,
    PROFESSIONAL_STAGE,
    StageController,
    Pipeline,
)
from .pipeline_runner import PipelineRunner  # noqa: F401
from .professional_pipeline import ProfessionalPipeline  # noqa: F401
from .orchestrated_pipeline import OrchestratedPipeline  # noqa: F401
from .e2e_pipeline import E2EPipeline  # noqa: F401

__all__ = [
    "SUPPORTED_STAGES",
    "TERMINAL_STAGE",
    "PROFESSIONAL_STAGE",
    "StageController",
    "Pipeline",
    "PipelineRunner",
    "ProfessionalPipeline",
    "OrchestratedPipeline",
    "E2EPipeline",
]
