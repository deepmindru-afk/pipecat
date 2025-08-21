#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""Arize Phoenix Tracer integration for frame processor metrics."""

from loguru import logger
import os

from pipecat.processors.metrics.frame_processor_metrics import FrameProcessorMetrics
# from pipecat.utils.base_object import BaseObject

try:
    from phoenix.otel import register
except ModuleNotFoundError as e:
    logger.error(f"Exception: {e}")
    logger.error(
        "In order to use Arize Phoenix, you need to `pip install pipecat-ai[arize-phoenix]`."
    )
    raise Exception(f"Missing module: {e}")


class ArizePhoenixOpenAITracer(FrameProcessorMetrics):
    """Frame processor tracing integration with Arize Phoenix."""

    def __init__(self):
        """Initialize the Arize Phoenix tracer."""
        super().__init__()
        self.import_dep_and_init_tracer()

    def import_dep_and_init_tracer(self):
        try:
            from openinference.instrumentation.openai import OpenAIInstrumentor

            self._tracer_provider = register()

            # ensure PHOENIX_COLLECTOR_ENDPOINT is set
            tracer_provider = register(
                # space_id = os.getenv("PHOENIX_SPACE_ID"),
                # api_key = os.getenv("PHOENIX_API_KEY"),
                project_name=os.getenv("PHOENIX_PROJECT_NAME"),
                batch=True,  # uses a batch span processor
                auto_instrument=True,  # uses all installed OpenInference instrumentors
            )

            self._openai_instrumentor = OpenAIInstrumentor().instrument(
                tracer_provider=self._tracer_provider
            )
            if not self._openai_instrumentor:
                logger.warning(
                    "Arize Phoenix for OpenAI not available. Phoenix features will be disabled."
                )
        except Exception as e:
            logger.warning(
                "Arize Phoenix for OpenAI not available. Phoenix features will be disabled."
            )
