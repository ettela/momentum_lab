from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

import pygame as pg
import pandas as pd

from momentum_lab.export.chart import export_chart
from momentum_lab.model.block import Block, D
from momentum_lab.ui.const import *
from momentum_lab.ui.surface import *
from momentum_lab.ui.display import *


class Scene:
    E_PRESETS = [1.0, 0.5, 0.0]

    def __init__(self, block_a: Block, block_b: Block, e: float = 1.0, fps: int = 60):
        # 保存初始参数用于重置
        self._init_a = Block(block_a.x, block_a.m, block_a.v)
        self._init_b = Block(block_b.x, block_b.m, block_b.v)
        self._e_idx = self.E_PRESETS.index(e) if e in self.E_PRESETS else 0

        # 当前物块与碰撞计算器
        self.block_a = Block(block_a.x, block_a.m, block_a.v)
        self.block_b = Block(block_b.x, block_b.m, block_b.v)
        self.collision = D(self.block_a, self.block_b, e=self.E_PRESETS[self._e_idx])
        self.fps = fps

        # 运行状态
        self.paused = False
        self.first_collision_recorded = False
        self.collision_count = 0

        # 面板显示初始系统动量、动能
        self.initial_p = self.collision.total_momentum
        self.initial_ek = self.collision.total_k_energy

        # 碰撞前后记录
        self.p_before: float | None = None
        self.p_after: float | None = None
        self.ek_before: float | None = None
        self.ek_after: float | None = None

        self._flash = 0

        # 一次性碰撞标志：只在碰撞发生的那一帧为 True
        self._just_collided: bool = False
        self._last_collision_time: float | None = None

        # 输入缓冲 限制小数位数
        self.input_buffers: Dict[str, str] = {
            "ma": self._format_var("ma", block_a.m),
            "va": self._format_var("va", block_a.v),
            "mb": self._format_var("mb", block_b.m),
            "vb": self._format_var("vb", block_b.v),
            "e": self._format_var("e", self.E_PRESETS[self._e_idx]),
        }
        self.active_input: str | None = None
        self.box_rects: Dict[str, pg.Rect] = {}
        self.hit_rects: Dict[str, pg.Rect] = {}

        self._paused_before_edit = False

        # 输入光标闪烁
        self._cursor_acc = 0.0
        self._cursor_visible = True
        self._cursor_blink_interval = 0.5

        # 导出提示
        self._export_msg: str = ""
        self._export_msg_timer: float = 0.0
        self._export_pending: bool = False
        self._export_pending_since: float = 0.0
        self._export_pending_hist_len: int = 0

        # 运行时间与历史记录
        self._time = 0.0
        self._history: list[dict] = []

    # 格式化显示值（简短）
    def _format_var(self, field: str, val: float) -> str:
        try:
            if field in ("ma", "mb"):
                return f"{val:.1f}"
            if field in ("va", "vb"):
                return f"{val:.2f}"
            if field == "e":
                return f"{val:.2f}"
        except Exception:
            pass
        return str(val)

    # 主循环
    def run(self):
        pg.init()
        screen = pg.display.set_mode((W, H), pg.NOFRAME)
        pg.display.set_caption("动量守恒演示")
        clock = pg.time.Clock()
        fonts = u_load_fonts()
        compute_panel_layout(self, fonts)

        while True:
            dt = clock.tick(self.fps) / 1000.0
            self._update_cursor(dt)

            # 更新导出计时器
            if self._export_msg_timer > 0:
                self._export_msg_timer -= dt
                if self._export_msg_timer <= 0:
                    self._export_msg = ""
                    self._export_msg_timer = 0.0

            for event in pg.event.get():
                if event.type == pg.QUIT:
                    pg.quit()
                    sys.exit()

                # 点击选中输入框
                if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    hit = None
                    for field, hit_rect in self.hit_rects.items():
                        if hit_rect.collidepoint(mx, my):
                            hit = field
                            break
                    if hit is not None:
                        self.active_input = hit
                        self.input_buffers[hit] = ""
                        self._paused_before_edit = self.paused
                        self.paused = True
                    else:
                        if self.active_input is not None:
                            field = self.active_input
                            self.input_buffers[field] = self._current_value_str(field)
                            self.active_input = None
                            self.paused = self._paused_before_edit

                # 键盘
                if event.type == pg.KEYDOWN:
                    if self.active_input is not None:
                        field = self.active_input

                        # 导出支持
                        if event.key == pg.K_s:
                            if not self.input_buffers.get(field):
                                self.input_buffers[field] = self._current_value_str(
                                    field
                                )
                                self.active_input = None
                                self.paused = self._paused_before_edit
                            else:
                                self._commit_active_input()
                            self._export_charts()
                            continue

                        if event.key in (pg.K_RETURN, pg.K_KP_ENTER):
                            self._commit_active_input()
                        elif event.key == pg.K_ESCAPE:
                            self.input_buffers[field] = self._current_value_str(field)
                            self.active_input = None
                            self.paused = self._paused_before_edit
                        elif event.key == pg.K_BACKSPACE:
                            if self.input_buffers.get(field):
                                self.input_buffers[field] = self.input_buffers[field][
                                    :-1
                                ]
                        else:
                            ch = event.unicode
                            if ch and (ch.isdigit() or ch in ".-"):
                                self.input_buffers[field] += ch
                        continue

                    # 全局键
                    match event.key:
                        case pg.K_q | pg.K_ESCAPE:
                            pg.quit()
                            sys.exit()
                        case pg.K_SPACE:
                            self.paused = not self.paused
                        case pg.K_r:
                            self._reset()
                        case pg.K_e:
                            self._cycle_e()
                        case pg.K_s:
                            self._export_charts()
                        case _:
                            pass

            if not self.paused:
                self._update(dt)
                if self._flash > 0:
                    self._flash -= 1
            self._time += dt
            self._record_history()

            screen.fill(C(BG))
            pg.draw.rect(screen, C(BG), (0, 0, SIM_W, H))

            draw_track(screen, fonts)
            draw_blocks(screen, fonts, self)
            draw_panel(screen, fonts, self)
            draw_hintbar(screen, fonts)

            if self.paused:
                draw_paused_overlay(screen, fonts)

            pg.display.flip()

    # 光标闪烁计时
    def _update_cursor(self, dt: float):
        self._cursor_acc += dt
        if self._cursor_acc >= self._cursor_blink_interval:
            self._cursor_acc -= self._cursor_blink_interval
            self._cursor_visible = not self._cursor_visible

    # 物理更新与碰撞处理
    def _update(self, dt: float):
        a, b = self.block_a, self.block_b
        wa = u_block_w(a)
        ax_right = sim_x(a.x) + wa
        bx_left = sim_x(b.x)

        if ax_right >= bx_left and a.v > b.v:
            self.collision.block_1 = a
            self.collision.block_2 = b
            if not self.first_collision_recorded:
                self.p_before = self.collision.total_momentum
                self.ek_before = self.collision.total_k_energy
            na, nb = self.collision.collide()
            na.x = b.x - wa / PIXELS_PER_M
            nb.x = b.x
            self.block_a, self.block_b = na, nb
            self.collision.block_1 = na
            self.collision.block_2 = nb
            if not self.first_collision_recorded:
                self.p_after = self.collision.total_momentum
                self.ek_after = self.collision.total_k_energy
                self.first_collision_recorded = True
            self.collision_count += 1
            self._flash = 18

            # 标记 刚发生碰撞
            self._just_collided = True
            self._last_collision_time = self._time

            if self._export_pending:
                self._export_pending = False
                self._do_export_after_collision()

        self.block_a.x += self.block_a.v * dt
        self.block_b.x += self.block_b.v * dt

        for blk in (self.block_a, self.block_b):
            w = u_block_w(blk)
            sx = sim_x(blk.x)
            if sx < SIM_PAD:
                blk.x = 0.0
                blk.v = abs(blk.v)
            right_limit = SIM_W - SIM_PAD - w
            if sx > right_limit:
                blk.x = (right_limit - ORIGIN_X) / PIXELS_PER_M
                blk.v = -abs(blk.v)

    # 重置场景
    def _reset(self):
        self.block_a = Block(self._init_a.x, self._init_a.m, self._init_a.v)
        self.block_b = Block(self._init_b.x, self._init_b.m, self._init_b.v)
        self.collision.block_1 = self.block_a
        self.collision.block_2 = self.block_b
        self.first_collision_recorded = False
        self.collision_count = 0
        self.p_before = None
        self.p_after = None
        self.ek_before = None
        self.ek_after = None
        self._flash = 0

        self.input_buffers = {
            "ma": self._format_var("ma", self.block_a.m),
            "va": self._format_var("va", self.block_a.v),
            "mb": self._format_var("mb", self.block_b.m),
            "vb": self._format_var("vb", self.block_b.v),
            "e": self._format_var("e", self.collision.e),
        }
        self.active_input = None
        self._paused_before_edit = False

        self.initial_p = self.collision.total_momentum
        self.initial_ek = self.collision.total_k_energy

        self._export_pending = False
        self._time = 0.0
        self._history.clear()

        # 清除一次性碰撞标志
        self._just_collided = False
        self._last_collision_time = None

    # 切换碰撞系数预设
    def _cycle_e(self):
        self._e_idx = (self._e_idx + 1) % len(self.E_PRESETS)
        new_e = self.E_PRESETS[self._e_idx]
        self.collision = D(self.block_a, self.block_b, e=new_e)
        self.input_buffers["e"] = self._format_var("e", self.collision.e)

        self._export_pending = False
        self._time = 0.0
        self._history.clear()
        self.first_collision_recorded = False
        self.collision_count = 0
        self.p_before = None
        self.p_after = None
        self.ek_before = None
        self.ek_after = None

    # 估算下一次碰撞时间，不能碰撞返回 None
    def _predict_collision_time(self) -> float | None:
        a = self.block_a
        b = self.block_b

        if a.v <= b.v:
            return None

        try:
            block_w_m = u_block_w(a) / PIXELS_PER_M
        except Exception:
            block_w_m = 0.5

        dist = b.x - a.x - block_w_m
        if dist <= 0:
            return 0.0
        rel_v = a.v - b.v
        if rel_v <= 0:
            return None
        t = dist / rel_v
        return t if t >= 0 else None

    # 记录数据至列表
    def _record_history(self):
        a = self.block_a
        b = self.block_b
        try:
            self.collision.block_1 = a
            self.collision.block_2 = b
            p_total = self.collision.total_momentum
            ek_total = self.collision.total_k_energy
        except Exception:
            p_total = a.moment + b.moment
            ek_total = a.k_energy + b.k_energy

        # 小数位数限制 round
        entry = {
            "t": round(self._time, 6),
            "xa": round(a.x, 6),
            "va": round(a.v, 6),
            "pa": round(a.moment, 6),
            "eka": round(a.k_energy, 6),
            "xb": round(b.x, 6),
            "vb": round(b.v, 6),
            "pb": round(b.moment, 6),
            "ekb": round(b.k_energy, 6),
            "p_total": round(p_total, 6),
            "ek_total": round(ek_total, 6),
            # 只有碰撞发生的那一帧为 True
            "collided": bool(self._just_collided),
        }
        self._history.append(entry)
        # 追加后立即清除一次性碰撞标志
        self._just_collided = False

    # 按 S 处理：设置/取消  或直接模拟导出图表
    def _export_charts(self):
        if self._export_pending:
            self._export_pending = False
            self._export_msg = "已取消导出等待"
            self._export_msg_timer = 2.0
            print("取消了等待中的导出")
            return

        pred = self._predict_collision_time()
        if pred is None:
            self._do_export_simulated()
            return

        self._export_pending = True
        self._export_pending_since = self._time
        self._export_pending_hist_len = len(self._history)
        self._export_msg = "等待碰撞后自动导出… (再按 S 取消)"
        self._export_msg_timer = 999.0
        print(f"已设置 t={self._time:.3f}s，预计碰撞约 {pred:.2f}s 后")

    # 碰撞发生后 截取数据 导出图标
    def _do_export_after_collision(self):
        # 日期缀名
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        outdir = Path("outputs") / f"export_{ts}"
        outdir.mkdir(parents=True, exist_ok=True)

        try:
            slice_start = self._export_pending_hist_len
            df = pd.DataFrame(self._history[slice_start:])
            if df.empty:
                df = pd.DataFrame(self._history)

            plot_history_df(df, outdir, scene=self)

            self._export_msg = f"已导出（{outdir.name}，{len(df)} 帧）"
            self._export_msg_timer = 4.0
            print(f"碰撞后导出至 {outdir} 共{len(df)}行")

        except Exception as exc:
            self._export_msg = f"导出失败: {exc}"
            self._export_msg_timer = 6.0
            print(f"导出失败: {exc}")

    # 模拟导出
    def _do_export_simulated(self):
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        outdir = Path("outputs") / f"export_{ts}"
        outdir.mkdir(parents=True, exist_ok=True)

        try:
            pred = self._predict_collision_time()
            tail = 2.0
            default_duration = 6.0
            duration = (
                default_duration if pred is None else max(default_duration, pred + tail)
            )

            paths = export_chart(
                self.block_a,
                self.block_b,
                e=self.collision.e,
                output_dir=outdir,
                duration=duration,
            )

            self._export_msg = (
                f"已导出 {len(paths)} 文件（{outdir.name}，{duration:.1f}s）"
            )
            self._export_msg_timer = 3.0
            print(f"导出 {len(paths)} 文件至：{outdir} (duration={duration:.2f}s)")
            for p in paths:
                print("  ", p)

        except Exception as exc:
            self._export_msg = f"导出失败: {exc}"
            self._export_msg_timer = 6.0
            print(f"导出失败: {exc}")

    # 获取输入窗口名
    def _current_value_str(self, field_name: str) -> str:
        match field_name:
            case "ma":
                return self._format_var("ma", self.block_a.m)
            case "va":
                return self._format_var("va", self.block_a.v)
            case "mb":
                return self._format_var("mb", self.block_b.m)
            case "vb":
                return self._format_var("vb", self.block_b.v)
            case "e":
                return self._format_var("e", self.collision.e)
            case _:
                return ""

    # 提交缓冲、更新参数
    def _commit_active_input(self):
        if not self.active_input:
            return

        field = self.active_input
        buf = self.input_buffers.get(field, "")

        try:
            val = float(buf)
        except Exception:
            self.input_buffers[field] = self._current_value_str(field)
            self.active_input = None
            self.paused = self._paused_before_edit
            return

        match field:
            case "ma":
                self.block_a.m = max(0.0001, val)
            case "va":
                self.block_a.v = val
            case "mb":
                self.block_b.m = max(0.0001, val)
            case "vb":
                self.block_b.v = val
            case "e":
                val = max(0.0, min(1.0, val))
                self.collision = D(self.block_a, self.block_b, e=val)
                self._time = 0.0
                self._history.clear()
                self.first_collision_recorded = False
                self.collision_count = 0
                self.p_before = None
                self.p_after = None
                self.ek_before = None
                self.ek_after = None
            case _:
                pass

        self.input_buffers[field] = self._current_value_str(field)
        self.active_input = None
        self.paused = self._paused_before_edit

        # 更新初始系统动、能量
        self.collision.block_1 = self.block_a
        self.collision.block_2 = self.block_b
        self.initial_p = self.collision.total_momentum
        self.initial_ek = self.collision.total_k_energy

        self._export_pending = False
        self._time = 0.0
        self._history.clear()
        self.first_collision_recorded = False
        self.collision_count = 0
        self.p_before = None
        self.p_after = None
        self.ek_before = None
        self.ek_after = None
