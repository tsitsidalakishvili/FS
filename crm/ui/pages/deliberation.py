import altair as alt
import html
import pandas as pd
import streamlit as st
from uuid import uuid4

try:
    import matplotlib.pyplot as plt
    from matplotlib_venn import venn2, venn3
except Exception:
    plt = None
    venn2 = None
    venn3 = None

from crm.clients.deliberation import (
    delib_api_get,
    delib_api_patch,
    delib_api_post,
    render_delib_api_unavailable,
)
from crm.ui.components.questionnaire import render_questionnaire_block


def _is_questionnaire_participation_mode():
    try:
        value = st.query_params.get("questionnaire")
    except Exception:
        params = st.experimental_get_query_params()
        value = params.get("questionnaire")
    if isinstance(value, list):
        value = value[0] if value else ""
    return str(value or "").strip().lower() == "deliberation"


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


def render_deliberation(public_only: bool):
    st.subheader("Deliberation")
    st.caption("Anonymous comments + votes, consensus analysis, and clustering.")
    st.caption(
        "Deliberation = “What do groups of people think?” (insight/clustering from votes)."
    )

    if "delib_anon_id" not in st.session_state:
        st.session_state["delib_anon_id"] = str(uuid4())
    headers = {"X-Participant-Id": st.session_state["delib_anon_id"]}

    conversations = delib_api_get("/conversations", show_error=False)
    if conversations is None:
        render_delib_api_unavailable()
        return
    conversations = conversations or []
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
                        st.success("Conversation created.")
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

            comments = delib_api_get(f"/conversations/{convo_id}/comments?status=approved") or []
            if not comments:
                st.info("No approved comments yet.")
            else:
                default_swipe_mode = public_only and _is_questionnaire_participation_mode()
                swipe_mode = st.toggle(
                    "Swipe mode (mobile-friendly)",
                    value=default_swipe_mode,
                    key=f"delib_swipe_mode_{convo_id}",
                    help="Shows one statement card at a time with quick left/right/pass actions.",
                )
                if swipe_mode:
                    approved_ids = [comment.get("id") for comment in comments if comment.get("id")]
                    comment_by_id = {comment.get("id"): comment for comment in comments}
                    voted_key = f"delib_swipe_voted_{convo_id}"
                    deck_key = f"delib_swipe_deck_{convo_id}"
                    voted_ids = {
                        cid for cid in st.session_state.get(voted_key, []) if cid in approved_ids
                    }
                    deck = st.session_state.get(deck_key) or []
                    deck = [cid for cid in deck if cid in approved_ids and cid not in voted_ids]
                    for cid in approved_ids:
                        if cid not in deck and cid not in voted_ids:
                            deck.append(cid)
                    st.session_state[voted_key] = list(voted_ids)
                    st.session_state[deck_key] = deck

                    total_cards = len(approved_ids)
                    done_cards = len(voted_ids)
                    progress = (done_cards / total_cards) if total_cards else 0.0
                    st.progress(progress)
                    st.caption(f"{done_cards}/{total_cards} statements voted")

                    st.markdown(
                        """
                        <style>
                        .delib-swipe-card {
                            border: 1px solid #D6EDF8;
                            border-radius: 16px;
                            padding: 22px 18px;
                            background: #FFFFFF;
                            box-shadow: 0 6px 20px rgba(17, 141, 193, 0.10);
                            margin-top: 10px;
                            margin-bottom: 12px;
                        }
                        .delib-swipe-text {
                            font-size: 1.08rem;
                            line-height: 1.5;
                            color: #0B3A52;
                            font-weight: 600;
                        }
                        </style>
                        """,
                        unsafe_allow_html=True,
                    )

                    if not deck:
                        st.success("You have voted on all available statements.")
                        if st.button(
                            "Start over",
                            key=f"delib_swipe_restart_{convo_id}",
                            help="Clear local swipe progress and review all statements again.",
                        ):
                            st.session_state[voted_key] = []
                            st.session_state[deck_key] = approved_ids
                            st.rerun()
                    else:
                        current_id = deck[0]
                        current_comment = comment_by_id.get(current_id, {})
                        current_text = html.escape(str(current_comment.get("text", "")))
                        counts = (
                            f"👍 {current_comment.get('agree_count', 0)}  "
                            f"👎 {current_comment.get('disagree_count', 0)}  "
                            f"➖ {current_comment.get('pass_count', 0)}"
                        )
                        st.markdown(
                            (
                                "<div class='delib-swipe-card'>"
                                f"<div class='delib-swipe-text'>{current_text}</div>"
                                "</div>"
                            ),
                            unsafe_allow_html=True,
                        )
                        st.caption(counts)
                        swipe_cols = st.columns(3)
                        disagree_clicked = swipe_cols[0].button(
                            "👈 Disagree",
                            key=f"delib-swipe-{current_id}-disagree",
                            help="Swipe left style action.",
                            use_container_width=True,
                        )
                        pass_clicked = swipe_cols[1].button(
                            "⏭ Pass",
                            key=f"delib-swipe-{current_id}-pass",
                            help="Skip this statement for now.",
                            use_container_width=True,
                        )
                        agree_clicked = swipe_cols[2].button(
                            "👉 Agree",
                            key=f"delib-swipe-{current_id}-agree",
                            help="Swipe right style action.",
                            use_container_width=True,
                        )
                        choice = -1 if disagree_clicked else 0 if pass_clicked else 1 if agree_clicked else None
                        if choice is not None:
                            ok = _cast_swipe_vote(convo_id, current_id, choice, headers)
                            if ok:
                                voted_ids.add(current_id)
                                st.session_state[voted_key] = list(voted_ids)
                                st.session_state[deck_key] = [cid for cid in deck if cid != current_id]
                                st.rerun()
                else:
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

            if convo and convo.get("allow_comment_submission", True):
                st.markdown("### Submit comment")
                new_comment = st.text_area("Your comment", key="delib_submit_comment")
                if st.button(
                    "Submit comment",
                    key="delib_submit_comment_btn",
                    help="Submit a new comment into this conversation (may require moderation).",
                ):
                    if new_comment.strip():
                        delib_api_post(
                            f"/conversations/{convo_id}/comments",
                            {"text": new_comment},
                            headers=headers,
                        )
                    else:
                        st.warning("Comment cannot be empty.")
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
                    st.metric("Comments", metrics["total_comments"])
                    st.metric("Participants", metrics["total_participants"])
                    st.metric("Votes", metrics["total_votes"])

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

            with csv_tab:
                st.subheader("In progress")
