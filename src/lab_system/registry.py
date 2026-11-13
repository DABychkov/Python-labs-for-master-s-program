"""Явный реестр фабрик анализаторов."""

from collections.abc import Callable

from .analysis import Analyzer

AnalyzerFactory = Callable[[], Analyzer]


class AnalyzerRegistry:
    def __init__(self, factories: dict[str, AnalyzerFactory] | None = None) -> None:
        self._factories = dict(factories or {})

    def register(self, analyzer_id: str, factory: AnalyzerFactory) -> None:
        if analyzer_id in self._factories:
            raise ValueError(f"analyzer already registered: {analyzer_id}")
        self._factories[analyzer_id] = factory

    def create(self, analyzer_id: str) -> Analyzer:
        try:
            return self._factories[analyzer_id]()
        except KeyError as error:
            raise KeyError(f"unknown analyzer: {analyzer_id}") from error

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._factories))


def default_registry() -> AnalyzerRegistry:
    from .analyzers import LengthAnalyzer, TemplateAnalyzer

    return AnalyzerRegistry(
        {
            LengthAnalyzer.analyzer_id: LengthAnalyzer,
            TemplateAnalyzer.analyzer_id: TemplateAnalyzer,
        }
    )
