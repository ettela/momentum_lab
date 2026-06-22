from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    FLOAT_LIKE = float | np.double


class CollisionType(Enum):
    ELASTIC = "elastic"
    PARTIAL = "partial"
    INELASTIC = "inelastic"
    # e 在 [0, 1] 连续取值， __cls__.from_e() 映射。

    @classmethod
    def from_e(cls, e: float) -> CollisionType:
        if np.isclose(e, 1.0, atol=0.01):
            return cls.ELASTIC
        if np.isclose(e, 0.0, atol=0.01):
            return cls.INELASTIC
        return cls.PARTIAL

    @property
    def label(self) -> str:
        return {
            CollisionType.ELASTIC: "完全弹性碰撞",
            CollisionType.PARTIAL: "非完全弹性碰撞",
            CollisionType.INELASTIC: "完全非弹性碰撞",
        }[self]


# 理想物块模型
@dataclass
class Block:
    x: float
    m: float
    v: float

    @property
    def k_energy(self) -> float:
        return 0.5 * self.m * self.v**2

    @property
    def moment(self) -> float:
        return self.m * self.v

    # XXX
    def __repr__(self):
        return (
            f"Block(x={self.x}, m={self.m}, v={self.v}, "
            f"k_energy={self.k_energy}, moment={self.moment})"
        )


# 仅考虑正碰
@dataclass
class D:
    block_1: Block
    block_2: Block
    e: float = 1.0
    kind: CollisionType = field(init=False)  # 碰撞类型

    def __post_init__(self):
        self.kind = CollisionType.from_e(self.e)

    @classmethod
    def elastic(cls, b1: Block, b2: Block) -> D:
        return cls(b1, b2, e=1.0)

    @classmethod
    def inelastic(cls, b1: Block, b2: Block) -> D:
        return cls(b1, b2, e=0.0)

    @classmethod
    def partially_elastic(cls, b1: Block, b2: Block, e: float = 0.5) -> D:
        return cls(b1, b2, e=float(np.clip(e, 0.0, 1.0)))

    # 计算部分
    def collide(self) -> tuple[Block, Block]:
        m1, v1 = self.block_1.m, self.block_1.v
        m2, v2 = self.block_2.m, self.block_2.v
        e = self.e
        M = m1 + m2
        v1n = ((m1 - e * m2) * v1 + (1 + e) * m2 * v2) / M
        v2n = ((m2 - e * m1) * v2 + (1 + e) * m1 * v1) / M
        return Block(self.block_1.x, m1, v1n), Block(self.block_2.x, m2, v2n)

    @property
    def total_momentum(self) -> float:
        return self.block_1.moment + self.block_2.moment

    @property
    def total_k_energy(self) -> float:
        return self.block_1.k_energy + self.block_2.k_energy
