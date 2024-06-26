# Use a stub file to avoid editing the original.
from collections.abc import Iterable
from typing import Final


__version__: Final[str]

class BaseNoise:
	permutation: tuple[int, ...]
	period: int

	def __init__(self, period: int = ..., permutation_table: Iterable[int] = ...) -> None: ...
	def randomize(self, period: int = ...) -> None: ...

class SimplexNoise(BaseNoise):
	def noise2(self, x: float, y: float) -> float: ...
	def noise3(self, x: float, y: float, z: float) -> float: ...


def lerp(t: float, a: float, b: float) -> float: ...
def grad3(hash: float, x: float, y: float, z: float) -> float: ...


class TileableNoise(BaseNoise):
	def noise3(self, x: float, y: float, z: float, repeat: int, base: float = 0.0) -> float: ...
