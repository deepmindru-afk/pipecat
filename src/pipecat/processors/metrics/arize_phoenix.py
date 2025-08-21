#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""Arize Phoenix Tracer integration for frame processor metrics."""

from loguru import logger
import os

from pipecat.processors.metrics.frame_processor_metrics import FrameProcessorMetrics

try:
    from phoenix.otel import register
    from opentelemetry import trace
    from openinference.semconv.trace import SpanAttributes
except ModuleNotFoundError as e:
    logger.error(f"Exception: {e}")
    logger.error(
        "In order to use Arize Phoenix, you need to `pip install pipecat-ai[arize-phoenix]`. Also set PHOENIX_COLLECTOR_ENDPOINT"
    )
    raise Exception(f"Missing module: {e}")


class ArizePhoenixOpenAITracer(FrameProcessorMetrics):
    """Frame processor tracing integration with Arize Phoenix."""

    def __init__(self, session_id):
        """Initialize the Arize Phoenix tracer."""
        super().__init__()
        self._tracer_provider = None
        self._openai_instrumentor = None
        self._session_id = session_id
        self.import_dep_and_init_tracer()

    def import_dep_and_init_tracer(self):
        try:
            from openinference.instrumentation.openai import OpenAIInstrumentor

            try:
                PHOENIX_COLLECTOR_ENDPOINT = os.getenv("PHOENIX_COLLECTOR_ENDPOINT")
                if not PHOENIX_COLLECTOR_ENDPOINT:
                    raise Exception(f"Missing env var PHOENIX_COLLECTOR_ENDPOINT.")

                self._tracer_provider = register(
                    batch=True,  # uses a batch span processor
                )

                self._openai_instrumentor = OpenAIInstrumentor().instrument(
                    tracer_provider=self._tracer_provider
                )

                current_span = trace.get_current_span()
                current_span.set_attribute(SpanAttributes.SESSION_ID, self._session_id)
            except Exception as e:
                logger.warning(
                    f"self._tracer_provider failed. Phoenix features will be disabled: {e}"
                )
            if not self._openai_instrumentor:
                logger.warning(
                    "Arize Phoenix for OpenAI not available. Phoenix features will be disabled."
                )
        except Exception as e:
            logger.warning(
                f"Arize Phoenix for OpenAI not available. Phoenix features will be disabled. {e}"
            )
