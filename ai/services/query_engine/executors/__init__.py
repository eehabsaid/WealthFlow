"""One module per capability. Each declares its Capability (vocabulary, metrics, dimensions,
filters) next to the executor that answers it; the owning provider returns it from
get_query_capabilities(). Executors are read-only and owner-scoped."""
