from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, TYPE_CHECKING, List

import pygame as pg
import pandas as pd

from momentum_lab.ui.const import *
from momentum_lab.ui.surface import *

if TYPE_CHECKING:
    from momentum_lab.ui.scene import Scene


# 计算面板布局并写回 scene.box_rects .hit_rects
def compute_panel_layout(scene: "Scene", fonts: Dict[str, pg.font.Font]) -> None:
    px = SIM_W
    pad = 20
    content_w = PANEL_W - pad * 2
    col_gap = 20
    col_total_w = (content_w - col_gap) // 2

    label_w_candidates = [
        fonts["small"].render("质量", True, C(TEXT_SEC_S)).get_width(),
        fonts["small"].render("速度", True, C(TEXT_SEC_S)).get_width(),
    ]
    label_max_w = max(label_w_candidates) + 8

    unit_examples = ["kg", "m/s", f"({scene.collision.kind.label})"]
    unit_width = max(
        (
            fonts["small"].render(u, True, C(TEXT_SEC_S)).get_width()
            for u in unit_examples
        )
    )
    unit_width = max(unit_width, 36)

    box_w = max(MIN_BOX_W, col_total_w - unit_width - UNIT_PADDING)
    cap_label_w = min(label_max_w, content_w - box_w - unit_width - UNIT_PADDING - 8)
    left_x = px + pad

    cy = 24
    cy += fonts["h2"].get_height() + 6

    e_box_x = px + pad + content_w - box_w - unit_width - UNIT_PADDING
    scene.box_rects["e"] = pg.Rect(e_box_x, cy, box_w, ROW_H)
    scene.hit_rects["e"] = pg.Rect(
        e_box_x, cy, box_w + unit_width + UNIT_PADDING + HIT_EXTRA, ROW_H
    )

    cy += ROW_H + ROW_GAP + 6
    cy += fonts["h2"].get_height() + 6

    scene.box_rects["ma"] = pg.Rect(left_x + cap_label_w, cy, box_w, ROW_H)
    scene.hit_rects["ma"] = pg.Rect(
        left_x + cap_label_w,
        cy,
        box_w + unit_width + UNIT_PADDING + HIT_EXTRA,
        ROW_H,
    )

    cy += ROW_H + ROW_GAP
    scene.box_rects["va"] = pg.Rect(left_x + cap_label_w, cy, box_w, ROW_H)
    scene.hit_rects["va"] = pg.Rect(
        left_x + cap_label_w,
        cy,
        box_w + unit_width + UNIT_PADDING + HIT_EXTRA,
        ROW_H,
    )

    cy += ROW_H + ROW_GAP + 6
    cy += fonts["h2"].get_height() + 6

    scene.box_rects["mb"] = pg.Rect(left_x + cap_label_w, cy, box_w, ROW_H)
    scene.hit_rects["mb"] = pg.Rect(
        left_x + cap_label_w,
        cy,
        box_w + unit_width + UNIT_PADDING + HIT_EXTRA,
        ROW_H,
    )

    cy += ROW_H + ROW_GAP
    scene.box_rects["vb"] = pg.Rect(left_x + cap_label_w, cy, box_w, ROW_H)
    scene.hit_rects["vb"] = pg.Rect(
        left_x + cap_label_w,
        cy,
        box_w + unit_width + UNIT_PADDING + HIT_EXTRA,
        ROW_H,
    )


# 地面
def draw_track(screen: pg.Surface, fonts: Dict[str, pg.font.Font]) -> None:
    pg.draw.line(
        screen,
        C(FLOOR_COL),
        (SIM_PAD - 10, FLOOR_Y),
        (SIM_W - SIM_PAD + 10, FLOOR_Y),
        2,
    )
    for m in range(0, 9):
        gx = sim_x(m)
        pg.draw.line(screen, C(FLOOR_COL), (gx, FLOOR_Y), (gx, FLOOR_Y + 8), 1)
        lbl = fonts["small"].render(str(m), True, C(TEXT_SEC_S))
        screen.blit(lbl, (gx - lbl.get_width() // 2, FLOOR_Y + 11))
    unit = fonts["small"].render("m", True, C(TEXT_SEC_S))
    screen.blit(unit, (SIM_W - SIM_PAD + 14, FLOOR_Y + 11))


# 绘制物块.碰撞闪光 、速度数值
def draw_blocks(
    screen: pg.Surface, fonts: Dict[str, pg.font.Font], scene: "Scene"
) -> None:
    for blk, col_hex, col_dim_hex, label in (
        (scene.block_a, COL_A, COL_A_DIM, "A"),
        (scene.block_b, COL_B, COL_B_DIM, "B"),
    ):
        col_color = C(col_hex)
        col_dim_color = C(col_dim_hex)

        w = u_block_w(blk)
        h = u_block_h(blk)
        sx = sim_x(blk.x)
        sy = FLOOR_Y - h

        if getattr(scene, "_flash", 0) > 0:
            alpha = min(255, scene._flash * 14)
            glow = pg.Surface((w + 6, h + 6), pg.SRCALPHA)
            tmp = C(col_hex)
            tmp.a = alpha
            glow.fill(tmp)
            screen.blit(glow, (sx - 3, sy - 3))

        body = pg.Surface((w, h), pg.SRCALPHA)
        # 渐变
        for row in range(h):
            t = row / h
            r = int(col_color.r * (1 - t * 0.35) + col_dim_color.r * t * 0.35)
            g = int(col_color.g * (1 - t * 0.35) + col_dim_color.g * t * 0.35)
            b_ = int(col_color.b * (1 - t * 0.35) + col_dim_color.b * t * 0.35)
            pg.draw.line(body, (r, g, b_), (0, row), (w, row))
        screen.blit(body, (sx, sy))

        lbl = fonts["h2"].render(label, True, C(MAIN))
        mlbl = fonts["small"].render(f"{blk.m} kg", True, C(MAIN))
        screen.blit(lbl, (sx + w // 2 - lbl.get_width() // 2, sy + 10))
        screen.blit(mlbl, (sx + w // 2 - mlbl.get_width() // 2, sy + 32))

        u_draw_velocity_arrow(screen, blk, sx, sy, w, C(col_hex))

        vtext = fonts["small"].render(f"{blk.v:.2f} m/s", True, C(col_hex))
        screen.blit(vtext, (sx + w // 2 - vtext.get_width() // 2, FLOOR_Y - h - 40))


# 数据面板
def draw_panel(
    screen: pg.Surface, fonts: Dict[str, pg.font.Font], scene: "Scene"
) -> None:
    px = SIM_W
    pg.draw.rect(screen, C(PANEL_BG), (px, 0, PANEL_W, H))
    pg.draw.line(screen, C(DIVIDER), (px, 0), (px, H), 1)

    pad = 20
    cy = 24

    cy = u_panel_heading(screen, fonts, px + pad, cy, "实验参数", C(TEXT_HEAD))
    cy += 8

    if getattr(scene, "_export_msg_timer", 0) > 0 and getattr(scene, "_export_msg", ""):
        msg_surf = fonts["small"].render(scene._export_msg, True, C(AMBER))
        screen.blit(msg_surf, (px + pad, cy))
        cy += msg_surf.get_height() + 6

    content_w = PANEL_W - pad * 2
    col_gap = 20
    col_total_w = (content_w - col_gap) // 2

    label_w_candidates = [
        fonts["small"].render("质量", True, C(TEXT_SEC_S)).get_width(),
        fonts["small"].render("速度", True, C(TEXT_SEC_S)).get_width(),
    ]
    label_max_w = max(label_w_candidates) + 8

    units = ["kg", "m/s", f"({scene.collision.kind.label})"]
    unit_width = max(
        (fonts["small"].render(u, True, C(TEXT_SEC_S)).get_width() for u in units)
    )
    unit_width = max(unit_width, 36)

    box_w = max(MIN_BOX_W, col_total_w - unit_width - UNIT_PADDING)
    cap_label_w = min(label_max_w, content_w - box_w - unit_width - UNIT_PADDING - 8)
    left_x = px + pad

    cy += ROW_H
    e_label_s = fonts["small"].render("碰撞系数", True, C(TEXT_SEC_S))
    screen.blit(e_label_s, (left_x - 10, cy + (ROW_H - e_label_s.get_height()) // 2))

    e_box_x = px + pad + content_w - box_w - unit_width - UNIT_PADDING
    e_box_rect = pg.Rect(e_box_x, cy, box_w, ROW_H)
    e_hit_rect = pg.Rect(
        e_box_x, cy, box_w + unit_width + UNIT_PADDING + HIT_EXTRA, ROW_H
    )
    scene.box_rects["e"] = e_box_rect
    scene.hit_rects["e"] = e_hit_rect

    pg.draw.rect(screen, C(BOTTON_COL), e_box_rect, border_radius=6)
    pg.draw.rect(screen, C(DIVIDER), e_box_rect, 1, border_radius=6)
    if scene.active_input == "e":
        pg.draw.rect(screen, C("#2878DC"), e_box_rect, 2, border_radius=6)

    if scene.active_input == "e":
        disp = scene.input_buffers.get("e", "")
        if getattr(scene, "_cursor_visible", True):
            disp = disp + "|"
    else:
        disp = scene._current_value_str("e")
    clip = screen.get_clip()
    screen.set_clip(e_box_rect.inflate(-4, 0))
    ds = fonts["small"].render(disp, True, C(TEXT_PRI))
    screen.blit(
        ds,
        (
            e_box_rect.right - BOX_INNER_PADDING - ds.get_width(),
            e_box_rect.y + (ROW_H - ds.get_height()) // 2,
        ),
    )
    screen.set_clip(clip)

    kind_label_s = fonts["small"].render(
        f"({scene.collision.kind.label})", True, C(TEXT_SEC)
    )
    kind_x = min(
        px + PANEL_W - pad - kind_label_s.get_width(), e_box_rect.right + UNIT_PADDING
    )
    screen.blit(
        kind_label_s, (kind_x, e_box_rect.y + (ROW_H - kind_label_s.get_height()) // 2)
    )

    cy += ROW_H + ROW_GAP + 6

    heading_a = fonts["h2"].render("物块 A", True, C(COL_A))
    screen.blit(heading_a, (left_x, cy))
    cy += heading_a.get_height() + HEADING_FIELD_GAP

    ma_label_s = fonts["small"].render("质量", True, C(TEXT_SEC_S))
    label_x = left_x
    screen.blit(ma_label_s, (label_x, cy + (ROW_H - ma_label_s.get_height()) // 2))
    ma_box_x = left_x + cap_label_w
    ma_box = pg.Rect(ma_box_x, cy, box_w, ROW_H)
    scene.box_rects["ma"] = ma_box
    scene.hit_rects["ma"] = pg.Rect(
        ma_box.x, ma_box.y, box_w + unit_width + UNIT_PADDING + HIT_EXTRA, ROW_H
    )
    pg.draw.rect(screen, C(BOTTON_COL), ma_box, border_radius=6)
    pg.draw.rect(screen, C(DIVIDER), ma_box, 1, border_radius=6)
    if scene.active_input == "ma":
        pg.draw.rect(screen, C("#2878DC"), ma_box, 2, border_radius=6)
    if scene.active_input == "ma":
        mdisp = scene.input_buffers.get("ma", "") + (
            "|" if getattr(scene, "_cursor_visible", True) else ""
        )
    else:
        mdisp = scene._current_value_str("ma")
    clip = screen.get_clip()
    screen.set_clip(ma_box.inflate(-4, 0))
    mds = fonts["small"].render(mdisp, True, C(COL_A))
    screen.blit(
        mds,
        (
            ma_box.right - BOX_INNER_PADDING - mds.get_width(),
            ma_box.y + (ROW_H - mds.get_height()) // 2,
        ),
    )
    screen.set_clip(clip)
    unit_s = fonts["small"].render("kg", True, C(TEXT_SEC))
    screen.blit(
        unit_s,
        (ma_box.right + UNIT_PADDING, ma_box.y + (ROW_H - unit_s.get_height()) // 2),
    )

    cy += ROW_H + ROW_GAP

    va_label_s = fonts["small"].render("速度", True, C(TEXT_SEC_S))
    screen.blit(va_label_s, (label_x, cy + (ROW_H - va_label_s.get_height()) // 2))
    va_box_x = left_x + cap_label_w
    va_box = pg.Rect(va_box_x, cy, box_w, ROW_H)
    scene.box_rects["va"] = va_box
    scene.hit_rects["va"] = pg.Rect(
        va_box.x, va_box.y, box_w + unit_width + UNIT_PADDING + HIT_EXTRA, ROW_H
    )
    pg.draw.rect(screen, C(BOTTON_COL), va_box, border_radius=6)
    pg.draw.rect(screen, C(DIVIDER), va_box, 1, border_radius=6)
    if scene.active_input == "va":
        pg.draw.rect(screen, C("#2878DC"), va_box, 2, border_radius=6)
    if scene.active_input == "va":
        # | 光标
        vdisp = scene.input_buffers.get("va", "") + (
            "|" if getattr(scene, "_cursor_visible", True) else ""
        )
    else:
        vdisp = scene._current_value_str("va")
    clip = screen.get_clip()
    screen.set_clip(va_box.inflate(-4, 0))
    vds = fonts["small"].render(vdisp, True, C(COL_A))
    screen.blit(
        vds,
        (
            va_box.right - BOX_INNER_PADDING - vds.get_width(),
            va_box.y + (ROW_H - vds.get_height()) // 2,
        ),
    )
    screen.set_clip(clip)
    unit_vs = fonts["small"].render("m/s", True, C(TEXT_SEC))
    screen.blit(
        unit_vs,
        (va_box.right + UNIT_PADDING, va_box.y + (ROW_H - unit_vs.get_height()) // 2),
    )

    cy += ROW_H + ROW_GAP + 6

    heading_b = fonts["h2"].render("物块 B", True, C(COL_B))
    screen.blit(heading_b, (left_x, cy))
    cy += heading_b.get_height() + HEADING_FIELD_GAP

    mb_label_s = fonts["small"].render("质量", True, C(TEXT_SEC_S))
    screen.blit(mb_label_s, (label_x, cy + (ROW_H - mb_label_s.get_height()) // 2))
    mb_box_x = left_x + cap_label_w
    mb_box = pg.Rect(mb_box_x, cy, box_w, ROW_H)
    scene.box_rects["mb"] = mb_box
    scene.hit_rects["mb"] = pg.Rect(
        mb_box.x, mb_box.y, box_w + unit_width + UNIT_PADDING + HIT_EXTRA, ROW_H
    )
    pg.draw.rect(screen, C(BOTTON_COL), mb_box, border_radius=6)
    pg.draw.rect(screen, C(DIVIDER), mb_box, 1, border_radius=6)
    if scene.active_input == "mb":
        pg.draw.rect(screen, C("#2878DC"), mb_box, 2, border_radius=6)
    if scene.active_input == "mb":
        mbdisp = scene.input_buffers.get("mb", "") + (
            "|" if getattr(scene, "_cursor_visible", True) else ""
        )
    else:
        mbdisp = scene._current_value_str("mb")
    clip = screen.get_clip()
    screen.set_clip(mb_box.inflate(-4, 0))
    mbds = fonts["small"].render(mbdisp, True, C(COL_B))
    screen.blit(
        mbds,
        (
            mb_box.right - BOX_INNER_PADDING - mbds.get_width(),
            mb_box.y + (ROW_H - mbds.get_height()) // 2,
        ),
    )
    screen.set_clip(clip)
    unit_mb = fonts["small"].render("kg", True, C(TEXT_SEC))
    screen.blit(
        unit_mb,
        (mb_box.right + UNIT_PADDING, mb_box.y + (ROW_H - unit_mb.get_height()) // 2),
    )

    cy += ROW_H + ROW_GAP

    vb_label_s = fonts["small"].render("速度", True, C(TEXT_SEC_S))
    screen.blit(vb_label_s, (label_x, cy + (ROW_H - vb_label_s.get_height()) // 2))
    vb_box_x = left_x + cap_label_w
    vb_box = pg.Rect(vb_box_x, cy, box_w, ROW_H)
    scene.box_rects["vb"] = vb_box
    scene.hit_rects["vb"] = pg.Rect(
        vb_box.x, vb_box.y, box_w + unit_width + UNIT_PADDING + HIT_EXTRA, ROW_H
    )
    pg.draw.rect(screen, C(BOTTON_COL), vb_box, border_radius=6)
    pg.draw.rect(screen, C(DIVIDER), vb_box, 1, border_radius=6)
    if scene.active_input == "vb":
        pg.draw.rect(screen, C("#2878DC"), vb_box, 2, border_radius=6)
    if scene.active_input == "vb":
        vbdisp = scene.input_buffers.get("vb", "") + (
            "|" if getattr(scene, "_cursor_visible", True) else ""
        )
    else:
        vbdisp = scene._current_value_str("vb")
    clip = screen.get_clip()
    screen.set_clip(vb_box.inflate(-4, 0))
    vbds = fonts["small"].render(vbdisp, True, C(COL_B))
    screen.blit(
        vbds,
        (
            vb_box.right - BOX_INNER_PADDING - vbds.get_width(),
            vb_box.y + (ROW_H - vbds.get_height()) // 2,
        ),
    )
    screen.set_clip(clip)
    unit_vb = fonts["small"].render("m/s", True, C(TEXT_SEC))
    screen.blit(
        unit_vb,
        (vb_box.right + UNIT_PADDING, vb_box.y + (ROW_H - unit_vb.get_height()) // 2),
    )

    cy = max(cy + ROW_H + ROW_GAP + 6, vb_box.bottom + 6)
    pg.draw.line(screen, C(DIVIDER), (px + pad, cy), (px + PANEL_W - pad, cy))
    cy += 18

    title_s = fonts["h2"].render("系统总能", True, C(TEXT_HEAD))
    screen.blit(title_s, (left_x, cy))
    cy += title_s.get_height() + 12

    label_texts = ["总动能", "总动量"]
    label_w = (
        max(
            fonts["small"].render(t, True, C(TEXT_SEC_S)).get_width()
            for t in label_texts
        )
        + 8
    )
    remaining_w = content_w - label_w
    col_w = (remaining_w - VAL_COL_GAP) // 2
    col1_x = left_x + label_w
    col2_x = col1_x + col_w + VAL_COL_GAP

    hdr_init = fonts["small"].render("初始", True, C(TEXT_SEC_S))
    hdr_now = fonts["small"].render("当前", True, C(TEXT_SEC_S))
    screen.blit(hdr_init, (col1_x + (col_w - hdr_init.get_width()) // 2, cy))
    screen.blit(hdr_now, (col2_x + (col_w - hdr_now.get_width()) // 2, cy))
    cy += hdr_init.get_height() + 10

    ek_label = fonts["small"].render("总动能", True, C(TEXT_SEC_S))
    ek_init_s = fonts["small"].render(f"{scene.initial_ek:.2f} J", True, C(TEXT_PRI))
    ek_now_s = fonts["small"].render(
        f"{scene.collision.total_k_energy:.2f} J", True, C(TEXT_PRI)
    )
    screen.blit(ek_label, (left_x, cy))
    screen.blit(ek_init_s, (col1_x + (col_w - ek_init_s.get_width()) // 2, cy))
    screen.blit(ek_now_s, (col2_x + (col_w - ek_now_s.get_width()) // 2, cy))
    cy += ek_init_s.get_height() + 14

    p_label = fonts["small"].render("总动量", True, C(TEXT_SEC_S))
    p_init_s = fonts["small"].render(f"{scene.initial_p:.2f} kg·m/s", True, C(TEXT_PRI))
    p_now_s = fonts["small"].render(
        f"{scene.collision.total_momentum:.2f} kg·m/s", True, C(TEXT_PRI)
    )
    screen.blit(p_label, (left_x, cy))
    screen.blit(p_init_s, (col1_x + (col_w - p_init_s.get_width()) // 2, cy))
    screen.blit(p_now_s, (col2_x + (col_w - p_now_s.get_width()) // 2, cy))
    cy += p_init_s.get_height() + 14


# 提示栏
def draw_hintbar(screen: pg.Surface, fonts: Dict[str, pg.font.Font]) -> None:
    by = H - HINT_H
    pg.draw.rect(screen, C(BUTTON_COL), (0, by, W, HINT_H))
    pg.draw.line(screen, C(DIVIDER), (0, by), (W, by))

    keys = [
        ("SPACE", "暂停/继续"),
        ("R", "重置"),
        ("E", "切换碰撞类型"),
        ("S", "导出图表/CSV"),
        ("Q", "退出"),
    ]
    cx = 20
    for k, desc in keys:
        kb = fonts["small"].render(k, True, C(TEXT_HEAD))
        kw = kb.get_width() + 14
        kh = kb.get_height() + 6
        ky = by + (HINT_H - kh) // 2
        pg.draw.rect(screen, C(BOTTON_COL), (cx, ky, kw, kh), border_radius=4)
        pg.draw.rect(screen, C("#3C4155"), (cx, ky, kw, kh), width=1, border_radius=4)
        screen.blit(kb, (cx + 7, ky + 3))
        cx += kw + 6
        db = fonts["small"].render(desc, True, C(TEXT_SEC_S))
        screen.blit(db, (cx, by + (HINT_H - db.get_height()) // 2))
        cx += db.get_width() + 28


# 暂停遮罩
def draw_paused_overlay(screen: pg.Surface, fonts: Dict[str, pg.font.Font]) -> None:
    overlay = pg.Surface((SIM_W, SIM_H), pg.SRCALPHA)
    overlay.fill((0, 0, 0, 80))
    screen.blit(overlay, (0, 0))
    s = fonts["h1"].render("已暂停", True, C(AMBER))
    screen.blit(
        s, (SIM_W // 2 - s.get_width() // 2, FLOOR_Y // 2 - s.get_height() // 2)
    )


# 导出图表
def plot_history_df(
    df: pd.DataFrame, outdir: Path, scene: Optional["Scene"] = None
) -> List[Path]:
    from momentum_lab.model.block import CollisionType
    from momentum_lab.export.chart import plot_df

    outdir.mkdir(parents=True, exist_ok=True)
    csv_path = outdir / "collision_history.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig", float_format="%.6f")
    pic_path = outdir / "combined_chart.png"
    title = None
    if scene is not None:
        title = f"{CollisionType.from_e(scene.collision.e).label}  ($e={scene.collision.e}$)"
    plot_df(
        df,
        pic_path,
        title=title,
        block_a=(scene.block_a if scene else None),
        block_b=(scene.block_b if scene else None),
    )
    return [pic_path, csv_path]
