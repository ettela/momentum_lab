from __future__ import annotations

from pathlib import Path
from typing import Optional, List

import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from momentum_lab.model.block import Block, CollisionType, D


# 模拟、返回对应 dataframe
def simulate_collision(
    block_a: Block,
    block_b: Block,
    e: float = 1.0,
    duration: float = 6.0,
    dt: float = 0.01,
) -> pd.DataFrame:
    a = Block(block_a.x, block_a.m, block_a.v)
    b = Block(block_b.x, block_b.m, block_b.v)
    collision = D(a, b, e=e)

    records = []
    collided = False

    # 块宽 m
    PIXELS_PER_M = 100
    BLOCK_W_A = max(20, min(120, int(a.m * 30))) / PIXELS_PER_M

    steps = max(1, int(duration / dt))
    for step in range(steps):
        t = step * dt

        # 一次性碰撞检测
        if not collided and (a.x + BLOCK_W_A) >= b.x and a.v > b.v:
            collision.block_1 = a
            collision.block_2 = b
            new_a, new_b = collision.collide()
            new_a.x = b.x - BLOCK_W_A
            a, b = new_a, new_b
            collided = True

        collision.block_1 = a
        collision.block_2 = b

        records.append(
            {
                "t": round(t, 4),
                "xa": round(a.x, 6),
                "va": round(a.v, 6),
                "pa": round(a.moment, 6),
                "eka": round(a.k_energy, 6),
                "xb": round(b.x, 6),
                "vb": round(b.v, 6),
                "pb": round(b.moment, 6),
                "ekb": round(b.k_energy, 6),
                "p_total": round(collision.total_momentum, 6),
                "ek_total": round(collision.total_k_energy, 6),
                "collided": collided,
            }
        )

        # 前进一步
        a.x += a.v * dt
        b.x += b.v * dt

    return pd.DataFrame(records)


# 全图表
def plot_df(
    df: pd.DataFrame,
    pic_path: Path,
    title: Optional[str] = None,
    block_a: Optional[Block] = None,
    block_b: Optional[Block] = None,
):
    t_col = df["t"]
    collision_t = (
        df.loc[df["collided"], "t"].min()
        if ("collided" in df.columns and df["collided"].any())
        else None
    )
    plt.rcParams["font.sans-serif"] = ["SimHei"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, axes = plt.subplots(3, 1, figsize=(10, 11), sharex=True)
    if title:
        fig.suptitle(title, fontsize=14)

    # 速度图
    ax1 = axes[0]
    ma_label = f"$m={block_a.m}kg$" if block_a is not None else ""
    mb_label = f"$m={block_b.m}kg$" if block_b is not None else ""
    ax1.plot(t_col, df["va"], color="#4682C8", label=f"$v_A$ ({ma_label})")
    ax1.plot(t_col, df["vb"], color="#DC503C", label=f"$v_B$ ({mb_label})")
    if collision_t is not None:
        ax1.axvline(
            collision_t, color="gray", linestyle="--", linewidth=1, label="碰撞时刻"
        )
    ax1.set_ylabel("速度 ($m/s$)")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 动量图
    ax2 = axes[1]
    ax2.plot(t_col, df["pa"], color="#4682C8", label="$p_A$")
    ax2.plot(t_col, df["pb"], color="#DC503C", label="$p_B$")
    ax2.plot(
        t_col,
        df["p_total"],
        color="#2A2A2A",
        linestyle="--",
        linewidth=2,
        label="总动量",
    )
    if collision_t is not None:
        ax2.axvline(collision_t, color="gray", linestyle="--", linewidth=1)
    ax2.set_ylabel("动量 $(kg·m/s)$")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 动能图
    ax3 = axes[2]
    ax3.plot(t_col, df["eka"], color="#4682C8", label="$E_{k_A}$")
    ax3.plot(t_col, df["ekb"], color="#DC503C", label="$E_{k_B}$")
    ax3.plot(
        t_col,
        df["ek_total"],
        color="#3CA050",
        linestyle="--",
        linewidth=2,
        label="总动能",
    )
    if collision_t is not None:
        ax3.axvline(
            collision_t, color="gray", linestyle="--", linewidth=1, label="碰撞时刻"
        )
    ax3.set_xlabel("时间 ($s$)")
    ax3.set_ylabel("动能 ($J$)")
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(pic_path, dpi=150)
    plt.close(fig)


def export_chart(
    block_a: Block,
    block_b: Block,
    e: float = 1.0,
    output_dir: str | Path = ".",
    duration: float = 6.0,
) -> List[Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = simulate_collision(block_a, block_b, e=e, duration=duration)
    title = f"{CollisionType.from_e(e).label} $(e={e})$"

    pic_path = Path(output_dir) / "collision_plot.png"
    plot_df(df, pic_path, title=title, block_a=block_a, block_b=block_b)

    csv_path = Path(output_dir) / "collision_data.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    return [pic_path, csv_path]
