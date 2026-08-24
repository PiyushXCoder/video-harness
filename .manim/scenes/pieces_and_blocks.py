"""Pieces, blocks and hash verification -> raw/2026-08-24 12-47-08.

"The data is divided into the pieces, and then those pieces are divided into the
blocks... you can get the hash for that, you can verify those pieces. If pieces
doesn't verify, you will just reject it."
"""

from manim import *
from catppuccin import LATTE, LatteScene, audit_layout

N_PIECES = 8
N_BLOCKS = 8


class PiecesAndBlocks(LatteScene):
    def construct(self):
        title = self.title("pieces, blocks, and the hash check", size=30)
        self.add(title)

        # The whole file, then the same bar broken into pieces.
        bar = Rectangle(width=10.4, height=0.9, stroke_color=LATTE["overlay1"],
                        stroke_width=2.2, fill_color=LATTE["surface1"], fill_opacity=0.55)
        bar.move_to([0, 2.05, 0])
        bar_lbl = self.caption("the file", size=20)
        bar_lbl.next_to(bar, UP, buff=0.2)
        self.play(FadeIn(bar), FadeIn(bar_lbl), run_time=0.6)

        pieces = VGroup(*[
            Rectangle(width=1.2, height=0.9, stroke_color=LATTE["blue"], stroke_width=2.2,
                      fill_color=LATTE["blue"], fill_opacity=0.14)
            for _ in range(N_PIECES)
        ]).arrange(RIGHT, buff=0.1).move_to(bar)
        piece_lbl = self.caption("pieces  --  512 KB each, one SHA-1 per piece", size=19)
        piece_lbl.next_to(pieces, UP, buff=0.2)

        self.play(FadeOut(bar), FadeOut(bar_lbl), FadeIn(pieces), FadeIn(piece_lbl), run_time=0.8)

        # One piece opens up into its blocks.
        target = pieces[2]
        self.play(Indicate(target, color=LATTE["blue"], scale_factor=1.15), run_time=0.6)

        blocks = VGroup(*[
            Rectangle(width=0.92, height=0.8, stroke_color=LATTE["sapphire"], stroke_width=2.0,
                      fill_color=LATTE["sapphire"], fill_opacity=0.12)
            for _ in range(N_BLOCKS)
        ]).arrange(RIGHT, buff=0.12).move_to([0, 0.15, 0])
        block_lbl = self.caption("blocks  --  16 KiB each, this is what you request", size=19)
        block_lbl.next_to(blocks, DOWN, buff=0.24)

        fan = VGroup(
            Line(target.get_corner(DL), blocks.get_corner(UL),
                 stroke_color=LATTE["overlay0"], stroke_width=1.6),
            Line(target.get_corner(DR), blocks.get_corner(UR),
                 stroke_color=LATTE["overlay0"], stroke_width=1.6),
        )
        self.play(Create(fan), run_time=0.5)
        self.play(FadeIn(blocks), FadeIn(block_lbl), run_time=0.6)

        # Blocks arrive one by one.
        self.play(*[b.animate.set_fill(LATTE["sapphire"], opacity=0.55) for b in blocks],
                  lag_ratio=0.14, run_time=1.3)

        # Verify: hash matches -> keep.
        check = Text("sha1(piece) == expected", font="Fira Code", font_size=22, color=LATTE["green"])
        check.move_to([0, -1.7, 0])
        ok = Text("keep it", font="Fira Code", font_size=24, color=LATTE["green"], weight=BOLD)
        ok.move_to([0, -2.65, 0])
        self.play(FadeIn(check), run_time=0.5)
        self.play(target.animate.set_stroke(LATTE["green"]).set_fill(LATTE["green"], opacity=0.5),
                  FadeIn(ok), run_time=0.7)
        self.wait(0.7)

        # A different piece fails -> throw it away and ask again.
        bad = pieces[5]
        fail = Text("sha1(piece) != expected", font="Fira Code", font_size=22, color=LATTE["red"])
        fail.move_to(check)
        reject = Text("reject, request it again", font="Fira Code", font_size=24,
                      color=LATTE["red"], weight=BOLD)
        reject.move_to(ok)

        self.play(FadeOut(ok), FadeOut(check), FadeOut(blocks), FadeOut(block_lbl), FadeOut(fan),
                  run_time=0.5)
        self.play(Indicate(bad, color=LATTE["red"], scale_factor=1.15),
                  FadeIn(fail), run_time=0.7)
        self.play(bad.animate.set_stroke(LATTE["red"]).set_fill(LATTE["red"], opacity=0.45),
                  FadeIn(reject), run_time=0.6)
        self.play(bad.animate.set_stroke(LATTE["overlay0"]).set_fill(LATTE["surface1"], opacity=0.4),
                  run_time=0.6)

        audit_layout({
            "title": title, "pieces": pieces, "piece_lbl": piece_lbl,
            "fail": fail, "reject": reject,
        })

        self.wait(1.2)
