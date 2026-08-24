"""Endgame mode -- the next-episode teaser -> raw/2026-08-24 12-58-28.

"By the end of the download, the number of peers are more than number of blocks
left... slow peers would actually hijack the whole download. To solve this we
ask multiple peers to give the same block and take the block from the fastest."
"""

from manim import *
from catppuccin import LATTE, LatteScene, clamp_to_frame, audit_layout

TOTAL, DONE = 24, 21


class EndgameMode(LatteScene):
    def construct(self):
        title = self.title("endgame: slow peers stop stalling the finish", size=27)
        self.add(title)

        # Download is nearly complete -- three blocks outstanding.
        cells = VGroup(*[
            Rectangle(width=0.42, height=0.62,
                      stroke_color=LATTE["green"] if i < DONE else LATTE["overlay0"],
                      stroke_width=1.6,
                      fill_color=LATTE["green"] if i < DONE else LATTE["surface1"],
                      fill_opacity=0.55 if i < DONE else 0.4)
            for i in range(TOTAL)
        ]).arrange(RIGHT, buff=0.055).move_to([0, 1.95, 0])
        bar_lbl = self.caption(f"{DONE}/{TOTAL} blocks done  --  3 left, and plenty of peers idle", size=19)
        bar_lbl.next_to(cells, UP, buff=0.22)
        self.play(FadeIn(cells), FadeIn(bar_lbl), run_time=0.7)

        left = VGroup(*cells[DONE:])
        self.play(*[Indicate(c, color=LATTE["yellow"], scale_factor=1.2) for c in left], run_time=0.7)

        # One block per peer -- and the slow peer is holding the last one.
        def lane(name, accent, speed):
            box = RoundedRectangle(corner_radius=0.14, width=2.05, height=0.62,
                                   stroke_color=LATTE[accent], stroke_width=2.2,
                                   fill_color=LATTE[accent], fill_opacity=0.12)
            txt = Text(f"{name}  {speed}", font="Fira Code", font_size=16, color=LATTE["text"])
            if txt.width > 1.8:
                txt.scale(1.8 / txt.width)
            return VGroup(box, txt.move_to(box))

        lanes = VGroup(
            lane("peer 1", "green", "fast"),
            lane("peer 2", "yellow", "SLOW"),
            lane("peer 3", "green", "fast"),
        ).arrange(RIGHT, buff=0.16).move_to([2.78, -0.60, 0])
        self.play(FadeIn(lanes, shift=UP * 0.15), run_time=0.6)

        naive = self.caption("one block each -- the slow peer\nstalls the whole download", size=19)
        naive.move_to([-3.30, -0.60, 0])
        clamp_to_frame(naive)
        self.play(FadeIn(naive), run_time=0.5)

        # peers 1 and 3 finish, peer 2 hangs.
        self.play(cells[DONE].animate.set_stroke(LATTE["green"]).set_fill(LATTE["green"], opacity=0.55),
                  cells[DONE + 2].animate.set_stroke(LATTE["green"]).set_fill(LATTE["green"], opacity=0.55),
                  run_time=0.7)
        stall = Text("waiting...", font="Fira Code", font_size=20, color=LATTE["yellow"], weight=BOLD)
        stall.next_to(lanes[1], DOWN, buff=0.30)
        self.play(FadeIn(stall), Indicate(cells[DONE + 1], color=LATTE["yellow"], scale_factor=1.25),
                  run_time=0.8)
        self.wait(0.6)

        # Endgame: ask everyone for the same block, take whichever lands first.
        self.play(FadeOut(naive), FadeOut(stall), run_time=0.4)
        switch = Text("endgame mode", font="Fira Code", font_size=25,
                      color=LATTE["mauve"], weight=BOLD)
        switch.move_to([-3.30, 0.55, 0])
        clamp_to_frame(switch)
        detail = self.caption("request the SAME block from every peer", size=19)
        detail.next_to(switch, DOWN, buff=0.26)
        clamp_to_frame(detail)
        self.play(FadeIn(switch), FadeIn(detail), run_time=0.6)

        target = cells[DONE + 1]
        reqs = VGroup(*[
            Arrow(l.get_top(), target.get_bottom(), buff=0.12, stroke_width=2.6,
                  color=LATTE["mauve"], max_tip_length_to_length_ratio=0.06, tip_length=0.16)
            for l in lanes
        ])
        self.play(*[GrowArrow(a) for a in reqs], run_time=0.8)

        winner = Text("peer 3 first -- cancel the rest", font="Fira Code", font_size=19,
                      color=LATTE["green"], weight=BOLD)
        winner.move_to([-3.30, -1.85, 0])
        clamp_to_frame(winner)
        self.play(
            target.animate.set_stroke(LATTE["green"]).set_fill(LATTE["green"], opacity=0.55),
            reqs[2].animate.set_color(LATTE["green"]).set_stroke(width=3.4),
            reqs[0].animate.set_color(LATTE["overlay0"]).set_stroke(opacity=0.35),
            reqs[1].animate.set_color(LATTE["overlay0"]).set_stroke(opacity=0.35),
            FadeIn(winner), run_time=0.9,
        )
        done = Text(f"{TOTAL}/{TOTAL}  complete", font="Fira Code", font_size=24,
                    color=LATTE["green"], weight=BOLD)
        done.move_to([0, -3.15, 0])
        self.play(FadeIn(done), run_time=0.5)

        audit_layout({
            "title": title, "cells": cells, "bar_lbl": bar_lbl, "lanes": lanes,
            "switch": switch, "detail": detail, "winner": winner, "done": done,
        })

        self.wait(1.3)
