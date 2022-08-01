import logging
from wsgiref.simple_server import make_server

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.pyramid import PyramidInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pyramid.config import Configurator
from pyramid.response import Response

tracer = trace.get_tracer(__name__)


def sub_fn(x: int) -> None:
    with tracer.start_span(f"x={x}"):
        if x < 3:
            sub_fn(x + 1)
        logging.info("x=%s", x)


def hello_world(request):
    sub_fn(0)
    return Response("Hello World!")


if __name__ == "__main__":
    trace_provider = TracerProvider(
        resource=Resource(attributes={"service.name": "hello_world"})
    )
    trace_provider.add_span_processor(
        BatchSpanProcessor(
            JaegerExporter(
                collector_endpoint="http://127.0.0.1:14268/api/traces?format=jaeger.thrift"
            )
        )
    )
    trace.set_tracer_provider(trace_provider)

    PyramidInstrumentor().instrument()
    LoggingInstrumentor().instrument(set_logging_format=True)

    with Configurator(settings={}) as config:
        config.add_route("hello", "/")
        config.add_view(hello_world, route_name="hello")
        app = config.make_wsgi_app()

    server = make_server("0.0.0.0", 6543, app)

    server.serve_forever()
