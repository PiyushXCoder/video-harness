"""Architecture of the torrent client, revealed one component at a time.

Laid out by CONSTRAINT, not coordinates (layout guideline S2/S28): the full graph
is arranged relationally ONCE -- rows of siblings, rows stacked, the whole thing
fitted into the content region -- and each clip then reveals a subset of it.

That satisfies two rules that pull against each other:
  S2  no arbitrary coordinates -- there is not one positional literal below
  S7/S19 established objects never move, so the viewer's spatial map survives
        cuts between clips

Component names and topology are checked against the real implementation at
~/Projects/dhaar-torrent (README "Architecture" plus the src/ module tree), not
against the narration alone -- the transcript never mentions request_manager,
and what it calls the "disk writer" is PieceWriter inside piece_manager.

Focus follows S16: the component a clip introduces is drawn at full strength,
everything established is dimmed to context, and the metadata path is ghosted
once the story has moved to the data path (S14 -- density).

  1 -> raw/2026-08-24 12-42-08  tracker gives us the peer list
  2 -> raw/2026-08-24 12-43-16  torrent parser + tracker client
  3 -> raw/2026-08-24 12-43-47  peer explorer dedups the tracker's repeats
  4 -> raw/2026-08-24 12-45-53  peer manager spins up peer connections
  5 -> raw/2026-08-24 12-47-48  piece manager
  6 -> raw/2026-08-24 12-49-17  disk writer
"""

import numpy as np

from manim import *
from catppuccin import (LATTE, LatteScene, Region, audit_layout, component,
                        connect, dim, edge_label, endpoints, place_label_clear, row,
                        CONTENT_REGION, GAP_LG, GAP_SM, GAP_XL)

# Component definitions -- no positions. Widths are content-driven, and the
# label auto-fit in component() means a long name shrinks rather than overflows.
SPEC = {
    "torrent":  dict(name=".torrent", sub="metadata", accent="peach", w=2.00),
    "parser":   dict(name="torrent parser", sub="bencode", accent="blue", w=2.70),
    "tclient":  dict(name="tracker client", accent="blue", w=2.60),
    "tracker":  dict(name="tracker", sub="external", accent="teal", w=1.90),
    "explorer": dict(name="peer explorer", sub="dedup", accent="mauve", w=2.60),
    "pmgr":     dict(name="peer manager", accent="mauve", w=2.50),
    "pconn":    dict(name="peer conn x50", accent="sapphire", w=2.60),
    "reqmgr":   dict(name="request manager", sub="per peer", accent="sapphire", w=2.90),
    "peers":    dict(name="peers", sub="external", accent="teal", w=1.60),
    "piecemgr": dict(name="piece manager", accent="mauve", w=2.60),
    "disk":     dict(name="piece writer", sub="disk", accent="green", w=2.40),
}

METADATA_PATH = ("torrent", "parser", "tclient", "tracker")

# (from, to, accent, label, dashed, both)
EDGES = {
    ("torrent", "tracker"):   ("peach", "info hash", False, False),
    ("tracker", "peers"):     ("teal", "peer list", True, False),
    ("torrent", "parser"):    ("peach", "bytes", False, False),
    ("parser", "tclient"):    ("blue", "info hash", False, False),
    ("tclient", "tracker"):   ("blue", "announce", False, True),
    ("tclient", "explorer"):  ("mauve", "raw peers", False, False),
    ("explorer", "pmgr"):     ("mauve", "clean list", False, False),
    ("pmgr", "pconn"):        ("sapphire", "spawn", False, False),
    ("pconn", "peers"):       ("sapphire", "wire", False, True),
    ("pconn", "reqmgr"):      ("sapphire", "framed", False, False),
    ("reqmgr", "piecemgr"):   ("mauve", "blocks", False, True),
    ("piecemgr", "disk"):     ("green", "verified", False, False),
}

STAGES = [
    dict(title="the tracker knows who has the data",
         nodes=["torrent", "tracker", "peers"],
         edges=[("torrent", "tracker"), ("tracker", "peers")],
         new=["torrent", "tracker", "peers"]),
    dict(title="parse the metadata, then announce",
         nodes=["torrent", "parser", "tclient", "tracker", "peers"],
         edges=[("torrent", "parser"), ("parser", "tclient"),
                ("tclient", "tracker"), ("tracker", "peers")],
         new=["parser", "tclient"]),
    dict(title="the tracker repeats itself -- so dedup",
         nodes=["torrent", "parser", "tclient", "tracker", "peers", "explorer"],
         edges=[("torrent", "parser"), ("parser", "tclient"), ("tclient", "tracker"),
                ("tracker", "peers"), ("tclient", "explorer")],
         new=["explorer"], note=("hash set drops the repeats", "explorer")),
    dict(title="one connection per peer, one manager over them",
         nodes=["torrent", "parser", "tclient", "tracker", "peers",
                "explorer", "pmgr", "pconn"],
         edges=[("torrent", "parser"), ("parser", "tclient"), ("tclient", "tracker"),
                ("tracker", "peers"), ("tclient", "explorer"), ("explorer", "pmgr"),
                ("pmgr", "pconn"), ("pconn", "peers")],
         new=["pmgr", "pconn"]),
    dict(title="who keeps track of the pieces?",
         nodes=["torrent", "parser", "tclient", "tracker", "peers", "explorer",
                "pmgr", "pconn", "reqmgr", "piecemgr"],
         edges=[("torrent", "parser"), ("parser", "tclient"), ("tclient", "tracker"),
                ("tracker", "peers"), ("tclient", "explorer"), ("explorer", "pmgr"),
                ("pmgr", "pconn"), ("pconn", "peers"), ("pconn", "reqmgr"),
                ("reqmgr", "piecemgr")],
         new=["reqmgr", "piecemgr"], ghost=METADATA_PATH),
    dict(title="verified pieces hit the disk",
         nodes=list(SPEC),
         edges=[("torrent", "parser"), ("parser", "tclient"), ("tclient", "tracker"),
                ("tracker", "peers"), ("tclient", "explorer"), ("explorer", "pmgr"),
                ("pmgr", "pconn"), ("pconn", "peers"), ("pconn", "reqmgr"),
                ("reqmgr", "piecemgr"), ("piecemgr", "disk")],
         new=["disk"], ghost=METADATA_PATH),
]


def build_graph():
    """Arrange every component relationally. Returns {key: mobject}.

    Called identically by all six stages, so a component lands in the same place
    no matter which stage is being rendered (S7/S19).
    """
    boxes = {
        key: component(spec["name"], LATTE[spec["accent"]], sub=spec.get("sub"),
                       width=spec["w"], height=0.95, font_size=22)
        for key, spec in SPEC.items()
    }

    metadata_row = row(boxes["torrent"], boxes["parser"], boxes["tclient"],
                       boxes["tracker"], gap=GAP_LG)
    peer_row = row(boxes["explorer"], boxes["pmgr"], boxes["pconn"],
                   boxes["peers"], gap=GAP_LG)
    storage_row = row(boxes["reqmgr"], boxes["piecemgr"], boxes["disk"], gap=GAP_LG)

    # Two full-width rows stack; storage hangs off the peer connection it serves.
    VGroup(metadata_row, peer_row).arrange(DOWN, buff=GAP_XL)
    storage_row.next_to(boxes["pconn"], DOWN, buff=GAP_XL)

    graph = VGroup(metadata_row, peer_row, storage_row)
    CONTENT_REGION.fit(graph)
    return boxes, graph


class _Architecture(LatteScene):
    STAGE = 1

    def construct(self):
        boxes, _ = build_graph()
        stage = STAGES[self.STAGE - 1]
        prev = STAGES[self.STAGE - 2] if self.STAGE > 1 else dict(nodes=[], edges=[])

        title = self.title(stage["title"], size=30)
        self.add(title)

        arrows, labels = self._wire(boxes, stage, set(stage["nodes"]))
        prev_arrows, prev_labels = self._wire(boxes, prev, set(prev["nodes"]))

        self._show_established(boxes, stage, prev, prev_arrows, prev_labels)
        self._reveal_new(boxes, stage, prev, arrows, labels, prev_arrows)
        self._annotate(boxes, stage)
        self._verify(boxes, stage, title, arrows, labels)
        self.wait(1.6)

    # --- one narrative beat per method (S25) -----------------------------------

    def _wire(self, boxes, stage, visible):
        """Arrows first, then labels solved against every box, label and line.

        Two passes: a label cannot be placed clear of the arrows until all the
        arrows for the stage exist.
        """
        arrows = {}
        for pair in stage.get("edges", []):
            accent, _text, dashed, both = EDGES[pair]
            a, b = pair
            arrows[pair] = connect(boxes[a], boxes[b], LATTE[accent],
                                   both=both, dashed=dashed)

        segments = [endpoints(arrow) for arrow in arrows.values()]
        obstacles = [boxes[k] for k in visible]
        labels = {}
        for pair in stage.get("edges", []):
            accent, text, _dashed, _both = EDGES[pair]
            lbl = edge_label(text, arrows[pair], color=LATTE[accent])
            place_label_clear(lbl, arrows[pair],
                              obstacles=obstacles + list(labels.values()),
                              segments=segments)
            labels[pair] = lbl
        return arrows, labels

    def _show_established(self, boxes, stage, prev, prev_arrows, prev_labels):
        """Everything already introduced is on screen from frame one, dimmed (S16)."""
        ghosted = set(stage.get("ghost", ()))
        carried = [k for k in prev["nodes"] if k in stage["nodes"]]
        for key in carried:
            if key not in stage["new"]:
                dim(boxes[key], "ghost" if key in ghosted else "context")
                self.add(boxes[key])
        for pair, arrow in prev_arrows.items():
            if pair in stage.get("edges", []):
                tier = "ghost" if set(pair) & ghosted else "context"
                self.add(dim(arrow, tier), dim(prev_labels[pair], tier))

    def _reveal_new(self, boxes, stage, prev, arrows, labels, prev_arrows):
        """Fade out what this beat replaces, then introduce only the new (S20)."""
        dropped = [p for p in prev_arrows if p not in stage.get("edges", [])]
        if dropped:
            self.play(*[FadeOut(prev_arrows[p]) for p in dropped], run_time=0.5)

        fresh_nodes = [k for k in stage["new"] if k in stage["nodes"]]
        if fresh_nodes:
            self.play(*[FadeIn(boxes[k], scale=0.85) for k in fresh_nodes], run_time=0.8)

        fresh_edges = [p for p in stage.get("edges", []) if p not in prev.get("edges", [])]
        if fresh_edges:
            self.play(*[FadeIn(VGroup(arrows[p], labels[p])) for p in fresh_edges],
                      run_time=0.7)

    def _annotate(self, boxes, stage):
        if "note" not in stage:
            return
        txt, anchor = stage["note"]
        note = self.caption(txt, size=19)
        note.next_to(boxes[anchor], DOWN, buff=GAP_SM)
        self.play(FadeIn(note, shift=UP * 0.1), run_time=0.5)
        self.play(Indicate(boxes[anchor], color=LATTE["mauve"], scale_factor=1.06),
                  run_time=0.8)

    def _verify(self, boxes, stage, title, arrows, labels):
        """S22 validation pass -- geometry, text, connections, composition."""
        checked = {"title": title}
        checked.update({k: boxes[k] for k in stage["nodes"]})
        checked.update({f"label[{a}->{b}]": labels[(a, b)] for (a, b) in labels})
        conns = [(f"arrow[{a}->{b}]", arrows[(a, b)], (a, b)) for (a, b) in arrows]
        audit_layout(checked, connections=conns)


class Arch1(_Architecture):
    STAGE = 1


class Arch2(_Architecture):
    STAGE = 2


class Arch3(_Architecture):
    STAGE = 3


class Arch4(_Architecture):
    STAGE = 4


class Arch5(_Architecture):
    STAGE = 5


class Arch6(_Architecture):
    STAGE = 6
