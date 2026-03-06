const STORAGE_KEYS = {
  participantId: "delib_participant_id_v1",
  voteQueue: "delib_vote_queue_v1",
};

const state = {
  participantId: "",
  inviteToken: "",
  conversationId: "",
  conversation: null,
  comments: [],
  currentComment: null,
  cursor: null,
  hasMore: true,
  loadingDeck: false,
  votedInSession: new Set(),
  queue: [],
  submittingComment: false,
};

const setupPanel = document.getElementById("setup-panel");
const conversationPanel = document.getElementById("conversation-panel");
const deckPanel = document.getElementById("deck-panel");
const commentPanel = document.getElementById("comment-panel");
const networkStatus = document.getElementById("network-status");

const conversationSelect = document.getElementById("conversation-select");
const startButton = document.getElementById("start-button");
const conversationTitle = document.getElementById("conversation-title");
const conversationDescription = document.getElementById("conversation-description");

const deckStatus = document.getElementById("deck-status");
const card = document.getElementById("card");
const cardText = document.getElementById("card-text");
const emptyState = document.getElementById("empty-state");
const badgeLeft = document.getElementById("badge-left");
const badgeRight = document.getElementById("badge-right");

const countAgree = document.getElementById("count-agree");
const countDisagree = document.getElementById("count-disagree");
const countPass = document.getElementById("count-pass");

const disagreeButton = document.getElementById("vote-disagree");
const passButton = document.getElementById("vote-pass");
const agreeButton = document.getElementById("vote-agree");

const commentInput = document.getElementById("comment-input");
const commentSubmit = document.getElementById("comment-submit");

const urlParams = new URLSearchParams(window.location.search);

function getOrCreateParticipantId() {
  const saved = localStorage.getItem(STORAGE_KEYS.participantId);
  if (saved) return saved;
  const generated =
    (window.crypto && window.crypto.randomUUID && window.crypto.randomUUID()) ||
    `p-${Date.now()}-${Math.random()}`;
  localStorage.setItem(STORAGE_KEYS.participantId, generated);
  return generated;
}

function loadQueue() {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEYS.voteQueue) || "[]");
    if (Array.isArray(parsed)) {
      return parsed;
    }
  } catch (_err) {
    // ignore malformed queue and start fresh
  }
  return [];
}

function saveQueue() {
  localStorage.setItem(STORAGE_KEYS.voteQueue, JSON.stringify(state.queue));
}

function authHeaders() {
  const headers = {
    "Content-Type": "application/json",
    "X-Participant-Id": state.participantId,
  };
  if (state.inviteToken) headers["X-Invite-Token"] = state.inviteToken;
  return headers;
}

async function apiFetch(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...authHeaders(),
      ...(options.headers || {}),
    },
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch (_err) {
      // keep default status text
    }
    throw new Error(`${response.status}: ${detail}`);
  }
  if (response.status === 204) return null;
  return response.json();
}

function setNetworkStatus() {
  networkStatus.textContent = navigator.onLine
    ? `Online${state.queue.length ? ` • queued votes: ${state.queue.length}` : ""}`
    : `Offline • queued votes: ${state.queue.length}`;
}

function showPanelsForDeck() {
  setupPanel.classList.add("hidden");
  conversationPanel.classList.remove("hidden");
  deckPanel.classList.remove("hidden");
}

function updateDeckStatus() {
  const queued = state.queue.length;
  deckStatus.textContent = queued
    ? `Votes queued: ${queued}. They sync automatically when online.`
    : "Swipe cards or use buttons to vote.";
  setNetworkStatus();
}

function renderCurrentCard() {
  state.currentComment = state.comments.shift() || null;
  if (!state.currentComment) {
    card.classList.add("hidden");
    emptyState.classList.remove("hidden");
    if (state.hasMore) {
      fetchDeckIfNeeded();
    } else {
      maybeShowCommentPanel();
    }
    return;
  }
  emptyState.classList.add("hidden");
  card.classList.remove("hidden");
  cardText.textContent = state.currentComment.text;
  countAgree.textContent = `👍 ${state.currentComment.agree_count || 0}`;
  countDisagree.textContent = `👎 ${state.currentComment.disagree_count || 0}`;
  countPass.textContent = `➖ ${state.currentComment.pass_count || 0}`;
  card.style.transform = "";
  card.style.opacity = "";
  badgeLeft.style.opacity = "0";
  badgeRight.style.opacity = "0";
}

function maybeShowCommentPanel() {
  if (state.conversation && state.conversation.allow_comment_submission) {
    commentPanel.classList.remove("hidden");
  } else {
    commentPanel.classList.add("hidden");
  }
}

function enqueueVote(vote) {
  const key = `${vote.conversation_id}:${vote.comment_id}`;
  const next = {
    ...vote,
    key,
    queued_at: new Date().toISOString(),
  };
  const existingIndex = state.queue.findIndex((item) => item.key === key);
  if (existingIndex >= 0) {
    state.queue[existingIndex] = next;
  } else {
    state.queue.push(next);
  }
  saveQueue();
  updateDeckStatus();
}

async function flushQueue() {
  if (!navigator.onLine || !state.queue.length) {
    setNetworkStatus();
    return;
  }
  const pending = [...state.queue];
  const remaining = [];
  for (let i = 0; i < pending.length; i += 1) {
    const item = pending[i];
    try {
      await apiFetch("/vote", {
        method: "POST",
        body: JSON.stringify({
          conversation_id: item.conversation_id,
          comment_id: item.comment_id,
          choice: item.choice,
        }),
      });
    } catch (_err) {
      remaining.push(item);
      remaining.push(...pending.slice(i + 1));
      break;
    }
  }
  state.queue = remaining;
  saveQueue();
  updateDeckStatus();
}

async function fetchConversations() {
  const conversations = await apiFetch("/participation/conversations");
  conversationSelect.innerHTML = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Select a conversation";
  conversationSelect.appendChild(placeholder);

  conversations.forEach((conversation) => {
    const opt = document.createElement("option");
    opt.value = conversation.id;
    opt.textContent = conversation.topic;
    conversationSelect.appendChild(opt);
  });

  const presetConversationId = urlParams.get("conversation_id") || urlParams.get("cid");
  if (presetConversationId && conversations.some((c) => c.id === presetConversationId)) {
    conversationSelect.value = presetConversationId;
    startButton.disabled = false;
  }
}

async function fetchDeckIfNeeded() {
  if (state.loadingDeck || !state.conversationId || !state.hasMore || state.comments.length > 6) return;
  state.loadingDeck = true;
  try {
    const cursorParam = state.cursor ? `&cursor=${encodeURIComponent(state.cursor)}` : "";
    const payload = await apiFetch(
      `/participation/conversations/${encodeURIComponent(state.conversationId)}/deck?limit=20${cursorParam}`
    );
    state.hasMore = payload.has_more;
    state.cursor = payload.next_cursor || null;
    const fresh = payload.comments.filter((comment) => !state.votedInSession.has(comment.id));
    state.comments.push(...fresh);
    if (!state.currentComment) {
      renderCurrentCard();
    }
  } catch (err) {
    deckStatus.textContent = `Could not load deck: ${err.message}`;
  } finally {
    state.loadingDeck = false;
  }
}

function animateVote(direction, onDone) {
  const x = direction === "right" ? 320 : direction === "left" ? -320 : 0;
  const y = direction === "up" ? -360 : 0;
  card.style.transition = "transform 180ms ease, opacity 180ms ease";
  card.style.transform = `translate(${x}px, ${y}px) rotate(${x / 40}deg)`;
  card.style.opacity = "0";
  window.setTimeout(() => {
    card.style.transition = "";
    onDone();
  }, 190);
}

function handleVote(choice, direction) {
  if (!state.currentComment) return;
  const votePayload = {
    conversation_id: state.conversationId,
    comment_id: state.currentComment.id,
    choice,
  };
  enqueueVote(votePayload);
  state.votedInSession.add(state.currentComment.id);
  animateVote(direction, () => {
    state.currentComment = null;
    renderCurrentCard();
    fetchDeckIfNeeded();
    flushQueue();
  });
}

function attachCardGestures() {
  let startX = 0;
  let startY = 0;
  let dragging = false;

  card.addEventListener("pointerdown", (event) => {
    if (!state.currentComment) return;
    dragging = true;
    startX = event.clientX;
    startY = event.clientY;
    card.setPointerCapture(event.pointerId);
    card.style.transition = "none";
  });

  card.addEventListener("pointermove", (event) => {
    if (!dragging) return;
    const dx = event.clientX - startX;
    const dy = event.clientY - startY;
    card.style.transform = `translate(${dx}px, ${dy}px) rotate(${dx / 20}deg)`;
    badgeRight.style.opacity = `${Math.max(0, Math.min(1, dx / 120))}`;
    badgeLeft.style.opacity = `${Math.max(0, Math.min(1, -dx / 120))}`;
  });

  card.addEventListener("pointerup", (event) => {
    if (!dragging) return;
    dragging = false;
    const dx = event.clientX - startX;
    const dy = event.clientY - startY;

    if (dx > 90) {
      handleVote(1, "right");
      return;
    }
    if (dx < -90) {
      handleVote(-1, "left");
      return;
    }
    if (dy < -90) {
      handleVote(0, "up");
      return;
    }
    if (Math.abs(dx) < 8 && Math.abs(dy) < 8) {
      handleVote(0, "up");
      return;
    }

    card.style.transition = "transform 120ms ease";
    card.style.transform = "";
    badgeLeft.style.opacity = "0";
    badgeRight.style.opacity = "0";
  });
}

async function startConversation() {
  const selectedId = conversationSelect.value;
  if (!selectedId) return;
  state.conversationId = selectedId;
  state.conversation = null;
  state.comments = [];
  state.currentComment = null;
  state.cursor = null;
  state.hasMore = true;
  state.votedInSession = new Set();
  commentPanel.classList.add("hidden");

  try {
    const details = await apiFetch(`/conversations/${encodeURIComponent(selectedId)}`);
    state.conversation = details;
    conversationTitle.textContent = details.topic;
    conversationDescription.textContent = details.description || "";
    showPanelsForDeck();
    updateDeckStatus();
    await fetchDeckIfNeeded();
  } catch (err) {
    deckStatus.textContent = `Could not start: ${err.message}`;
  }
}

async function submitComment() {
  if (state.submittingComment || !state.conversationId) return;
  const text = (commentInput.value || "").trim();
  if (text.length < 3) {
    alert("Comment should be at least 3 characters.");
    return;
  }
  state.submittingComment = true;
  commentSubmit.disabled = true;
  try {
    await apiFetch(`/conversations/${encodeURIComponent(state.conversationId)}/comments`, {
      method: "POST",
      body: JSON.stringify({ text }),
    });
    commentInput.value = "";
    alert("Comment submitted.");
  } catch (err) {
    alert(`Comment failed: ${err.message}`);
  } finally {
    state.submittingComment = false;
    commentSubmit.disabled = false;
  }
}

function registerServiceWorker() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/participate/sw.js", { scope: "/participate/" }).catch(() => {
      // ignore failures; app still works without worker
    });
  }
}

async function init() {
  state.participantId = getOrCreateParticipantId();
  state.inviteToken = urlParams.get("invite") || "";
  state.queue = loadQueue();
  setNetworkStatus();

  startButton.addEventListener("click", startConversation);
  conversationSelect.addEventListener("change", () => {
    startButton.disabled = !conversationSelect.value;
  });

  agreeButton.addEventListener("click", () => handleVote(1, "right"));
  disagreeButton.addEventListener("click", () => handleVote(-1, "left"));
  passButton.addEventListener("click", () => handleVote(0, "up"));
  commentSubmit.addEventListener("click", submitComment);

  attachCardGestures();

  window.addEventListener("online", () => {
    setNetworkStatus();
    flushQueue();
  });
  window.addEventListener("offline", setNetworkStatus);
  window.setInterval(flushQueue, 10000);

  try {
    await fetchConversations();
    flushQueue();
  } catch (err) {
    conversationSelect.innerHTML = '<option value="">Conversations unavailable</option>';
    deckStatus.textContent = `Error: ${err.message}`;
  }
  registerServiceWorker();
}

init();
