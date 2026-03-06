import altair as alt
import html
import pandas as pd
import streamlit as st
import textwrap
from uuid import uuid4
from urllib.parse import quote

try:
    import matplotlib.pyplot as plt
    from matplotlib_venn import venn2, venn3
except Exception:
    plt = None
    venn2 = None
    venn3 = None

try:
    from crm.ui.components.swipecards_loader import load_streamlit_swipecards
    streamlit_swipecards = load_streamlit_swipecards()
except Exception:
    streamlit_swipecards = None

from crm.clients.deliberation import (
    delib_api_get,
    delib_api_patch,
    delib_api_post,
    render_delib_api_unavailable,
)
from crm.ui.components.questionnaire import render_questionnaire_block

def _safe_int(value):
    try:
        return int(value)
    except Exception:
        return 0


def _guess_column(columns, candidates):
    normalized_candidates = {str(c).strip().lower() for c in candidates}
    for col in columns:
        col_name = str(col).strip().lower()
        if col_name in normalized_candidates:
            return col
    for col in columns:
        col_name = str(col).strip().lower().replace(" ", "_")
        if col_name in normalized_candidates:
            return col
    return ""


def _clean_vote_csv_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        as_int = int(value)
        if float(value) == float(as_int):
            return as_int
    cleaned = str(value).strip()
    return cleaned or None


def _clean_optional_text_csv_value(value):
    if pd.isna(value):
        return None
    cleaned = str(value).strip()
    if not cleaned or cleaned.lower() in {"nan", "none", "null"}:
        return None
    return cleaned


def _clean_optional_bool_csv_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        as_int = int(value)
        if float(value) == float(as_int):
            if as_int == 1:
                return True
            if as_int == 0:
                return False
        return None
    text = str(value).strip().lower()
    if text in {"true", "t", "yes", "y", "1"}:
        return True
    if text in {"false", "f", "no", "n", "0"}:
        return False
    return None


def _clean_id_csv_value(value):
    if pd.isna(value):
        return ""
    if isinstance(value, bool):
        return ""
    if isinstance(value, (int, float)):
        as_int = int(value)
        if float(value) == float(as_int):
            return str(as_int)
    return str(value).strip()


def _resolve_card_typography(text):
    char_count = len(" ".join(str(text or "").split()))
    if char_count <= 85:
        return {"font_size": 52, "line_height": 62, "max_chars": 24, "max_lines": 6}
    if char_count <= 150:
        return {"font_size": 44, "line_height": 56, "max_chars": 28, "max_lines": 7}
    if char_count <= 230:
        return {"font_size": 38, "line_height": 50, "max_chars": 32, "max_lines": 9}
    return {"font_size": 32, "line_height": 44, "max_chars": 36, "max_lines": 10}


def _wrap_card_text(text, max_chars, max_lines):
    raw = " ".join(str(text or "").split())
    if not raw:
        return ["No statement text provided."]
    lines = textwrap.wrap(raw, width=max_chars, break_long_words=False, break_on_hyphens=False)
    if not lines:
        return ["No statement text provided."]
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        lines[-1] = (last[:-1] + "…") if len(last) > 1 else "…"
    return lines


def _build_swipe_card_image(comment, idx, total, compact=False):
    card_text = comment.get("text", "")
    typography = _resolve_card_typography(card_text)
    question_lines = _wrap_card_text(
        card_text,
        max_chars=typography["max_chars"],
        max_lines=typography["max_lines"],
    )
    font_size = typography["font_size"]
    line_height = typography["line_height"]

    title = html.escape(f"Question {idx + 1} / {total}")
    subtitle = html.escape("Swipe right = agree   •   Swipe left = disagree   •   Swipe down = pass")
    footer = (
        "Reactions: "
        f"👍 {_safe_int(comment.get('agree_count', 0))}   "
        f"👎 {_safe_int(comment.get('disagree_count', 0))}   "
        f"➖ {_safe_int(comment.get('pass_count', 0))}"
    )
    footer_text = html.escape(footer)

    panel_y = 210 if compact else 230
    panel_h = 860 if compact else 680
    text_block_h = ((len(question_lines) - 1) * line_height) + font_size
    start_y = int(panel_y + max(74, (panel_h - text_block_h) / 2) + (font_size * 0.82))
    line_elements = []
    for i, line in enumerate(question_lines):
        y = start_y + (i * line_height)
        line_elements.append(
            f"<text x='80' y='{y}' font-size='{font_size}' font-weight='700' "
            f"fill='#0B3A52'>{html.escape(line)}</text>"
        )
    lines_svg = "".join(line_elements)
    subtitle_svg = (
        f"<text x='64' y='152' font-size='24' fill='#D8ECF7'>{subtitle}</text>"
        if not compact
        else ""
    )
    footer_svg = (
        "<rect x='32' y='944' width='656' height='144' rx='26' fill='url(#footerGrad)'/>"
        "<line x1='360' y1='968' x2='360' y2='1062' stroke='#4F8DA8' stroke-width='2'/>"
        "<text x='64' y='1000' font-size='30' font-weight='700' fill='#FFFFFF'>⬅ Disagree</text>"
        "<text x='478' y='1000' font-size='30' font-weight='700' fill='#FFFFFF'>Agree ➡</text>"
        f"<text x='64' y='1048' font-size='22' fill='#D8ECF7'>{footer_text}</text>"
        if not compact
        else ""
    )

    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 720 1120'>"
        "<defs>"
        "<linearGradient id='bgGrad' x1='0%' y1='0%' x2='100%' y2='100%'>"
        "<stop offset='0%' stop-color='#0B3A52'/>"
        "<stop offset='55%' stop-color='#167CA7'/>"
        "<stop offset='100%' stop-color='#42B5D9'/>"
        "</linearGradient>"
        "<linearGradient id='headerGrad' x1='0%' y1='0%' x2='100%' y2='0%'>"
        "<stop offset='0%' stop-color='#0A3146'/>"
        "<stop offset='100%' stop-color='#12769F'/>"
        "</linearGradient>"
        "<linearGradient id='questionGrad' x1='0%' y1='0%' x2='0%' y2='100%'>"
        "<stop offset='0%' stop-color='#FFFFFF'/>"
        "<stop offset='100%' stop-color='#F0F9FF'/>"
        "</linearGradient>"
        "<linearGradient id='footerGrad' x1='0%' y1='0%' x2='100%' y2='100%'>"
        "<stop offset='0%' stop-color='#0D435C'/>"
        "<stop offset='100%' stop-color='#0A2D3D'/>"
        "</linearGradient>"
        "</defs>"
        "<rect width='720' height='1120' rx='40' fill='url(#bgGrad)'/>"
        "<circle cx='640' cy='110' r='120' fill='#FFFFFF' opacity='0.10'/>"
        "<circle cx='90' cy='1060' r='170' fill='#FFFFFF' opacity='0.08'/>"
        "<rect x='20' y='20' width='680' height='1080' rx='36' fill='#FFFFFF' opacity='0.16'/>"
        "<rect x='32' y='32' width='656' height='170' rx='26' fill='url(#headerGrad)'/>"
        f"<text x='64' y='102' font-size='36' font-weight='700' fill='#FFFFFF'>{title}</text>"
        f"{subtitle_svg}"
        f"<rect x='32' y='{panel_y}' width='656' height='{panel_h}' rx='34' fill='url(#questionGrad)' stroke='#A9D2E6' stroke-width='3'/>"
        f"{lines_svg}"
        f"{footer_svg}"
        "</svg>"
    )
    return "data:image/svg+xml;utf8," + quote(svg)


def _apply_questionnaire_card_only_layout():
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] {
          background: linear-gradient(145deg, #0B3A52 0%, #167CA7 52%, #44BEE0 100%) !important;
        }
        header[data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        #MainMenu,
        footer {
          display: none !important;
        }
        .block-container {
          padding-top: 0.4rem !important;
          padding-bottom: 0.4rem !important;
          padding-left: 0.3rem !important;
          padding-right: 0.3rem !important;
          max-width: 100% !important;
        }
        [data-testid="stVerticalBlock"] > div {
          background: transparent !important;
        }
        [data-testid="stExpander"] details {
          background: #F8FCFF !important;
          border: 1px solid #CFE2EC !important;
          border-radius: 14px !important;
        }
        [data-testid="stExpander"] details > summary {
          background: #FFFFFF !important;
          color: #0B3A52 !important;
          border-radius: 14px !important;
          padding: 0.4rem 0.7rem !important;
        }
        [data-testid="stExpander"] details > div {
          background: #F8FCFF !important;
          border-radius: 0 0 14px 14px !important;
          padding: 0.45rem 0.6rem 0.7rem 0.6rem !important;
        }
        [data-testid="stExpander"] details * {
          color: #0B3A52 !important;
        }
        [data-testid="stForm"] {
          background: #F8FCFF !important;
          border: 1px solid #CFE2EC !important;
          border-radius: 14px !important;
          padding: 0.6rem !important;
        }
        .fs-questionnaire-note {
          background: #F8FCFF;
          border: 1px solid #CFE2EC;
          border-radius: 12px;
          padding: 0.5rem 0.7rem;
          margin: 0.35rem 0 0.55rem 0;
          color: #0B3A52;
        }
        .fs-questionnaire-note h4 {
          margin: 0;
          font-size: 1.02rem;
          color: #0B3A52;
        }
        .fs-questionnaire-note p {
          margin: 0.2rem 0 0 0;
          color: #365D72;
          font-size: 0.9rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _is_questionnaire_participation_mode():
    try:
        value = st.query_params.get("questionnaire")
    except Exception:
        params = st.experimental_get_query_params()
        value = params.get("questionnaire")
    if isinstance(value, list):
        value = value[0] if value else ""
    return str(value or "").strip().lower() == "deliberation"


def _get_query_param(name):
    try:
        value = st.query_params.get(name)
    except Exception:
        params = st.experimental_get_query_params()
        value = params.get(name)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _cast_swipe_vote(convo_id, comment_id, choice, headers):
    result = delib_api_post(
        "/vote",
        {
            "conversation_id": convo_id,
            "comment_id": comment_id,
            "choice": choice,
        },
        headers=headers,
    )
    return result is not None


def _render_swipe_component(comments, convo_id, headers, compact=False):
    if streamlit_swipecards is None:
        st.warning(
            "Swipe component is unavailable in this environment. "
            "Use classic mode below."
        )
        _render_classic_vote_list(comments, convo_id, headers)
        return {"current_comment_id": None, "total_swiped": 0}

    cards = []
    for idx, comment in enumerate(comments):
        cards.append(
            {
                "name": " " if compact else f"Question {idx + 1}/{len(comments)}",
                "description": " ",
                "image": _build_swipe_card_image(comment, idx, len(comments), compact=compact),
            }
        )

    mode_suffix = "compact" if compact else "full"
    result = streamlit_swipecards(
        cards=cards,
        display_mode="cards",
        view="mobile",
        show_border=False,
        last_card_message="You have reviewed all statements.",
        colors={
            "like_bg": "#167CA7",
            "like_fg": "#FFFFFF",
            "pass_bg": "#0D435C",
            "pass_fg": "#FFFFFF",
            "back_bg": "#4D6B7A",
            "back_fg": "#FFFFFF",
            "btn_border": "#CFE2EC",
            "card_bg": "#FFFFFF",
            "background_color": "#F8FCFF",
            "text_color": "#0B3A52",
        },
        key=f"delib_swipe_component_{convo_id}_{mode_suffix}",
    )

    processed_key = f"delib_swipe_processed_{convo_id}_{mode_suffix}"
    processed_count = int(st.session_state.get(processed_key, 0))
    swiped_cards = (
        result.get("swipedCards", [])
        if isinstance(result, dict)
        else []
    )
    total_swiped = len(swiped_cards)
    current_comment_id = None
    if comments and total_swiped < len(comments):
        active_comment = comments[total_swiped]
        if isinstance(active_comment, dict):
            current_comment_id = active_comment.get("id")

    if not compact:
        st.progress((total_swiped / len(comments)) if comments else 0.0)
        st.caption("Swipe right = Agree, swipe left = Disagree, swipe down = Pass.")
        st.caption("Each card shows one question/comment only.")
        st.caption(f"{total_swiped}/{len(comments)} reactions recorded")

    if total_swiped > processed_count:
        new_actions = swiped_cards[processed_count:]
        for action_item in new_actions:
            idx = action_item.get("index")
            action = action_item.get("action")
            if not isinstance(idx, int) or idx < 0 or idx >= len(comments):
                continue
            if action == "right":
                choice = 1
            elif action == "left":
                choice = -1
            elif action == "down":
                choice = 0
            else:
                continue
            comment_id = comments[idx].get("id")
            if comment_id:
                _cast_swipe_vote(convo_id, comment_id, choice, headers)
        st.session_state[processed_key] = total_swiped
        st.rerun()

    if not compact and st.button(
        "Reset swipe progress",
        key=f"delib_swipe_reset_{convo_id}",
        help="Reset local swipe progress for this conversation.",
    ):
        st.session_state[processed_key] = 0
        st.rerun()

    return {"current_comment_id": current_comment_id, "total_swiped": total_swiped}


def _render_classic_vote_list(comments, convo_id, headers):
    for comment in comments:
        st.markdown(f"**{comment['text']}**")
        counts = (
            f"👍 {comment['agree_count']}  "
            f"👎 {comment['disagree_count']}  "
            f"➖ {comment['pass_count']}"
        )
        st.caption(counts)
        cols = st.columns(3)
        if cols[0].button(
            "Agree",
            key=f"delib-{comment['id']}-agree",
            help="Vote Agree on this comment.",
        ):
            delib_api_post(
                "/vote",
                {
                    "conversation_id": convo_id,
                    "comment_id": comment["id"],
                    "choice": 1,
                },
                headers=headers,
            )
        if cols[1].button(
            "Disagree",
            key=f"delib-{comment['id']}-disagree",
            help="Vote Disagree on this comment.",
        ):
            delib_api_post(
                "/vote",
                {
                    "conversation_id": convo_id,
                    "comment_id": comment["id"],
                    "choice": -1,
                },
                headers=headers,
            )
        if cols[2].button(
            "Pass",
            key=f"delib-{comment['id']}-pass",
            help="Skip/Pass on this comment (neutral / no vote).",
        ):
            delib_api_post(
                "/vote",
                {
                    "conversation_id": convo_id,
                    "comment_id": comment["id"],
                    "choice": 0,
                },
                headers=headers,
            )
        st.divider()


def _render_questionnaire_comment_form(convo_id, headers):
    st.markdown(
        """
        <div class="fs-questionnaire-note">
          <h4>Add anonymous comment</h4>
          <p>Optional. No registration required.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.form(f"delib_questionnaire_comment_form_{convo_id}", clear_on_submit=True):
        new_comment = st.text_area(
            "Your comment",
            key=f"delib_questionnaire_comment_text_{convo_id}",
            height=90,
            placeholder="Share your view...",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("Submit anonymous comment")
    if submitted:
        text = (new_comment or "").strip()
        if not text:
            st.warning("Comment cannot be empty.")
        elif len(text) < 2:
            st.warning("Comment should be at least 2 characters.")
        else:
            result = delib_api_post(
                f"/conversations/{convo_id}/comments",
                {"text": text},
                headers=headers,
            )
            if result:
                status = str(result.get("status", "")).lower()
                notice_key = f"delib_questionnaire_comment_notice_{convo_id}"
                if status == "pending":
                    st.session_state[notice_key] = "pending"
                else:
                    st.session_state[notice_key] = "approved"
                st.rerun()


def _render_questionnaire_like_dislike_buttons(comments, convo_id, headers, focus_comment_id=None):
    anon_comments = [c for c in comments if not bool(c.get("is_seed", False))]
    if not anon_comments:
        st.info("No anonymous participant comments yet.")
        return

    if focus_comment_id:
        anon_comments = [c for c in anon_comments if c.get("id") == focus_comment_id]
        if not anon_comments:
            st.info("This card has no anonymous comment reactions.")
            return

    max_items = 1 if focus_comment_id else min(len(anon_comments), 20)
    for comment in anon_comments[:max_items]:
        comment_id = comment.get("id")
        text = str(comment.get("text") or "").strip()
        if not comment_id or not text:
            continue
        st.markdown(text)
        st.caption(
            f"👍 {_safe_int(comment.get('agree_count', 0))}   "
            f"👎 {_safe_int(comment.get('disagree_count', 0))}"
        )
        cols = st.columns([1, 1, 4])
        like_clicked = cols[0].button(
            "👍 Like",
            key=f"delib_q_like_{convo_id}_{comment_id}",
        )
        dislike_clicked = cols[1].button(
            "👎 Dislike",
            key=f"delib_q_dislike_{convo_id}_{comment_id}",
        )
        if like_clicked:
            if _cast_swipe_vote(convo_id, comment_id, 1, headers):
                st.rerun()
        if dislike_clicked:
            if _cast_swipe_vote(convo_id, comment_id, -1, headers):
                st.rerun()
        st.divider()


def render_deliberation(public_only: bool):
    if "delib_anon_id" not in st.session_state:
        st.session_state["delib_anon_id"] = str(uuid4())
    headers = {"X-Participant-Id": st.session_state["delib_anon_id"]}

    conversations = delib_api_get("/conversations", show_error=False)
    if conversations is None:
        render_delib_api_unavailable()
        return
    conversations = conversations or []
    questionnaire_mode = public_only and _is_questionnaire_participation_mode()

    if questionnaire_mode:
        _apply_questionnaire_card_only_layout()
        convo_id = st.session_state.get("delib_conversation_id") or _get_query_param(
            "conversation_id"
        ) or _get_query_param("conversation")
        if not convo_id:
            st.error("Missing conversation_id in participant link.")
            return
        convo = delib_api_get(f"/conversations/{convo_id}")
        if not convo:
            st.error("Conversation not found.")
            return
        q_notice_key = f"delib_questionnaire_comment_notice_{convo_id}"
        q_notice = st.session_state.pop(q_notice_key, None)
        if q_notice == "pending":
            st.info("Comment submitted. It is awaiting moderation before it appears in the feed.")
        elif q_notice == "approved":
            st.success("Comment submitted and added to the feed.")
        comments = delib_api_get(f"/conversations/{convo_id}/comments?status=approved") or []
        if not comments:
            st.info("No approved comments yet.")
        else:
            swipe_state = _render_swipe_component(comments, convo_id, headers, compact=True)
            current_comment_id = (
                swipe_state.get("current_comment_id")
                if isinstance(swipe_state, dict)
                else None
            )
            with st.expander("Anonymous participant comments (optional Like / Dislike)", expanded=False):
                _render_questionnaire_like_dislike_buttons(
                    comments,
                    convo_id,
                    headers,
                    focus_comment_id=current_comment_id,
                )
        if convo.get("allow_comment_submission", True):
            _render_questionnaire_comment_form(convo_id, headers)
        return

    st.subheader("Deliberation")
    st.caption("Anonymous comments + votes, consensus analysis, and clustering.")
    st.caption(
        "Deliberation = “What do groups of people think?” (insight/clustering from votes)."
    )
    convo_options = {c["topic"]: c["id"] for c in conversations} if conversations else {}
    selected_title = st.selectbox(
        "Select conversation",
        [""] + list(convo_options.keys()),
        key="delib_conversation_select",
        help="Pick which deliberation conversation you want to participate in / analyze.",
    )
    if selected_title:
        st.session_state["delib_conversation_id"] = convo_options[selected_title]

    if public_only:
        tab_participate, tab_reports = st.tabs(["Participate", "Reports"])
    else:
        tab_config, tab_participate, tab_moderate, tab_reports = st.tabs(
            ["Configure", "Participate", "Moderate", "Monitor / Reports"]
        )

        with tab_config:
            st.markdown("### Questionnaire templates (shareable)")
            q_supporter_tab, q_member_tab = st.tabs(["Supporters", "Members"])
            with q_supporter_tab:
                render_questionnaire_block("supporter", show_expander=False)
            with q_member_tab:
                render_questionnaire_block("member", show_expander=False)

            st.markdown("---")
            st.markdown("### Create conversation")
            topic = st.text_input(
                "Topic",
                key="delib_topic",
                help="Conversation title participants will see.",
            )
            description = st.text_area(
                "Description",
                key="delib_description",
                help="Context shown above the conversation during participation.",
            )
            allow_comment_submission = st.checkbox(
                "Allow participant comments",
                value=True,
                key="delib_allow_comment",
                help="If enabled, participants can submit new comments (may be moderated).",
            )
            allow_viz = st.checkbox(
                "Allow visualization",
                value=True,
                key="delib_allow_viz",
                help="If enabled, show cluster charts/visualizations in reports.",
            )
            moderation_required = st.checkbox(
                "Moderation required",
                value=False,
                key="delib_moderation",
                help="If enabled, submitted comments require approval before becoming voteable.",
            )
            is_open = st.checkbox(
                "Open for participation",
                value=True,
                key="delib_is_open",
                help="If disabled, participation is closed (read-only).",
            )
            if st.button(
                "Create conversation",
                key="delib_create_convo",
                help="Create a new deliberation conversation (topic + settings).",
            ):
                if len(topic.strip()) >= 3:
                    result = delib_api_post(
                        "/conversations",
                        {
                            "topic": topic,
                            "description": description,
                            "allow_comment_submission": allow_comment_submission,
                            "allow_viz": allow_viz,
                            "moderation_required": moderation_required,
                            "is_open": is_open,
                        },
                    )
                    if result:
                        created_convo_id = str(result.get("id") or "").strip()
                        if created_convo_id:
                            st.session_state["delib_conversation_id"] = created_convo_id
                        created_topic = str(result.get("topic") or topic).strip()
                        if created_topic:
                            st.session_state["delib_conversation_select"] = created_topic
                        st.success("Conversation created.")
                        st.rerun()
                else:
                    st.warning("Topic must be at least 3 characters.")

            convo_id = st.session_state.get("delib_conversation_id")
            if convo_id:
                st.markdown("### Update conversation")
                convo = delib_api_get(f"/conversations/{convo_id}")
                if convo:
                    updated_topic = st.text_input(
                        "Topic (edit)", value=convo.get("topic", ""), key="delib_topic_edit"
                    )
                    updated_description = st.text_area(
                        "Description (edit)",
                        value=convo.get("description") or "",
                        key="delib_description_edit",
                    )
                    updated_allow_comment = st.checkbox(
                        "Allow participant comments (edit)",
                        value=convo.get("allow_comment_submission", True),
                        key="delib_allow_comment_edit",
                    )
                    updated_allow_viz = st.checkbox(
                        "Allow visualization (edit)",
                        value=convo.get("allow_viz", True),
                        key="delib_allow_viz_edit",
                    )
                    updated_moderation = st.checkbox(
                        "Moderation required (edit)",
                        value=convo.get("moderation_required", False),
                        key="delib_moderation_edit",
                    )
                    updated_is_open = st.checkbox(
                        "Open for participation (edit)",
                        value=convo.get("is_open", True),
                        key="delib_is_open_edit",
                    )
                    if st.button(
                        "Save settings",
                        key="delib_save_settings",
                        help="Update conversation settings (open/closed, moderation, etc.).",
                    ):
                        result = delib_api_patch(
                            f"/conversations/{convo_id}",
                            {
                                "topic": updated_topic,
                                "description": updated_description,
                                "allow_comment_submission": updated_allow_comment,
                                "allow_viz": updated_allow_viz,
                                "moderation_required": updated_moderation,
                                "is_open": updated_is_open,
                            },
                        )
                        if result:
                            st.success("Conversation updated.")

                    st.markdown("### Generate demo votes")
                    st.caption(
                        "Use this to quickly populate reports/charts for demos when real votes are low."
                    )
                    demo_cols = st.columns(3)
                    with demo_cols[0]:
                        demo_participants = st.number_input(
                            "Participants",
                            min_value=1,
                            max_value=1000,
                            value=120,
                            step=10,
                            key="delib_demo_participants",
                        )
                    with demo_cols[1]:
                        demo_votes_per = st.number_input(
                            "Votes per participant",
                            min_value=1,
                            max_value=200,
                            value=20,
                            step=1,
                            key="delib_demo_votes_per",
                        )
                    with demo_cols[2]:
                        demo_seed = st.number_input(
                            "Seed",
                            min_value=0,
                            max_value=999999,
                            value=42,
                            step=1,
                            key="delib_demo_seed",
                        )
                    if st.button(
                        "Generate demo votes",
                        key="delib_generate_demo_votes",
                        help="Create simulated participants and votes for the selected conversation.",
                    ):
                        result = delib_api_post(
                            f"/conversations/{convo_id}/simulate-votes",
                            {
                                "participants": int(demo_participants),
                                "votes_per_participant": int(demo_votes_per),
                                "seed": int(demo_seed),
                            },
                        )
                        if result:
                            st.success(
                                f"Generated {result.get('generated_votes', 0)} votes "
                                f"across {result.get('participants', 0)} participants."
                            )

                    st.markdown("### Seed comments (bulk)")
                    seed_text = st.text_area(
                        "One comment per line",
                        key="delib_seed_text",
                        help="Seed statements/questions as separate comments so participants can vote on a shared set.",
                    )
                    if st.button(
                        "Add seed comments",
                        key="delib_seed_submit",
                        help="Bulk add seed comments (one per line).",
                    ):
                        lines = [line.strip() for line in seed_text.splitlines() if line.strip()]
                        if lines:
                            result = delib_api_post(
                                f"/conversations/{convo_id}/seed-comments:bulk",
                                {"comments": lines},
                            )
                            if result:
                                st.success(f"Added {result.get('created', 0)} comments.")
                        else:
                            st.warning("Add at least one comment.")

                    st.markdown("### Seed comments from CSV column")
                    st.caption("Upload a CSV and pick a column to turn each row into a comment.")
                    csv_upload = st.file_uploader("CSV", type=["csv"], key="delib_seed_csv_upload")
                    if csv_upload is not None:
                        try:
                            df_seed = pd.read_csv(csv_upload)
                        except Exception as exc:
                            st.error(f"Could not read CSV: {exc}")
                            df_seed = pd.DataFrame()
                        if not df_seed.empty:
                            st.dataframe(df_seed.head(10), use_container_width=True)
                            col = st.selectbox(
                                "Column to use as comment text",
                                options=[""] + df_seed.columns.tolist(),
                                key="delib_seed_csv_col",
                            )
                            max_rows = st.number_input(
                                "Max rows to seed",
                                min_value=1,
                                max_value=5000,
                                value=200,
                                step=50,
                                key="delib_seed_csv_max_rows",
                            )
                            if st.button(
                                "Seed from CSV",
                                key="delib_seed_csv_btn",
                                help="Create seed comments from the selected CSV column.",
                            ):
                                if not col:
                                    st.warning("Select a column.")
                                else:
                                    values = [
                                        str(v).strip()
                                        for v in df_seed[col].head(int(max_rows)).tolist()
                                        if str(v).strip() and str(v).strip().lower() not in {"nan", "none"}
                                    ]
                                    values = list(dict.fromkeys(values))
                                    if not values:
                                        st.warning("No valid values found in that column.")
                                    else:
                                        result = delib_api_post(
                                            f"/conversations/{convo_id}/seed-comments:bulk",
                                            {"comments": values},
                                        )
                                        if result:
                                            st.success(
                                                f"Seeded {result.get('created', 0)} comments from CSV."
                                            )

                    st.markdown("### One-file CSV import (question + comments + reactions)")
                    st.caption(
                        "Upload one CSV containing comment records and vote reactions. "
                        "Useful columns: conversation_id, participant_id, participant_cluster, "
                        "comment_id, comment_text, is_seed, comment_created_at, vote, reaction_created_at."
                    )
                    combined_upload = st.file_uploader(
                        "Combined deliberation CSV",
                        type=["csv"],
                        key="delib_combined_csv_upload",
                    )
                    if combined_upload is not None:
                        try:
                            df_combined = pd.read_csv(combined_upload)
                        except Exception as exc:
                            st.error(f"Could not read combined CSV: {exc}")
                            df_combined = pd.DataFrame()
                        if not df_combined.empty:
                            st.dataframe(df_combined.head(10), use_container_width=True)
                            columns = df_combined.columns.tolist()
                            options = [""] + columns

                            conversation_default = _guess_column(
                                columns,
                                {"conversation_id", "conversation", "conversationid"},
                            )
                            participant_default = _guess_column(
                                columns,
                                {"participant_id", "participant", "voter_id", "user_id"},
                            )
                            participant_cluster_default = _guess_column(
                                columns,
                                {"participant_cluster", "cluster_id", "cluster", "segment"},
                            )
                            comment_id_default = _guess_column(
                                columns,
                                {"comment_id", "statement_id", "seed_id"},
                            )
                            comment_text_default = _guess_column(
                                columns,
                                {"comment_text", "comment", "text", "statement"},
                            )
                            is_seed_default = _guess_column(columns, {"is_seed", "seed"})
                            comment_created_default = _guess_column(
                                columns,
                                {"comment_created_at", "comment_created", "created_at"},
                            )
                            vote_default = _guess_column(
                                columns,
                                {"vote", "choice", "reaction"},
                            )
                            reaction_created_default = _guess_column(
                                columns,
                                {"reaction_created_at", "vote_created_at", "voted_at"},
                            )

                            map_cols = st.columns(4)
                            with map_cols[0]:
                                conversation_col = st.selectbox(
                                    "Conversation ID column (optional)",
                                    options=options,
                                    index=options.index(conversation_default)
                                    if conversation_default in options
                                    else 0,
                                    key="delib_combined_conversation_col",
                                )
                                participant_col = st.selectbox(
                                    "Participant ID column",
                                    options=options,
                                    index=options.index(participant_default)
                                    if participant_default in options
                                    else 0,
                                    key="delib_combined_participant_col",
                                )
                                participant_cluster_col = st.selectbox(
                                    "Participant cluster column (optional)",
                                    options=options,
                                    index=options.index(participant_cluster_default)
                                    if participant_cluster_default in options
                                    else 0,
                                    key="delib_combined_participant_cluster_col",
                                )
                            with map_cols[1]:
                                comment_id_col = st.selectbox(
                                    "Comment ID column *",
                                    options=options,
                                    index=options.index(comment_id_default)
                                    if comment_id_default in options
                                    else 0,
                                    key="delib_combined_comment_id_col",
                                )
                                comment_text_col = st.selectbox(
                                    "Comment text column (optional)",
                                    options=options,
                                    index=options.index(comment_text_default)
                                    if comment_text_default in options
                                    else 0,
                                    key="delib_combined_comment_text_col",
                                )
                            with map_cols[2]:
                                is_seed_col = st.selectbox(
                                    "is_seed column (optional)",
                                    options=options,
                                    index=options.index(is_seed_default)
                                    if is_seed_default in options
                                    else 0,
                                    key="delib_combined_is_seed_col",
                                )
                                comment_created_col = st.selectbox(
                                    "comment_created_at column (optional)",
                                    options=options,
                                    index=options.index(comment_created_default)
                                    if comment_created_default in options
                                    else 0,
                                    key="delib_combined_comment_created_col",
                                )
                            with map_cols[3]:
                                vote_col = st.selectbox(
                                    "Vote column (optional)",
                                    options=options,
                                    index=options.index(vote_default)
                                    if vote_default in options
                                    else 0,
                                    key="delib_combined_vote_col",
                                )
                                reaction_created_col = st.selectbox(
                                    "reaction_created_at column (optional)",
                                    options=options,
                                    index=options.index(reaction_created_default)
                                    if reaction_created_default in options
                                    else 0,
                                    key="delib_combined_reaction_created_col",
                                )

                            controls = st.columns([1, 1])
                            with controls[0]:
                                max_combined_rows = st.number_input(
                                    "Max rows to import",
                                    min_value=1,
                                    max_value=50000,
                                    value=5000,
                                    step=100,
                                    key="delib_combined_max_rows",
                                )
                            with controls[1]:
                                run_analysis_after_combined = st.checkbox(
                                    "Run analysis after one-file import",
                                    value=True,
                                    key="delib_combined_run_analysis",
                                )

                            if st.button(
                                "Import one-file CSV",
                                key="delib_combined_import_btn",
                                help="Import comments + reactions from a single CSV file.",
                            ):
                                if not comment_id_col:
                                    st.warning("Select a Comment ID column.")
                                else:
                                    subset = df_combined.head(int(max_combined_rows))
                                    rows = []
                                    for source in subset.to_dict(orient="records"):
                                        comment_id = _clean_id_csv_value(source.get(comment_id_col))
                                        if not comment_id:
                                            continue
                                        row_payload = {"comment_id": comment_id}
                                        if conversation_col:
                                            conversation_value = _clean_optional_text_csv_value(
                                                source.get(conversation_col)
                                            )
                                            if conversation_value:
                                                row_payload["conversation_id"] = conversation_value
                                        if participant_col:
                                            participant_value = _clean_id_csv_value(
                                                source.get(participant_col)
                                            )
                                            if participant_value:
                                                row_payload["participant_id"] = participant_value
                                        if participant_cluster_col:
                                            participant_cluster_value = _clean_optional_text_csv_value(
                                                source.get(participant_cluster_col)
                                            )
                                            if participant_cluster_value:
                                                row_payload["participant_cluster"] = participant_cluster_value
                                        if comment_text_col:
                                            comment_text_value = _clean_optional_text_csv_value(
                                                source.get(comment_text_col)
                                            )
                                            if comment_text_value:
                                                row_payload["comment_text"] = comment_text_value
                                        if is_seed_col:
                                            is_seed_value = _clean_optional_bool_csv_value(
                                                source.get(is_seed_col)
                                            )
                                            if is_seed_value is not None:
                                                row_payload["is_seed"] = is_seed_value
                                        if comment_created_col:
                                            comment_created_value = _clean_optional_text_csv_value(
                                                source.get(comment_created_col)
                                            )
                                            if comment_created_value:
                                                row_payload["comment_created_at"] = comment_created_value
                                        if vote_col:
                                            vote_value = _clean_vote_csv_value(source.get(vote_col))
                                            if vote_value is not None:
                                                row_payload["vote"] = vote_value
                                        if reaction_created_col:
                                            reaction_created_value = _clean_optional_text_csv_value(
                                                source.get(reaction_created_col)
                                            )
                                            if reaction_created_value:
                                                row_payload["reaction_created_at"] = reaction_created_value
                                        rows.append(row_payload)

                                    if not rows:
                                        st.warning("No valid rows found for import.")
                                    else:
                                        result = delib_api_post(
                                            f"/conversations/{convo_id}/dataset:bulk",
                                            {"rows": rows},
                                        )
                                        if result:
                                            mismatch_rows = int(result.get("conversation_mismatch_rows", 0) or 0)
                                            st.success(
                                                "Imported one-file dataset: "
                                                f"{result.get('comments_created', 0)} comments created, "
                                                f"{result.get('comments_updated', 0)} comments updated, "
                                                f"{result.get('votes_imported', 0)} votes imported, "
                                                f"{result.get('skipped_rows', 0)} rows skipped."
                                            )
                                            if mismatch_rows > 0:
                                                st.caption(
                                                    f"Note: {mismatch_rows} row(s) had a different conversation_id in the file; "
                                                    "they were still imported into the selected conversation."
                                                )
                                            if run_analysis_after_combined:
                                                refreshed = delib_api_post(
                                                    f"/conversations/{convo_id}/analyze",
                                                    {},
                                                )
                                                if refreshed:
                                                    st.success(
                                                        "Monitor / Reports has been refreshed with the imported dataset."
                                                    )

            else:
                st.info("Select a conversation to edit settings or seed comments.")

    with tab_participate:
        convo_id = st.session_state.get("delib_conversation_id")
        if not convo_id:
            st.info("Select a conversation first.")
        else:
            convo = delib_api_get(f"/conversations/{convo_id}")
            if convo:
                st.subheader(convo["topic"])
                st.caption(convo.get("description") or "")
                if not convo.get("is_open", True):
                    st.warning("This conversation is closed.")
            p_notice_key = f"delib_participate_comment_notice_{convo_id}"
            p_notice = st.session_state.pop(p_notice_key, None)
            if p_notice == "pending":
                st.info("Comment submitted. It is awaiting moderation before it appears in the feed.")
            elif p_notice == "approved":
                st.success("Comment submitted and added to the feed.")

            comments = delib_api_get(f"/conversations/{convo_id}/comments?status=approved") or []
            if not comments:
                st.info("No approved comments yet.")
            else:
                default_swipe_mode = public_only and _is_questionnaire_participation_mode()
                swipe_mode = st.toggle(
                    "Swipe mode (mobile-friendly)",
                    value=default_swipe_mode,
                    key=f"delib_swipe_mode_{convo_id}",
                    help="Shows one statement card at a time with real touch swipe gestures.",
                )
                if swipe_mode:
                    _render_swipe_component(comments, convo_id, headers, compact=False)
                else:
                    _render_classic_vote_list(comments, convo_id, headers)

            if convo and convo.get("allow_comment_submission", True):
                st.markdown("### Submit comment")
                new_comment = st.text_area("Your comment", key="delib_submit_comment")
                if st.button(
                    "Submit comment",
                    key="delib_submit_comment_btn",
                    help="Submit a new comment into this conversation (may require moderation).",
                ):
                    text = new_comment.strip()
                    if not text:
                        st.warning("Comment cannot be empty.")
                    elif len(text) < 2:
                        st.warning("Comment should be at least 2 characters.")
                    else:
                        result = delib_api_post(
                            f"/conversations/{convo_id}/comments",
                            {"text": text},
                            headers=headers,
                        )
                        if result:
                            status = str(result.get("status", "")).lower()
                            notice_key = f"delib_participate_comment_notice_{convo_id}"
                            if status == "pending":
                                st.session_state[notice_key] = "pending"
                            else:
                                st.session_state[notice_key] = "approved"
                            st.rerun()
            else:
                st.caption("Comment submission is disabled for this conversation.")

    if not public_only:
        with tab_moderate:
            convo_id = st.session_state.get("delib_conversation_id")
            if not convo_id:
                st.info("Select a conversation first.")
            else:
                pending = delib_api_get(
                    f"/conversations/{convo_id}/comments?status=pending"
                ) or []
                if not pending:
                    st.info("No pending comments.")
                else:
                    for comment in pending:
                        st.markdown(f"**{comment['text']}**")
                        cols = st.columns(2)
                        if cols[0].button(
                            "Approve",
                            key=f"delib-{comment['id']}-approve",
                            help="Approve this pending comment so it becomes voteable.",
                        ):
                            delib_api_patch(
                                f"/comments/{comment['id']}", {"status": "approved"}
                            )
                        if cols[1].button(
                            "Reject",
                            key=f"delib-{comment['id']}-reject",
                            help="Reject this pending comment.",
                        ):
                            delib_api_patch(
                                f"/comments/{comment['id']}", {"status": "rejected"}
                            )
                        st.divider()

    with tab_reports:
        convo_id = st.session_state.get("delib_conversation_id")
        if not convo_id:
            st.info("Select a conversation first.")
        else:
            report_tab, csv_tab = st.tabs(["Vote-based report", "CSV clustering"])

            with report_tab:
                if st.button(
                    "Run analysis",
                    key="delib_run_analysis",
                    help="Compute clusters + consensus/polarizing topics from votes.",
                ):
                    report = delib_api_post(f"/conversations/{convo_id}/analyze", {})
                else:
                    report = delib_api_get(f"/conversations/{convo_id}/report")

                if report:
                    metrics = report["metrics"]
                    total_comments = int(metrics.get("total_comments", 0))
                    total_participants = int(metrics.get("total_participants", 0))
                    total_votes = int(metrics.get("total_votes", 0))
                    st.metric("Comments", total_comments)
                    st.metric("Participants", total_participants)
                    st.metric("Votes", total_votes)
                    avg_votes_per_participant = (
                        round(total_votes / total_participants, 2) if total_participants > 0 else 0.0
                    )
                    st.caption(
                        f"Clustering input: {total_participants} participants, {total_votes} votes "
                        f"(avg {avg_votes_per_participant} votes/participant)."
                    )
                    if total_participants < 2:
                        st.warning("Need at least 2 participants with votes to generate opinion clusters.")
                    elif total_votes < 6:
                        st.info(
                            "Vote volume is still low; clustering may look unstable. "
                            "You can import a one-file CSV dataset from Configure."
                        )

                    st.subheader("Potential agreement topics")
                    potential_agreements = report.get("potential_agreements", [])
                    if potential_agreements:
                        for topic in potential_agreements:
                            st.markdown(f"- {topic}")
                    else:
                        st.caption("No strong agreement topics yet.")

                    st.subheader("Consensus statements")
                    consensus_df = pd.DataFrame(metrics["consensus"])
                    if consensus_df.empty:
                        st.caption("No consensus statements yet.")
                    else:
                        st.dataframe(consensus_df, use_container_width=True)

                    st.subheader("Polarizing statements")
                    polarizing_df = pd.DataFrame(metrics["polarizing"])
                    if polarizing_df.empty:
                        st.caption("No polarizing statements yet.")
                    else:
                        st.dataframe(polarizing_df, use_container_width=True)

                    st.subheader("Cluster summaries")
                    summaries_df = pd.DataFrame(report.get("cluster_summaries", []))
                    if summaries_df.empty:
                        st.caption("No cluster summaries available yet.")
                    else:
                        st.dataframe(summaries_df, use_container_width=True)

                    st.subheader("Cluster similarity")
                    similarity_df = pd.DataFrame(report.get("cluster_similarity", []))
                    if similarity_df.empty:
                        st.caption("No similarity data available yet.")
                    else:
                        similarity_df["similarity"] = similarity_df["similarity"].round(3)
                        st.dataframe(similarity_df, use_container_width=True)

                    st.subheader("Venn diagram: shared agreement topics")
                    summaries = report.get("cluster_summaries", [])
                    if not summaries or len(summaries) < 2:
                        st.caption("Need at least two clusters with agreement topics.")
                    elif plt is None or (venn2 is None and venn3 is None):
                        st.caption("matplotlib-venn is required for Venn diagrams.")
                    else:
                        summaries = sorted(
                            summaries, key=lambda s: s.get("size", 0), reverse=True
                        )
                        selected = summaries[:3]
                        sets = [set(item.get("top_agree", [])) for item in selected]
                        if not any(sets):
                            st.caption("No overlapping agreement topics yet.")
                        else:
                            labels = [
                                f"{item.get('cluster_id')} ({item.get('size', 0)})"
                                for item in selected
                            ]
                            fig, ax = plt.subplots()
                            if len(selected) == 2 and venn2:
                                venn2(sets, set_labels=labels, ax=ax)
                            elif len(selected) >= 3 and venn3:
                                venn3(sets[:3], set_labels=labels[:3], ax=ax)
                            st.pyplot(fig, clear_figure=True)

                    points_df = pd.DataFrame(report.get("points", []))
                    if not points_df.empty:
                        st.subheader("Opinion clusters")
                        chart = (
                            alt.Chart(points_df)
                            .mark_circle(size=60, opacity=0.7)
                            .encode(
                                x="x:Q",
                                y="y:Q",
                                color="cluster_id:N",
                                tooltip=["cluster_id", "participant_id"],
                            )
                        )
                        st.altair_chart(chart, use_container_width=True)
                    elif total_participants >= 2 and total_votes > 0:
                        st.caption(
                            "No cluster chart points available yet. Ensure votes reference approved comment IDs, "
                            "then click Run analysis."
                        )

            with csv_tab:
                st.subheader("CSV clustering workflow")
                st.caption(
                    "Use Configure → One-file CSV import (question + comments + reactions) to import data, then click Run analysis in "
                    "Vote-based report."
                )
                sample_df = pd.DataFrame(
                    [
                        {
                            "participant_id": "anon_001",
                            "comment_id": "comment-uuid-1",
                            "vote": "agree",
                        },
                        {
                            "participant_id": "anon_001",
                            "comment_id": "comment-uuid-2",
                            "vote": "pass",
                        },
                        {
                            "participant_id": "anon_002",
                            "comment_id": "comment-uuid-1",
                            "vote": "disagree",
                        },
                    ]
                )
                st.dataframe(sample_df, use_container_width=True)
