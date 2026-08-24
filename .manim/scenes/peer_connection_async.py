"""The async design of a peer connection -> raw/2026-08-24 12-50-23.

The narration describes this diagram entirely in words: split the stream into a
read half and a write half, hand each to its own task, wire them through two
channels to a task in the middle, and run a tokio::select! event loop there with
three arms -- timeout, read/respond, and tick.
"""

from manim import *
from catppuccin import LATTE, LatteScene, component, link, edge_label, audit_layout


class PeerAsync(LatteScene):
    def construct(self):
        title = self.title("one peer, two tasks, one event loop", size=30)
        self.add(title)

        peer = component("peer", LATTE["teal"], sub="remote", width=1.9, height=0.9, font_size=22)
        peer.move_to([-3.50, 1.85, 0])
        # It is the Framed<TcpStream, WireCodec> that gets split, not the raw
        # socket -- the codec is already in place by this point.
        stream = component("Framed<TcpStream>", LATTE["sapphire"], sub=".split()",
                           width=3.6, height=0.9, font_size=22)
        stream.move_to([0.30, 1.85, 0])
        wire = link(peer, stream, LATTE["teal"], both=True)

        self.play(FadeIn(peer, scale=0.85), FadeIn(stream, scale=0.85), run_time=0.6)
        self.play(GrowArrow(wire), run_time=0.4)

        reader = component("reader task", LATTE["blue"], sub="read half", width=3.0, height=0.95, font_size=22)
        reader.move_to([-2.30, -0.15, 0])
        writer = component("writer task", LATTE["blue"], sub="write half", width=3.0, height=0.95, font_size=22)
        writer.move_to([2.30, -0.15, 0])

        to_reader = link(stream, reader, LATTE["blue"])
        to_writer = link(stream, writer, LATTE["blue"])
        split_note = self.caption("each half gets its own task", size=19)
        split_note.next_to(stream, UP, buff=0.30)

        self.play(FadeIn(split_note), run_time=0.4)
        self.play(FadeIn(reader, scale=0.85), FadeIn(writer, scale=0.85),
                  GrowArrow(to_reader), GrowArrow(to_writer), run_time=0.9)

        # The event loop task in the middle -- the two tasks never talk directly.
        loop_box = RoundedRectangle(
            corner_radius=0.16, width=7.6, height=1.75,
            stroke_color=LATTE["mauve"], stroke_width=2.8,
            fill_color=LATTE["mauve"], fill_opacity=0.10,
        ).move_to([0.00, -2.65, 0])
        loop_name = Text("event loop", font="Fira Code", font_size=23, color=LATTE["text"])
        loop_sub = Text("tokio::select!", font="Fira Code", font_size=19, color=LATTE["mauve"])
        VGroup(loop_name, loop_sub).arrange(DOWN, buff=0.08).move_to(loop_box.get_top() + DOWN * 0.48)

        arms = VGroup()
        # Four arms, matching src/peer_connection/request_manager.rs -- there are
        # two distinct timeouts, not one.
        for name, key in (("idle timeout", "yellow"), ("request timeout", "maroon"),
                          ("availability tick", "peach"), ("incoming msg", "blue")):
            pill = RoundedRectangle(
                corner_radius=0.18, width=1.78, height=0.5,
                stroke_color=LATTE[key], stroke_width=2.0,
                fill_color=LATTE[key], fill_opacity=0.14,
            )
            lbl = Text(name, font="Fira Code", font_size=15, color=LATTE["text"])
            if lbl.width > 1.58:
                lbl.scale(1.58 / lbl.width)
            arms.add(VGroup(pill, lbl.move_to(pill)))
        arms.arrange(RIGHT, buff=0.14).move_to(loop_box.get_bottom() + UP * 0.42)

        ch_in = link(reader, loop_box, LATTE["green"])
        ch_out = link(loop_box, writer, LATTE["green"])
        ch_in_lbl = edge_label("mpsc", ch_in, color=LATTE["green"], shift=LEFT * 0.72)
        ch_out_lbl = edge_label("mpsc", ch_out, color=LATTE["green"], shift=RIGHT * 0.72)

        self.play(FadeOut(split_note), FadeIn(loop_box), FadeIn(loop_name), FadeIn(loop_sub), run_time=0.7)
        self.play(GrowArrow(ch_in), GrowArrow(ch_out),
                  FadeIn(ch_in_lbl), FadeIn(ch_out_lbl), run_time=0.7)
        self.play(FadeIn(arms, shift=UP * 0.12), run_time=0.6)

        # Each arm fires in turn -- the three things select! buys you.
        for arm, key in zip(arms, ("yellow", "maroon", "peach", "blue")):
            self.play(Indicate(arm, color=LATTE[key], scale_factor=1.12), run_time=0.65)

        audit_layout({
            "title": title, "peer": peer, "stream": stream,
            "reader": reader, "writer": writer, "loop": loop_box,
            "loop_name": loop_name, "loop_sub": loop_sub, "arms": arms,
            "ch_in_lbl": ch_in_lbl, "ch_out_lbl": ch_out_lbl,
        }, allow=[("loop", "loop_name"), ("loop", "loop_sub"), ("loop", "arms")])

        self.wait(1.2)
