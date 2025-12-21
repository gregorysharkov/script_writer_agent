"""Knowledge Graph setup and seeding utilities."""

__all__ = []

try:
    from pragmatic_content_factory.setup.seed_knowledge_graph import seed_knowledge_graph
    __all__.append("seed_knowledge_graph")
except ImportError:
    pass

try:
    from pragmatic_content_factory.setup.parsers.worldview_parser import parse_worldview, SourceLink
    __all__.extend(["parse_worldview", "SourceLink"])
except ImportError:
    pass
