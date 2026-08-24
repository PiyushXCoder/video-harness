"""Code clips lifted from the real implementation at ~/Projects/dhaar-torrent.

Every snippet is real source, trimmed for screen. Elisions are marked `// ...`
so nothing on screen is invented -- pasted source reads as authority, whereas
plausible-looking made-up code undermines the whole video.

  PeerCap       -> raw/2026-08-24 12-45-53  "you need to organize those connections"
  SplitAndSpawn -> raw/2026-08-24 12-50-23  "split the stream into two"
  SelectLoop    -> raw/2026-08-24 12-50-23  "that third guy does an event loop"
  VerifyPiece   -> raw/2026-08-24 12-47-08  "you can verify those pieces"

Sources:
  src/peer_manager/mod.rs              (MAX_PEERS cap, guarded select! arm)
  src/peer_connection/mod.rs           (framed.split(), the two wire tasks)
  src/peer_connection/request_manager.rs (the select! event loop)
  src/piece_manager/mod.rs             (verify_piece)
"""

from manim import *
from catppuccin import (LATTE, LatteScene, audit_layout, code_block,
                        CONTENT_REGION, GAP_SM)

SPLIT_AND_SPAWN = """
let (incoming_sender, incoming_receiver) = channels::new_incoming_channel();
let (outgoing_sender, mut outgoing_receiver) = channels::new_outgoing_channel();

let (mut sink, mut stream) = framed.split();
let mut joinset: JoinSet<()> = JoinSet::new();

joinset.spawn(async move {                       // writes the wire
    while let Some(item) = outgoing_receiver.recv().await {
        if let Err(e) = sink.send(item).await {
            warn!("wire write failed: {e}");
            break;
        }
    }
});

joinset.spawn(async move {                       // reads the wire
    loop {
        match stream.next().await {
            Some(Ok(item)) => {
                if incoming_sender.send(item).await.is_err() { break; }
            }
            _ => break,
        }
    }
});
"""

SELECT_LOOP = """
loop {
    select! {
        _ = time::sleep_until(idle_deadline) => {
            return Err(PeerConnectionError::PeerDisconnected);
        },
        // Armed only while we are actually waiting on blocks.
        _ = async {
            match request_deadline {
                Some(deadline) => time::sleep_until(deadline).await,
                None => std::future::pending().await,
            }
        } => {
            self.unlock_active_blocks().await;
            request_deadline = None;
        },
        _ = availability_tick.tick() => {
            self.availability_tick().await?;
        },
        item = self.incoming_channel_receiver.recv() => {
            let Some(item) = item else {
                return Err(PeerConnectionError::PeerDisconnected);
            };
            self.handle_incoming_message(item).await?;   // ...
            idle_deadline = time::Instant::now() + IDLE_TIMEOUT;
        },
    }
}
"""

PEER_CAP = """
const MAX_PEERS: usize = 50;

loop {
    tokio::select! {
        msg = peer_manager_channel_receiver.recv() => {
            match msg {
                Some(PeerManagerChannelMessage::Closing(peer)) => {
                    self.active -= 1;
                    self.peer_slection_strategy.push(peer, true);
                }
                None => break,
            }
        }
        Some(msg) = peer_explorer_channel_receiver.recv() => {
            /* PeerFound -> push onto the selection strategy */
        }
        // This arm is only eligible while we are under the cap.
        Some(attempt) = self.peer_slection_strategy.pop(),
            if self.active < MAX_PEERS && self.peer_slection_strategy.peek().is_some() =>
        {
            self.active += 1;
            tokio::spawn(async move { /* PeerConnection::connect ... */ });
        }
    }
}
"""

VERIFY_PIECE = """
async fn verify_piece(&self, piece_index: u32) -> bool {
    let Some(piece) = self.pieces.get(piece_index as usize) else {
        return false;
    };
    let Ok(data) = self.piece_writer.read(/* ... */).await else {
        return false;
    };
    let digest: [u8; 20] = sha1::Sha1::digest(&data).into();
    digest == piece.hash
}
"""


class _CodeClip(LatteScene):
    TITLE = ""
    SOURCE = ""
    CAPTION = ""
    ORIGIN = ""

    def construct(self):
        title = self.title(self.TITLE, size=28)
        self.add(title)

        block = code_block(self.SOURCE, width=CONTENT_REGION.width - 1.2)
        origin = self.caption(self.ORIGIN, size=16)
        caption = self.label(self.CAPTION, size=21, color=LATTE["subtext1"])

        body = VGroup(block, origin).arrange(DOWN, buff=GAP_SM)
        stack = VGroup(body, caption).arrange(DOWN, buff=GAP_SM * 2)
        CONTENT_REGION.fit(stack)

        self.play(FadeIn(block, shift=UP * 0.15), run_time=0.8)
        self.play(FadeIn(origin), run_time=0.3)
        self.play(FadeIn(caption, shift=UP * 0.1), run_time=0.5)

        audit_layout({"title": title, "code": block, "origin": origin,
                      "caption": caption}, max_ink=0.80)

        # Hold proportional to how much there is to read. 27 lines of Rust in
        # 1.8s is not a code clip, it is a flash frame.
        lines = len(self.SOURCE.strip().splitlines())
        self.wait(min(2.5 + 0.30 * lines, 12.0))


class SplitAndSpawn(_CodeClip):
    TITLE = "one stream, two tasks, two channels"
    SOURCE = SPLIT_AND_SPAWN
    ORIGIN = "src/peer_connection/mod.rs"
    CAPTION = "the reader and writer never talk to each other -- only through channels"


class SelectLoop(_CodeClip):
    TITLE = "the event loop: four arms, one task"
    SOURCE = SELECT_LOOP
    ORIGIN = "src/peer_connection/request_manager.rs"
    CAPTION = "idle timeout, request timeout, availability tick, incoming message"


class PeerCap(_CodeClip):
    TITLE = "fifty connections, no more"
    SOURCE = PEER_CAP
    ORIGIN = "src/peer_manager/mod.rs"
    CAPTION = "a select! arm can carry a guard -- under the cap, it is eligible; at the cap, it is not"


class VerifyPiece(_CodeClip):
    TITLE = "a piece is only real once the hash matches"
    SOURCE = VERIFY_PIECE
    ORIGIN = "src/piece_manager/mod.rs"
    CAPTION = "SHA-1 over the piece, compared with the hash from the .torrent"
