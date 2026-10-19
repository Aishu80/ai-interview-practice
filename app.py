"""
AI-Powered Interview Practice and Rubric-Based Feedback System
Main Gradio application with 7-tab interface.
"""

import gradio as gr
import json
import os
import time
import tempfile
import traceback
from datetime import datetime
from typing import Optional

# ── Local imports ───────────────────────────────────────────────────────────
from utils.config import get_config, AppConfig
from models.schemas import (
    ResumeProfile, InterviewConfig, MCQSet, MCQuestion,
    MCQResults, WrittenQuestion, WrittenAssessment,
    WrittenAnswerEvaluation, RubricScore, GrammarError,
    FeedbackReport, InterviewSession,
)
from services.ai_client import AIClient
from services.resume_parser import parse_resume, validate_and_parse
from services.resume_analyzer import ResumeAnalyzer
from services.question_generator import QuestionGenerator
from services.interview_engine import InterviewEngine
from services.answer_evaluator import AnswerEvaluator
from services.feedback_generator import FeedbackGenerator
from services.report_generator import ReportGenerator
from utils.scoring import (
    calculate_mcq_results, calculate_written_score,
    calculate_combined_score, get_performance_label,
)
from utils.session_manager import SessionManager
from utils.validators import validate_file, validate_mcq_set

# ── Initialize services ────────────────────────────────────────────────────
config = get_config()
ai_client = AIClient(config)
resume_analyzer = ResumeAnalyzer(ai_client)
question_generator = QuestionGenerator(ai_client)
interview_engine = InterviewEngine()
answer_evaluator = AnswerEvaluator(ai_client)
feedback_generator = FeedbackGenerator(ai_client)
report_generator = ReportGenerator()
session_manager = SessionManager(config.db_path, config.enable_history)


# ═══════════════════════════════════════════════════════════════════════════
# CUSTOM CSS
# ═══════════════════════════════════════════════════════════════════════════

CUSTOM_CSS = """
/* ── Root variables ──────────────────────────────────────────────── */
:root {
    --primary: #4f46e5;
    --primary-light: #818cf8;
    --primary-dark: #3730a3;
    --accent: #06b6d4;
    --success: #10b981;
    --warning: #f59e0b;
    --danger: #ef4444;
    --bg-primary: #f8fafc;
    --bg-card: #ffffff;
    --text-primary: #1e293b;
    --text-secondary: #64748b;
    --text-muted: #94a3b8;
    --border: #e2e8f0;
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
    --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -2px rgba(0,0,0,0.05);
    --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.08), 0 4px 6px -4px rgba(0,0,0,0.05);
    --radius: 12px;
    --radius-sm: 8px;
}

/* ── Global ──────────────────────────────────────────────────────── */
.gradio-container {
    max-width: 1280px !important;
    margin: 0 auto !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    background: var(--bg-primary) !important;
}

/* ── Tab navigation ──────────────────────────────────────────────── */
.tab-nav button {
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    padding: 12px 20px !important;
    border-radius: var(--radius-sm) var(--radius-sm) 0 0 !important;
    transition: all 0.2s ease !important;
    border: none !important;
    color: var(--text-secondary) !important;
    background: transparent !important;
}
.tab-nav button.selected {
    color: var(--primary) !important;
    background: var(--bg-card) !important;
    border-bottom: 3px solid var(--primary) !important;
    box-shadow: var(--shadow-sm) !important;
}
.tab-nav button:hover:not(.selected) {
    color: var(--primary-light) !important;
    background: rgba(79,70,229,0.04) !important;
}

/* ── Cards ───────────────────────────────────────────────────────── */
.card {
    background: var(--bg-card) !important;
    border-radius: var(--radius) !important;
    padding: 24px !important;
    border: 1px solid var(--border) !important;
    box-shadow: var(--shadow-md) !important;
    margin-bottom: 16px !important;
}

/* ── Header banner ───────────────────────────────────────────────── */
.header-banner {
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #06b6d4 100%) !important;
    color: white !important;
    padding: 32px !important;
    border-radius: var(--radius) !important;
    margin-bottom: 24px !important;
    box-shadow: var(--shadow-lg) !important;
}
.header-banner h1 {
    color: white !important;
    font-size: 1.75rem !important;
    font-weight: 800 !important;
    margin: 0 0 8px 0 !important;
    letter-spacing: -0.025em !important;
}
.header-banner p {
    color: rgba(255,255,255,0.9) !important;
    font-size: 1rem !important;
    margin: 0 !important;
    line-height: 1.6 !important;
}

/* ── Status badges ───────────────────────────────────────────────── */
.badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.badge-easy { background: #d1fae5; color: #065f46; }
.badge-medium { background: #fef3c7; color: #92400e; }
.badge-hard { background: #fee2e2; color: #991b1b; }
.badge-success { background: #d1fae5; color: #065f46; }
.badge-warning { background: #fef3c7; color: #92400e; }
.badge-danger { background: #fee2e2; color: #991b1b; }
.badge-info { background: #dbeafe; color: #1e40af; }
.badge-demo { background: #fef3c7; color: #92400e; border: 1px dashed #f59e0b; }

/* ── Stat cards ──────────────────────────────────────────────────── */
.stat-card {
    background: var(--bg-card);
    border-radius: var(--radius);
    padding: 20px;
    border: 1px solid var(--border);
    box-shadow: var(--shadow-sm);
    text-align: center;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.stat-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
}
.stat-value {
    font-size: 2rem;
    font-weight: 800;
    color: var(--primary);
    line-height: 1.2;
}
.stat-label {
    font-size: 0.8rem;
    color: var(--text-secondary);
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 4px;
}

/* ── Progress bar ────────────────────────────────────────────────── */
.progress-container {
    background: #e2e8f0;
    border-radius: 10px;
    height: 12px;
    overflow: hidden;
    margin: 12px 0;
}
.progress-bar {
    background: linear-gradient(90deg, var(--primary), var(--accent));
    height: 100%;
    border-radius: 10px;
    transition: width 0.5s ease;
}

/* ── Buttons ─────────────────────────────────────────────────────── */
.primary-btn {
    background: linear-gradient(135deg, var(--primary), var(--primary-dark)) !important;
    color: white !important;
    border: none !important;
    padding: 12px 28px !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important;
    font-size: 0.925rem !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 4px rgba(79,70,229,0.3) !important;
}
.primary-btn:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(79,70,229,0.4) !important;
}
.secondary-btn {
    background: var(--bg-card) !important;
    color: var(--primary) !important;
    border: 2px solid var(--primary) !important;
    padding: 10px 24px !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
}
.secondary-btn:hover {
    background: rgba(79,70,229,0.05) !important;
}
.success-btn {
    background: linear-gradient(135deg, var(--success), #059669) !important;
    color: white !important;
    border: none !important;
    padding: 12px 28px !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 4px rgba(16,185,129,0.3) !important;
}
.danger-btn {
    background: linear-gradient(135deg, var(--danger), #dc2626) !important;
    color: white !important;
    border: none !important;
    padding: 12px 28px !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important;
}

/* ── Question card ───────────────────────────────────────────────── */
.question-card {
    background: var(--bg-card);
    border-radius: var(--radius);
    padding: 28px;
    border: 1px solid var(--border);
    box-shadow: var(--shadow-md);
    margin: 16px 0;
}
.question-number {
    font-size: 0.85rem;
    font-weight: 700;
    color: var(--primary);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 12px;
}
.question-text {
    font-size: 1.1rem;
    color: var(--text-primary);
    line-height: 1.7;
    font-weight: 500;
}

/* ── Report sections ─────────────────────────────────────────────── */
.report-section {
    background: var(--bg-card);
    border-radius: var(--radius);
    padding: 24px;
    margin: 16px 0;
    border: 1px solid var(--border);
    box-shadow: var(--shadow-sm);
}
.report-section h3 {
    color: var(--text-primary);
    font-size: 1.1rem;
    font-weight: 700;
    margin: 0 0 16px 0;
    padding-bottom: 12px;
    border-bottom: 2px solid var(--border);
}

/* ── Score display ───────────────────────────────────────────────── */
.score-excellent { color: #059669; }
.score-good { color: #2563eb; }
.score-average { color: #d97706; }
.score-poor { color: #dc2626; }

/* ── Empty state ─────────────────────────────────────────────────── */
.empty-state {
    text-align: center;
    padding: 48px 24px;
    color: var(--text-muted);
}
.empty-state-icon {
    font-size: 3rem;
    margin-bottom: 16px;
}
.empty-state-text {
    font-size: 1rem;
    line-height: 1.6;
}

/* ── Info box ────────────────────────────────────────────────────── */
.info-box {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-left: 4px solid var(--primary);
    border-radius: var(--radius-sm);
    padding: 16px 20px;
    margin: 12px 0;
    color: #1e40af;
    font-size: 0.9rem;
    line-height: 1.6;
}
.warning-box {
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-left: 4px solid var(--warning);
    border-radius: var(--radius-sm);
    padding: 16px 20px;
    margin: 12px 0;
    color: #92400e;
}
.success-box {
    background: #ecfdf5;
    border: 1px solid #a7f3d0;
    border-left: 4px solid var(--success);
    border-radius: var(--radius-sm);
    padding: 16px 20px;
    margin: 12px 0;
    color: #065f46;
}
.error-box {
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-left: 4px solid var(--danger);
    border-radius: var(--radius-sm);
    padding: 16px 20px;
    margin: 12px 0;
    color: #991b1b;
}

/* ── Interview option styling ────────────────────────────────────── */
.option-btn {
    text-align: left !important;
    padding: 14px 20px !important;
    margin: 6px 0 !important;
    border-radius: var(--radius-sm) !important;
    border: 2px solid var(--border) !important;
    background: var(--bg-card) !important;
    font-size: 0.95rem !important;
    transition: all 0.15s ease !important;
    cursor: pointer !important;
}
.option-btn:hover {
    border-color: var(--primary-light) !important;
    background: rgba(79,70,229,0.03) !important;
}
.option-selected {
    border-color: var(--primary) !important;
    background: rgba(79,70,229,0.06) !important;
    box-shadow: 0 0 0 1px var(--primary) !important;
}

/* ── Demo mode banner ────────────────────────────────────────────── */
.demo-banner {
    background: linear-gradient(90deg, #fef3c7, #fde68a);
    border: 1px solid #f59e0b;
    border-radius: var(--radius-sm);
    padding: 12px 20px;
    margin-bottom: 16px;
    text-align: center;
    font-weight: 600;
    color: #92400e;
    font-size: 0.85rem;
}

/* ── Responsive ──────────────────────────────────────────────────── */
@media (max-width: 768px) {
    .header-banner { padding: 20px !important; }
    .header-banner h1 { font-size: 1.3rem !important; }
    .stat-value { font-size: 1.5rem; }
}

/* ── Markdown content ────────────────────────────────────────────── */
.markdown-content h1, .markdown-content h2, .markdown-content h3 {
    color: var(--text-primary) !important;
}
.markdown-content p {
    color: var(--text-secondary) !important;
    line-height: 1.7 !important;
}
"""


# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def get_demo_banner() -> str:
    """Return a demo mode notice if running without API key."""
    if config.demo_mode:
        return (
            '<div class="demo-banner">'
            '⚠️ DEMO MODE — No OpenAI API key configured. '
            'Results are generated locally and do not reflect actual AI evaluation. '
            'Set OPENAI_API_KEY in your .env file for full functionality.'
            '</div>'
        )
    return ""


def format_profile_card(profile: ResumeProfile) -> str:
    """Format a ResumeProfile into displayable HTML card."""
    sections = []

    def _make_section(title: str, icon: str, items) -> str:
        if not items:
            return ""
        html = f'<div class="report-section"><h3>{icon} {title}</h3>'
        if isinstance(items, list):
            if items and isinstance(items[0], dict):
                for item in items:
                    parts = []
                    for k, v in item.items():
                        if v:
                            parts.append(f"<strong>{k.replace('_',' ').title()}:</strong> {v}")
                    html += '<div style="margin:8px 0;padding:10px;background:#f8fafc;border-radius:8px;">'
                    html += "<br>".join(parts) + "</div>"
            else:
                tags = "".join(
                    f'<span style="display:inline-block;background:#eef2ff;color:#4338ca;'
                    f'padding:4px 12px;border-radius:16px;margin:3px;font-size:0.85rem;'
                    f'font-weight:500;">{item}</span>'
                    for item in items if item
                )
                html += tags
        html += "</div>"
        return html

    sections.append(_make_section("Education", "🎓", profile.education))
    sections.append(_make_section("Technical Skills", "🛠️", profile.skills))
    sections.append(_make_section("Programming Languages", "💻", profile.programming_languages))
    sections.append(_make_section("Frameworks & Tools", "🔧", profile.frameworks_tools))
    sections.append(_make_section("Projects", "📁", profile.projects))
    sections.append(_make_section("Work Experience", "💼", profile.work_experience))
    sections.append(_make_section("Internships", "🏢", profile.internships))
    sections.append(_make_section("Certifications", "📜", profile.certifications))
    sections.append(_make_section("Interview Topics", "🎯", profile.interview_topics))

    if profile.target_role:
        sections.append(
            f'<div class="report-section"><h3>🎯 Suggested Target Role</h3>'
            f'<span class="badge badge-info">{profile.target_role}</span></div>'
        )
    if profile.missing_info:
        sections.append(_make_section("Missing Information", "⚠️", profile.missing_info))

    return "\n".join(s for s in sections if s)


def format_mcq_for_display(question: dict, index: int, total: int,
                           selected: int = -1) -> str:
    """Format an MCQ for the interview interface."""
    diff = question.get("difficulty", "easy")
    badge_cls = f"badge-{diff}"
    domain = question.get("domain", "")
    topic = question.get("topic", "")

    header = (
        f'<div class="question-card">'
        f'<div class="question-number">Question {index + 1} of {total}</div>'
        f'<div style="margin-bottom:12px;">'
        f'<span class="badge {badge_cls}">{diff.upper()}</span> '
        f'<span class="badge badge-info">{domain}</span>'
    )
    if topic:
        header += f' <span class="badge" style="background:#f1f5f9;color:#475569;">{topic}</span>'
    header += "</div>"
    header += f'<div class="question-text">{question.get("question_text", "")}</div></div>'
    return header


def format_progress_bar(answered: int, total: int) -> str:
    """Format an HTML progress bar."""
    pct = (answered / total * 100) if total > 0 else 0
    return (
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin:8px 0;">'
        f'<span style="font-weight:600;color:var(--text-secondary);font-size:0.85rem;">'
        f'Progress: {answered}/{total} answered</span>'
        f'<span style="font-weight:700;color:var(--primary);font-size:0.9rem;">{pct:.0f}%</span></div>'
        f'<div class="progress-container">'
        f'<div class="progress-bar" style="width:{pct}%"></div></div>'
    )


def build_plotly_charts(mcq_results: MCQResults,
                        written_assessment: Optional[WrittenAssessment],
                        domain_scores: dict):
    """Build Plotly figures for the performance report."""
    import plotly.graph_objects as go

    charts = {}

    # 1. Domain-wise score bar chart
    if domain_scores:
        domains = []
        scores = []
        colors = []
        for d, info in domain_scores.items():
            if isinstance(info, dict):
                s = info.get("score")
                if s is not None:
                    domains.append(d)
                    scores.append(s)
                    colors.append(
                        "#10b981" if s >= 75 else "#f59e0b" if s >= 50 else "#ef4444"
                    )
            elif isinstance(info, (int, float)):
                domains.append(d)
                scores.append(info)
                colors.append(
                    "#10b981" if info >= 75 else "#f59e0b" if info >= 50 else "#ef4444"
                )
        if domains:
            fig = go.Figure(data=[go.Bar(
                x=scores, y=domains, orientation='h',
                marker_color=colors,
                text=[f"{s:.0f}%" for s in scores],
                textposition='auto',
            )])
            fig.update_layout(
                title="Domain-Wise Performance",
                xaxis_title="Score (%)", yaxis_title="",
                xaxis=dict(range=[0, 100]),
                height=max(300, len(domains) * 45 + 100),
                margin=dict(l=180, r=40, t=50, b=40),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif"),
            )
            charts["domain"] = fig

    # 2. Difficulty-wise performance
    diff_labels = ["Easy", "Medium", "Hard"]
    diff_scores = [
        mcq_results.easy_accuracy,
        mcq_results.medium_accuracy,
        mcq_results.hard_accuracy,
    ]
    diff_totals = [mcq_results.easy_total, mcq_results.medium_total, mcq_results.hard_total]
    diff_correct = [mcq_results.easy_correct, mcq_results.medium_correct, mcq_results.hard_correct]

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        name="Correct", x=diff_labels, y=diff_correct,
        marker_color="#10b981", text=diff_correct, textposition='auto',
    ))
    fig2.add_trace(go.Bar(
        name="Total", x=diff_labels,
        y=[t - c for t, c in zip(diff_totals, diff_correct)],
        marker_color="#e2e8f0",
        text=[f"{t-c}" for t, c in zip(diff_totals, diff_correct)],
        textposition='auto',
    ))
    fig2.update_layout(
        title="Difficulty-Wise Performance",
        barmode="stack",
        xaxis_title="Difficulty", yaxis_title="Questions",
        height=350, margin=dict(l=40, r=40, t=50, b=40),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    charts["difficulty"] = fig2

    # 3. Topic-wise accuracy
    if mcq_results.topic_accuracy:
        topics = []
        accuracies = []
        for topic, info in mcq_results.topic_accuracy.items():
            if isinstance(info, dict):
                total = info.get("total", 0)
                correct = info.get("correct", 0)
                if total > 0:
                    topics.append(f"{topic} ({correct}/{total})")
                    accuracies.append(correct / total * 100)
        if topics:
            colors3 = [
                "#10b981" if a >= 75 else "#f59e0b" if a >= 50 else "#ef4444"
                for a in accuracies
            ]
            fig3 = go.Figure(data=[go.Bar(
                x=accuracies, y=topics, orientation='h',
                marker_color=colors3,
                text=[f"{a:.0f}%" for a in accuracies],
                textposition='auto',
            )])
            fig3.update_layout(
                title="Topic-Wise Accuracy",
                xaxis_title="Accuracy (%)", yaxis_title="",
                xaxis=dict(range=[0, 100]),
                height=max(300, len(topics) * 40 + 100),
                margin=dict(l=200, r=40, t=50, b=40),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif"),
            )
            charts["topic"] = fig3

    return charts


# ═══════════════════════════════════════════════════════════════════════════
# GRADIO APPLICATION
# ═══════════════════════════════════════════════════════════════════════════

def create_app() -> gr.Blocks:
    """Build and return the Gradio Blocks application."""

    with gr.Blocks(
        title="AI Interview Practice Platform",
    ) as app:

        # ── Session state ────────────────────────────────────────────
        session_state = gr.State(value={
            "profile": None,
            "config": None,
            "session_id": None,
            "mcq_set": None,
            "user_answers": {},
            "current_q": 0,
            "mcq_submitted": False,
            "mcq_results": None,
            "written_questions": [],
            "written_answers": {},
            "written_submitted": False,
            "written_assessment": None,
            "feedback_report": None,
            "resume_text": "",
            "start_time": None,
        })

        # ── Global header ────────────────────────────────────────────
        gr.HTML(
            '<div class="header-banner">'
            '<h1>🎯 AI Interview Practice Platform</h1>'
            '<p>Master your interview skills with AI-powered personalized practice, '
            'rubric-based feedback, and comprehensive performance analytics.</p>'
            '</div>'
        )

        demo_html = get_demo_banner()
        if demo_html:
            gr.HTML(demo_html)

        # ══════════════════════════════════════════════════════════════
        # TABS
        # ══════════════════════════════════════════════════════════════

        with gr.Tabs() as tabs:

            # ─────────────────────────────────────────────────────────
            # TAB 1: DASHBOARD
            # ─────────────────────────────────────────────────────────
            with gr.Tab("📊 Dashboard", id=0):
                gr.HTML(
                    '<div class="card">'
                    '<h2 style="color:var(--text-primary);margin:0 0 8px 0;">Welcome to AI Interview Practice</h2>'
                    '<p style="color:var(--text-secondary);line-height:1.7;margin:0;">'
                    'Prepare for your next interview with AI-generated personalized questions, '
                    'real-time feedback, and detailed performance analytics. '
                    'Upload your resume to get started.</p>'
                    '</div>'
                )
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.HTML(
                            '<div class="stat-card">'
                            '<div class="stat-value">📝</div>'
                            '<div class="stat-label">Step 1: Upload Resume</div>'
                            '</div>'
                        )
                    with gr.Column(scale=1):
                        gr.HTML(
                            '<div class="stat-card">'
                            '<div class="stat-value">⚙️</div>'
                            '<div class="stat-label">Step 2: Configure Interview</div>'
                            '</div>'
                        )
                    with gr.Column(scale=1):
                        gr.HTML(
                            '<div class="stat-card">'
                            '<div class="stat-value">🎯</div>'
                            '<div class="stat-label">Step 3: Take Interview</div>'
                            '</div>'
                        )
                    with gr.Column(scale=1):
                        gr.HTML(
                            '<div class="stat-card">'
                            '<div class="stat-value">📈</div>'
                            '<div class="stat-label">Step 4: Get Feedback</div>'
                            '</div>'
                        )

                gr.HTML(
                    '<div class="info-box">'
                    '<strong>How it works:</strong><br>'
                    '1️⃣ Upload your resume (PDF, DOCX, or TXT)<br>'
                    '2️⃣ Review and confirm extracted profile information<br>'
                    '3️⃣ Configure your interview type, difficulty, and focus areas<br>'
                    '4️⃣ Complete 20 AI-generated multiple-choice questions<br>'
                    '5️⃣ Answer 3 open-ended written assessment questions<br>'
                    '6️⃣ Receive detailed performance analysis with improvement recommendations'
                    '</div>'
                )

                dash_history_html = gr.HTML(value="", visible=True)

                start_btn = gr.Button(
                    "🚀 Start New Interview",
                    elem_classes=["primary-btn"],
                    size="lg",
                )

                def load_dashboard():
                    sessions = session_manager.get_all_sessions()
                    if not sessions:
                        return (
                            '<div class="empty-state">'
                            '<div class="empty-state-icon">📋</div>'
                            '<div class="empty-state-text">No previous interviews yet. '
                            'Start your first interview to see your history here!</div>'
                            '</div>'
                        )
                    html = '<div class="report-section"><h3>📋 Recent Interview History</h3>'
                    for s in sessions[:5]:
                        score_display = f"{s.get('mcq_score', 0):.0f}%"
                        role = s.get("target_role", "N/A")
                        itype = s.get("interview_type", "N/A")
                        date = s.get("created_at", "")[:10]
                        label = get_performance_label(s.get("mcq_score", 0))
                        color_cls = (
                            "score-excellent" if label == "Excellent"
                            else "score-good" if label == "Good"
                            else "score-average" if label == "Average"
                            else "score-poor"
                        )
                        html += (
                            f'<div style="display:flex;justify-content:space-between;'
                            f'align-items:center;padding:12px;margin:6px 0;'
                            f'background:#f8fafc;border-radius:8px;border:1px solid #e2e8f0;">'
                            f'<div><strong>{role}</strong> — {itype.title()} '
                            f'<span style="color:#94a3b8;font-size:0.85rem;">({date})</span></div>'
                            f'<div class="{color_cls}" style="font-weight:700;">'
                            f'{score_display} ({label})</div></div>'
                        )
                    html += "</div>"
                    return html

                app.load(load_dashboard, outputs=[dash_history_html])

                start_btn.click(
                    lambda: gr.Tabs(selected=1),
                    outputs=[tabs],
                )

            # ─────────────────────────────────────────────────────────
            # TAB 2: RESUME ANALYSIS
            # ─────────────────────────────────────────────────────────
            with gr.Tab("📄 Resume Analysis", id=1):
                gr.HTML(
                    '<div class="card"><h2 style="margin:0 0 8px 0;color:var(--text-primary);">'
                    '📄 Resume Upload & Analysis</h2>'
                    '<p style="color:var(--text-secondary);margin:0;">'
                    'Upload your resume to extract skills, experience, and relevant '
                    'information for personalised interview questions.</p></div>'
                )

                with gr.Row():
                    with gr.Column(scale=2):
                        resume_file = gr.File(
                            label="Upload Resume (PDF, DOCX, or TXT — max 10 MB)",
                            file_types=[".pdf", ".docx", ".txt"],
                            type="filepath",
                        )
                        upload_status = gr.HTML(value="")

                        with gr.Row():
                            extract_btn = gr.Button(
                                "📑 Extract Text", elem_classes=["secondary-btn"],
                            )
                            analyze_btn = gr.Button(
                                "🔍 Analyze Resume", elem_classes=["primary-btn"],
                            )

                    with gr.Column(scale=3):
                        resume_text_display = gr.Textbox(
                            label="Extracted Resume Text",
                            lines=12,
                            interactive=False,
                            placeholder="Resume text will appear here after extraction…",
                        )

                analysis_status = gr.HTML(value="")
                profile_display = gr.HTML(value="")

                with gr.Accordion("✏️ Edit Profile", open=False):
                    edit_skills = gr.Textbox(
                        label="Skills (comma-separated)",
                        placeholder="Python, Java, SQL, …",
                    )
                    edit_role = gr.Textbox(
                        label="Target Job Role",
                        placeholder="e.g. Software Developer",
                    )
                    edit_projects = gr.Textbox(
                        label="Key Projects (one per line)",
                        lines=3,
                        placeholder="Project Name — Description",
                    )

                confirm_profile_btn = gr.Button(
                    "✅ Confirm Profile & Continue",
                    elem_classes=["success-btn"],
                    size="lg",
                )
                confirm_status = gr.HTML(value="")

                # ── Resume handlers ──────────────────────────────────
                def handle_extract(file_path, state):
                    if file_path is None:
                        return (
                            "",
                            '<div class="warning-box">⚠️ Please upload a resume file first.</div>',
                            state,
                        )
                    try:
                        text, err = validate_and_parse(
                            file_path, config.max_file_size_bytes
                        )
                        if err:
                            return (
                                "",
                                f'<div class="error-box">❌ {err}</div>',
                                state,
                            )
                        state["resume_text"] = text
                        return (
                            text,
                            '<div class="success-box">✅ Resume text extracted successfully! '
                            'Click <b>Analyze Resume</b> to identify skills and experience.</div>',
                            state,
                        )
                    except Exception as e:
                        return (
                            "",
                            f'<div class="error-box">❌ Extraction failed: {e}</div>',
                            state,
                        )

                def handle_analyze(resume_text, state):
                    if not resume_text or not resume_text.strip():
                        return (
                            '<div class="warning-box">⚠️ Please extract resume text first.</div>',
                            "",
                            "", "", "",
                            state,
                        )
                    try:
                        profile = resume_analyzer.analyze(resume_text)
                        state["profile"] = profile
                        profile_html = format_profile_card(profile)
                        skills_str = ", ".join(
                            profile.skills + profile.programming_languages + profile.frameworks_tools
                        )
                        projects_str = "\n".join(
                            f"{p.get('name', 'Project')} — {p.get('description', '')}"
                            for p in profile.projects
                        ) if profile.projects else ""
                        demo_note = " (Demo analysis)" if config.demo_mode else ""
                        return (
                            f'<div class="success-box">✅ Resume analyzed successfully!{demo_note} '
                            f'Review the extracted information below, edit if needed, '
                            f'then confirm to continue.</div>',
                            profile_html,
                            skills_str,
                            profile.target_role,
                            projects_str,
                            state,
                        )
                    except Exception as e:
                        return (
                            f'<div class="error-box">❌ Analysis failed: {e}</div>',
                            "", "", "", "",
                            state,
                        )

                def handle_confirm_profile(skills_text, role_text, projects_text, state):
                    profile = state.get("profile")
                    if profile is None:
                        return (
                            '<div class="error-box">❌ Please analyze your resume first.</div>',
                            state,
                            gr.Tabs(),
                        )
                    # Apply edits
                    if skills_text.strip():
                        all_skills = [s.strip() for s in skills_text.split(",") if s.strip()]
                        profile.skills = all_skills
                    if role_text.strip():
                        profile.target_role = role_text.strip()
                    if projects_text.strip():
                        projects = []
                        for line in projects_text.strip().split("\n"):
                            if "—" in line:
                                name, desc = line.split("—", 1)
                                projects.append({"name": name.strip(), "description": desc.strip()})
                            elif line.strip():
                                projects.append({"name": line.strip(), "description": ""})
                        if projects:
                            profile.projects = projects
                    state["profile"] = profile
                    return (
                        '<div class="success-box">✅ Profile confirmed! '
                        'Proceed to <b>Interview Setup</b>.</div>',
                        state,
                        gr.Tabs(selected=2),
                    )

                extract_btn.click(
                    handle_extract,
                    inputs=[resume_file, session_state],
                    outputs=[resume_text_display, upload_status, session_state],
                )
                analyze_btn.click(
                    handle_analyze,
                    inputs=[resume_text_display, session_state],
                    outputs=[
                        analysis_status, profile_display,
                        edit_skills, edit_role, edit_projects,
                        session_state,
                    ],
                )
                confirm_profile_btn.click(
                    handle_confirm_profile,
                    inputs=[edit_skills, edit_role, edit_projects, session_state],
                    outputs=[confirm_status, session_state, tabs],
                )

            # ─────────────────────────────────────────────────────────
            # TAB 3: INTERVIEW SETUP
            # ─────────────────────────────────────────────────────────
            with gr.Tab("⚙️ Interview Setup", id=2):
                gr.HTML(
                    '<div class="card"><h2 style="margin:0 0 8px 0;color:var(--text-primary);">'
                    '⚙️ Interview Configuration</h2>'
                    '<p style="color:var(--text-secondary);margin:0;">'
                    'Customize your interview type, difficulty, and focus areas.</p></div>'
                )

                with gr.Row():
                    with gr.Column(scale=1):
                        setup_role = gr.Textbox(
                            label="Target Job Role",
                            placeholder="e.g. Software Developer, Data Analyst",
                        )
                        setup_type = gr.Dropdown(
                            label="Interview Type",
                            choices=["Technical", "HR", "Aptitude", "Mixed"],
                            value="Technical",
                        )
                        setup_level = gr.Dropdown(
                            label="Experience Level",
                            choices=["Fresher", "Entry-Level Professional", "Experienced Professional"],
                            value="Fresher",
                        )
                        setup_difficulty = gr.Dropdown(
                            label="Difficulty Mode",
                            choices=["Progressive", "Adaptive"],
                            value="Progressive",
                        )

                    with gr.Column(scale=1):
                        setup_focus = gr.CheckboxGroup(
                            label="Focus Areas",
                            choices=[
                                "Resume Skills", "Resume Projects",
                                "Technical Knowledge", "Logical Reasoning",
                                "Problem Solving", "Grammar",
                                "Sentence Formation", "Communication",
                                "Behavioral Questions",
                            ],
                            value=["Resume Skills", "Technical Knowledge"],
                        )
                        setup_jd = gr.Textbox(
                            label="Job Description (Optional)",
                            lines=3,
                            placeholder="Paste the job description for more targeted questions…",
                        )
                        setup_topics = gr.Textbox(
                            label="Additional Topics (Optional)",
                            placeholder="e.g. Docker, CI/CD, REST APIs",
                        )

                setup_config_summary = gr.HTML(value="")
                setup_status = gr.HTML(value="")

                with gr.Row():
                    reset_setup_btn = gr.Button(
                        "🔄 Reset Form", elem_classes=["secondary-btn"],
                    )
                    start_interview_btn = gr.Button(
                        "🚀 Start Interview",
                        elem_classes=["primary-btn"],
                        size="lg",
                    )

                def populate_setup(state):
                    profile = state.get("profile")
                    if profile and profile.target_role:
                        return profile.target_role
                    return ""

                # Populate role from profile when tab loads
                tabs.select(
                    populate_setup,
                    inputs=[session_state],
                    outputs=[setup_role],
                )

                def handle_reset_setup():
                    return (
                        "",
                        "Technical",
                        "Fresher",
                        "Progressive",
                        ["Resume Skills", "Technical Knowledge"],
                        "", "",
                        "",
                        "",
                    )

                reset_setup_btn.click(
                    handle_reset_setup,
                    outputs=[
                        setup_role, setup_type, setup_level,
                        setup_difficulty, setup_focus, setup_jd, setup_topics,
                        setup_config_summary, setup_status,
                    ],
                )

                def handle_start_interview(
                    role, itype, level, diff_mode, focus, jd, topics, state
                ):
                    profile = state.get("profile")
                    if profile is None:
                        return (
                            '<div class="error-box">❌ Please complete the Resume Analysis '
                            'step first.</div>',
                            "",
                            state,
                            gr.Tabs(),
                        )
                    if not role.strip():
                        return (
                            '<div class="warning-box">⚠️ Please enter a target job role.</div>',
                            "",
                            state,
                            gr.Tabs(),
                        )

                    # Map display values to internal values
                    type_map = {
                        "Technical": "technical", "HR": "hr",
                        "Aptitude": "aptitude", "Mixed": "mixed",
                    }
                    level_map = {
                        "Fresher": "fresher",
                        "Entry-Level Professional": "entry_level",
                        "Experienced Professional": "experienced",
                    }
                    diff_map = {"Progressive": "progressive", "Adaptive": "adaptive"}

                    interview_config = InterviewConfig(
                        target_role=role.strip(),
                        interview_type=type_map.get(itype, "technical"),
                        experience_level=level_map.get(level, "fresher"),
                        difficulty_mode=diff_map.get(diff_mode, "progressive"),
                        focus_areas=focus if focus else ["Resume Skills", "Technical Knowledge"],
                        job_description=jd.strip(),
                        additional_topics=topics.strip(),
                    )
                    state["config"] = interview_config

                    # Generate questions
                    try:
                        mcq_set = question_generator.generate_questions(
                            profile, interview_config
                        )
                        state["mcq_set"] = mcq_set
                        state["user_answers"] = {}
                        state["current_q"] = 0
                        state["mcq_submitted"] = False
                        state["mcq_results"] = None
                        state["written_submitted"] = False
                        state["written_assessment"] = None
                        state["feedback_report"] = None
                        state["start_time"] = datetime.now().isoformat()

                        # Create engine session
                        session = interview_engine.create_session(
                            profile, interview_config, mcq_set
                        )
                        state["session_id"] = session.session_id

                        config_summary = (
                            f'<div class="info-box">'
                            f'<strong>Interview Configuration:</strong><br>'
                            f'• Role: {role}<br>'
                            f'• Type: {itype}<br>'
                            f'• Level: {level}<br>'
                            f'• Difficulty: {diff_mode}<br>'
                            f'• Focus: {", ".join(focus)}<br>'
                            f'• Questions: {len(mcq_set.questions)}'
                            f'</div>'
                        )
                        demo_note = " (Demo questions)" if config.demo_mode else ""
                        return (
                            f'<div class="success-box">✅ Interview ready!{demo_note} '
                            f'{len(mcq_set.questions)} questions generated. '
                            f'Switching to Mock Interview…</div>',
                            config_summary,
                            state,
                            gr.Tabs(selected=3),
                        )
                    except Exception as e:
                        return (
                            f'<div class="error-box">❌ Failed to generate questions: {e}</div>',
                            "",
                            state,
                            gr.Tabs(),
                        )

                start_interview_btn.click(
                    handle_start_interview,
                    inputs=[
                        setup_role, setup_type, setup_level,
                        setup_difficulty, setup_focus, setup_jd, setup_topics,
                        session_state,
                    ],
                    outputs=[setup_status, setup_config_summary, session_state, tabs],
                )

            # ─────────────────────────────────────────────────────────
            # TAB 4: MOCK INTERVIEW
            # ─────────────────────────────────────────────────────────
            with gr.Tab("🎯 Mock Interview", id=3):
                interview_header = gr.HTML(
                    '<div class="card"><h2 style="margin:0 0 8px 0;color:var(--text-primary);">'
                    '🎯 Mock Interview</h2>'
                    '<p style="color:var(--text-secondary);margin:0;">'
                    'Answer each question carefully. You can navigate between questions '
                    'and change your answers before submitting.</p></div>'
                )

                interview_progress = gr.HTML(value="")
                question_display = gr.HTML(value="")

                answer_radio = gr.Radio(
                    label="Select your answer:",
                    choices=["A", "B", "C", "D"],
                    value=None,
                    interactive=True,
                )

                with gr.Row():
                    prev_btn = gr.Button(
                        "⬅️ Previous", elem_classes=["secondary-btn"],
                    )
                    save_btn = gr.Button(
                        "💾 Save Answer", elem_classes=["primary-btn"],
                    )
                    next_btn = gr.Button(
                        "➡️ Next", elem_classes=["secondary-btn"],
                    )

                interview_status = gr.HTML(value="")

                submit_interview_btn = gr.Button(
                    "✅ Submit Interview",
                    elem_classes=["success-btn"],
                    size="lg",
                )
                submit_confirm = gr.HTML(value="")

                def load_question(state):
                    mcq_set = state.get("mcq_set")
                    if mcq_set is None or not mcq_set.questions:
                        return (
                            format_progress_bar(0, 20),
                            '<div class="empty-state"><div class="empty-state-icon">📝</div>'
                            '<div class="empty-state-text">No interview in progress. '
                            'Please go to Interview Setup to start.</div></div>',
                            gr.Radio(choices=[], value=None),
                            "",
                            state,
                        )
                    if state.get("mcq_submitted"):
                        return (
                            format_progress_bar(20, 20),
                            '<div class="success-box">✅ Interview submitted! '
                            'Proceed to the Written Assessment tab.</div>',
                            gr.Radio(choices=[], value=None),
                            "",
                            state,
                        )

                    idx = state.get("current_q", 0)
                    questions = mcq_set.questions
                    total = len(questions)
                    idx = max(0, min(idx, total - 1))
                    state["current_q"] = idx

                    q = questions[idx]
                    q_dict = q.to_safe_dict()
                    answered = len(state.get("user_answers", {}))
                    progress_html = format_progress_bar(answered, total)
                    question_html = format_mcq_for_display(q_dict, idx, total)

                    # Prepare radio options
                    options = [f"{chr(65+i)}. {opt}" for i, opt in enumerate(q.options)]
                    # Check if already answered
                    current_answer = state.get("user_answers", {}).get(q.id, -1)
                    radio_value = None
                    if current_answer >= 0 and current_answer < len(options):
                        radio_value = options[current_answer]

                    return (
                        progress_html,
                        question_html,
                        gr.Radio(choices=options, value=radio_value, interactive=True),
                        "",
                        state,
                    )

                def save_answer(selected, state):
                    mcq_set = state.get("mcq_set")
                    if mcq_set is None or state.get("mcq_submitted"):
                        return '<div class="warning-box">⚠️ No active interview.</div>', state

                    idx = state.get("current_q", 0)
                    q = mcq_set.questions[idx]
                    answers = state.get("user_answers", {})

                    if selected is None:
                        return '<div class="info-box">ℹ️ No option selected.</div>', state

                    # Parse selection index from "A. ..." format
                    option_idx = ord(selected[0]) - 65
                    answers[q.id] = option_idx
                    state["user_answers"] = answers

                    # Also save in engine
                    sid = state.get("session_id")
                    if sid:
                        interview_engine.save_answer(sid, q.id, option_idx)

                    answered = len(answers)
                    return (
                        f'<div class="success-box">✅ Answer saved ({answered}/20 answered)</div>',
                        state,
                    )

                def navigate(direction, state):
                    mcq_set = state.get("mcq_set")
                    if mcq_set is None:
                        return ("", "", gr.Radio(choices=[], value=None), "", state)

                    idx = state.get("current_q", 0)
                    total = len(mcq_set.questions)
                    if direction == "next":
                        idx = min(idx + 1, total - 1)
                    elif direction == "prev":
                        idx = max(idx - 1, 0)
                    state["current_q"] = idx
                    return load_question(state)

                def handle_submit_interview(state):
                    mcq_set = state.get("mcq_set")
                    if mcq_set is None:
                        return (
                            '<div class="error-box">❌ No active interview.</div>',
                            state,
                            gr.Tabs(),
                        )
                    if state.get("mcq_submitted"):
                        return (
                            '<div class="warning-box">⚠️ Interview already submitted.</div>',
                            state,
                            gr.Tabs(),
                        )

                    answers = state.get("user_answers", {})
                    unanswered = len(mcq_set.questions) - len(answers)

                    # Calculate results
                    mcq_results = calculate_mcq_results(
                        mcq_set.questions, answers
                    )
                    state["mcq_results"] = mcq_results
                    state["mcq_submitted"] = True

                    # Save in engine
                    sid = state.get("session_id")
                    if sid:
                        interview_engine.submit_interview(sid)
                        session = interview_engine.get_session(sid)
                        if session:
                            session.mcq_results = mcq_results

                    # Generate written questions
                    try:
                        profile = state.get("profile")
                        icfg = state.get("config")
                        written_qs = answer_evaluator.generate_written_questions(
                            profile, icfg
                        )
                        state["written_questions"] = written_qs
                        state["written_answers"] = {}
                    except Exception:
                        state["written_questions"] = []

                    label = get_performance_label(mcq_results.accuracy)
                    return (
                        f'<div class="success-box">✅ Interview submitted!<br>'
                        f'Score: <strong>{mcq_results.accuracy:.1f}%</strong> ({label})<br>'
                        f'Correct: {mcq_results.correct} | '
                        f'Incorrect: {mcq_results.incorrect} | '
                        f'Unanswered: {mcq_results.unanswered}<br><br>'
                        f'Proceed to the <b>Written Assessment</b> tab for the next part.</div>',
                        state,
                        gr.Tabs(selected=4),
                    )

                # Wire interview events
                # Load question when tab is selected
                tabs.select(
                    load_question,
                    inputs=[session_state],
                    outputs=[
                        interview_progress, question_display,
                        answer_radio, interview_status, session_state,
                    ],
                )
                save_btn.click(
                    save_answer,
                    inputs=[answer_radio, session_state],
                    outputs=[interview_status, session_state],
                )
                prev_btn.click(
                    lambda s: navigate("prev", s),
                    inputs=[session_state],
                    outputs=[
                        interview_progress, question_display,
                        answer_radio, interview_status, session_state,
                    ],
                )
                next_btn.click(
                    lambda s: navigate("next", s),
                    inputs=[session_state],
                    outputs=[
                        interview_progress, question_display,
                        answer_radio, interview_status, session_state,
                    ],
                )
                submit_interview_btn.click(
                    handle_submit_interview,
                    inputs=[session_state],
                    outputs=[submit_confirm, session_state, tabs],
                )

            # ─────────────────────────────────────────────────────────
            # TAB 5: WRITTEN ASSESSMENT
            # ─────────────────────────────────────────────────────────
            with gr.Tab("✍️ Written Assessment", id=4):
                gr.HTML(
                    '<div class="card"><h2 style="margin:0 0 8px 0;color:var(--text-primary);">'
                    '✍️ Written Assessment</h2>'
                    '<p style="color:var(--text-secondary);margin:0;">'
                    'Answer the following open-ended questions. Your responses will be evaluated '
                    'for communication clarity, grammar, relevance, and technical understanding.</p></div>'
                )

                written_status = gr.HTML(value="")

                # Three written question blocks
                wq1_display = gr.HTML(value="")
                wa1_input = gr.Textbox(
                    label="Your Answer (Question 1)",
                    lines=8,
                    placeholder="Write your answer here (150-300 words recommended)…",
                )
                wq2_display = gr.HTML(value="")
                wa2_input = gr.Textbox(
                    label="Your Answer (Question 2)",
                    lines=8,
                    placeholder="Write your answer here (150-300 words recommended)…",
                )
                wq3_display = gr.HTML(value="")
                wa3_input = gr.Textbox(
                    label="Your Answer (Question 3)",
                    lines=8,
                    placeholder="Write your answer here (150-300 words recommended)…",
                )

                submit_written_btn = gr.Button(
                    "📨 Submit Written Assessment",
                    elem_classes=["primary-btn"],
                    size="lg",
                )
                written_result_status = gr.HTML(value="")

                def load_written_questions(state):
                    if not state.get("mcq_submitted"):
                        return (
                            '<div class="warning-box">⚠️ Please complete the MCQ interview first.</div>',
                            "", "", "", "", "", "",
                            state,
                        )
                    if state.get("written_submitted"):
                        return (
                            '<div class="success-box">✅ Written assessment already submitted. '
                            'Go to the Performance Report tab.</div>',
                            "", "", "", "", "", "",
                            state,
                        )

                    wqs = state.get("written_questions", [])
                    if not wqs:
                        # Try generating again
                        try:
                            profile = state.get("profile")
                            icfg = state.get("config")
                            wqs = answer_evaluator.generate_written_questions(profile, icfg)
                            state["written_questions"] = wqs
                        except Exception:
                            return (
                                '<div class="error-box">❌ Could not generate written questions.</div>',
                                "", "", "", "", "", "",
                                state,
                            )

                    saved_answers = state.get("written_answers", {})
                    displays = []
                    saved_texts = []
                    for i, wq in enumerate(wqs[:3]):
                        displays.append(
                            f'<div class="question-card">'
                            f'<div class="question-number">Written Question {i+1} of 3</div>'
                            f'<div style="margin-bottom:8px;">'
                            f'<span class="badge badge-info">{wq.question_type}</span> '
                            f'<span class="badge" style="background:#f1f5f9;color:#475569;">'
                            f'{wq.word_guide}</span></div>'
                            f'<div class="question-text">{wq.question_text}</div></div>'
                        )
                        saved_texts.append(saved_answers.get(wq.id, ""))

                    # Pad if less than 3
                    while len(displays) < 3:
                        displays.append("")
                        saved_texts.append("")

                    return (
                        '<div class="info-box">ℹ️ Answer all three questions below, then submit.</div>',
                        displays[0], saved_texts[0],
                        displays[1], saved_texts[1],
                        displays[2], saved_texts[2],
                        state,
                    )

                tabs.select(
                    load_written_questions,
                    inputs=[session_state],
                    outputs=[
                        written_status,
                        wq1_display, wa1_input,
                        wq2_display, wa2_input,
                        wq3_display, wa3_input,
                        session_state,
                    ],
                )

                def handle_submit_written(a1, a2, a3, state):
                    if not state.get("mcq_submitted"):
                        return (
                            '<div class="error-box">❌ Complete the MCQ interview first.</div>',
                            state,
                            gr.Tabs(),
                        )
                    if state.get("written_submitted"):
                        return (
                            '<div class="warning-box">⚠️ Already submitted.</div>',
                            state,
                            gr.Tabs(),
                        )

                    wqs = state.get("written_questions", [])
                    answers_map = {}
                    answer_texts = [a1, a2, a3]
                    for i, wq in enumerate(wqs[:3]):
                        answers_map[wq.id] = answer_texts[i] if i < len(answer_texts) else ""
                    state["written_answers"] = answers_map

                    # Evaluate
                    try:
                        profile = state.get("profile")
                        icfg = state.get("config")
                        assessment = answer_evaluator.evaluate_all(
                            wqs[:3], answers_map, profile, icfg
                        )
                        state["written_assessment"] = assessment
                        state["written_submitted"] = True

                        # Generate feedback
                        try:
                            mcq_results = state.get("mcq_results")
                            # Build an InterviewSession for the feedback generator
                            temp_session = InterviewSession(
                                session_id=state.get("session_id", ""),
                                resume_profile=profile,
                                interview_config=icfg,
                                mcq_results=mcq_results,
                                written_assessment=assessment,
                                mcq_submitted=True,
                                written_submitted=True,
                            )
                            feedback = feedback_generator.generate_feedback(temp_session)
                            state["feedback_report"] = feedback

                            # Save to history
                            combined = calculate_combined_score(
                                mcq_results.accuracy, assessment.overall_score, True
                            )
                            session_manager.save_session(
                                state.get("session_id", ""),
                                {
                                    "target_role": icfg.target_role if icfg else "",
                                    "interview_type": icfg.interview_type if icfg else "",
                                    "mcq_score": mcq_results.accuracy if mcq_results else 0,
                                    "written_score": assessment.overall_score,
                                    "combined_score": combined,
                                },
                            )
                        except Exception as e:
                            # Feedback generation failed but written eval succeeded
                            print(f"Feedback generation error: {e}")

                        demo_note = " (Demo evaluation)" if config.demo_mode else ""
                        return (
                            f'<div class="success-box">✅ Written assessment evaluated!{demo_note}<br>'
                            f'Overall Written Score: <strong>{assessment.overall_score:.1f}/100</strong><br><br>'
                            f'Proceed to the <b>Performance Report</b> tab for your full results.</div>',
                            state,
                            gr.Tabs(selected=5),
                        )
                    except Exception as e:
                        return (
                            f'<div class="error-box">❌ Evaluation failed: {e}</div>',
                            state,
                            gr.Tabs(),
                        )

                submit_written_btn.click(
                    handle_submit_written,
                    inputs=[wa1_input, wa2_input, wa3_input, session_state],
                    outputs=[written_result_status, session_state, tabs],
                )

            # ─────────────────────────────────────────────────────────
            # TAB 6: PERFORMANCE REPORT
            # ─────────────────────────────────────────────────────────
            with gr.Tab("📈 Performance Report", id=5):
                gr.HTML(
                    '<div class="card"><h2 style="margin:0 0 8px 0;color:var(--text-primary);">'
                    '📈 Performance Report</h2>'
                    '<p style="color:var(--text-secondary);margin:0;">'
                    'Your comprehensive interview performance analysis with scores, '
                    'charts, and personalized improvement recommendations.</p></div>'
                )

                report_status = gr.HTML(value="")
                report_summary = gr.HTML(value="")

                with gr.Row():
                    chart_domain = gr.Plot(label="Domain Performance")
                    chart_difficulty = gr.Plot(label="Difficulty Performance")
                chart_topic = gr.Plot(label="Topic Accuracy")

                report_details = gr.HTML(value="")
                report_answers = gr.HTML(value="")

                with gr.Row():
                    download_json_btn = gr.Button(
                        "📥 Download JSON Report", elem_classes=["secondary-btn"],
                    )
                    download_pdf_btn = gr.Button(
                        "📥 Download PDF Report", elem_classes=["secondary-btn"],
                    )
                download_file = gr.File(label="Download", visible=False)

                def load_report(state):
                    mcq_results = state.get("mcq_results")
                    if mcq_results is None:
                        return (
                            '<div class="warning-box">⚠️ No interview results available. '
                            'Please complete the interview first.</div>',
                            "", None, None, None, "", "",
                        )

                    written_assessment = state.get("written_assessment")
                    feedback = state.get("feedback_report")

                    # ── Summary section ──
                    both_complete = written_assessment is not None and state.get("written_submitted")
                    combined = calculate_combined_score(
                        mcq_results.accuracy,
                        written_assessment.overall_score if written_assessment else 0,
                        both_complete,
                    )
                    label = get_performance_label(
                        combined if combined is not None else mcq_results.accuracy
                    )
                    color_cls = (
                        "score-excellent" if label == "Excellent"
                        else "score-good" if label == "Good"
                        else "score-average" if label == "Average"
                        else "score-poor"
                    )

                    summary_html = '<div class="report-section"><h3>📊 Overall Summary</h3>'
                    summary_html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:16px;margin:16px 0;">'

                    # MCQ stats
                    summary_html += (
                        f'<div class="stat-card">'
                        f'<div class="stat-value">{mcq_results.accuracy:.1f}%</div>'
                        f'<div class="stat-label">MCQ Accuracy</div></div>'
                    )
                    summary_html += (
                        f'<div class="stat-card">'
                        f'<div class="stat-value" style="color:#10b981;">{mcq_results.correct}</div>'
                        f'<div class="stat-label">Correct</div></div>'
                    )
                    summary_html += (
                        f'<div class="stat-card">'
                        f'<div class="stat-value" style="color:#ef4444;">{mcq_results.incorrect}</div>'
                        f'<div class="stat-label">Incorrect</div></div>'
                    )
                    summary_html += (
                        f'<div class="stat-card">'
                        f'<div class="stat-value" style="color:#94a3b8;">{mcq_results.unanswered}</div>'
                        f'<div class="stat-label">Unanswered</div></div>'
                    )

                    if written_assessment:
                        summary_html += (
                            f'<div class="stat-card">'
                            f'<div class="stat-value">{written_assessment.overall_score:.1f}</div>'
                            f'<div class="stat-label">Written Score</div></div>'
                        )
                    if combined is not None:
                        summary_html += (
                            f'<div class="stat-card">'
                            f'<div class="stat-value {color_cls}">{combined:.1f}%</div>'
                            f'<div class="stat-label">Combined Score</div></div>'
                        )

                    summary_html += '</div>'

                    # Scoring methodology
                    summary_html += (
                        '<div class="info-box">'
                        '<strong>Scoring Methodology:</strong><br>'
                        '• MCQ Score = Correct Answers / 20 × 100<br>'
                        '• Written Score = Mean of rubric domain scores<br>'
                    )
                    if both_complete:
                        summary_html += '• Combined Score = MCQ Score × 0.60 + Written Score × 0.40'
                    else:
                        summary_html += (
                            '• Combined score requires both MCQ and Written assessments'
                        )
                    summary_html += '</div></div>'

                    # ── Charts ──
                    domain_scores = {}
                    if feedback:
                        domain_scores = feedback.domain_scores
                    elif mcq_results.domain_accuracy:
                        for d, info in mcq_results.domain_accuracy.items():
                            if isinstance(info, dict):
                                total = info.get("total", 0)
                                correct = info.get("correct", 0)
                                domain_scores[d] = {
                                    "score": (correct / total * 100) if total > 0 else 0
                                }

                    charts = build_plotly_charts(
                        mcq_results, written_assessment, domain_scores
                    )
                    chart_d = charts.get("domain")
                    chart_diff = charts.get("difficulty")
                    chart_t = charts.get("topic")

                    # ── Details section ──
                    details_html = ""

                    # Strengths & Weaknesses
                    if feedback:
                        if feedback.strengths:
                            details_html += '<div class="report-section"><h3>💪 Strengths</h3><ul>'
                            for s in feedback.strengths:
                                details_html += f"<li style='margin:6px 0;color:var(--text-secondary);'>{s}</li>"
                            details_html += "</ul></div>"
                        if feedback.weaknesses:
                            details_html += '<div class="report-section"><h3>📌 Areas for Improvement</h3><ul>'
                            for w in feedback.weaknesses:
                                details_html += f"<li style='margin:6px 0;color:var(--text-secondary);'>{w}</li>"
                            details_html += "</ul></div>"
                        if feedback.improvement_plan:
                            plan = feedback.improvement_plan
                            details_html += '<div class="report-section"><h3>🎯 Personalized Improvement Plan</h3>'
                            if "priority_areas" in plan:
                                for pa in plan["priority_areas"]:
                                    if isinstance(pa, dict):
                                        details_html += (
                                            f'<div style="margin:10px 0;padding:12px;background:#f8fafc;'
                                            f'border-radius:8px;border-left:3px solid var(--primary);">'
                                            f'<strong>{pa.get("area", "")}</strong><br>'
                                            f'<span style="color:var(--text-secondary);">'
                                            f'{pa.get("current_level", "")}</span>'
                                        )
                                        if pa.get("action_items"):
                                            details_html += "<ul>"
                                            for ai_item in pa["action_items"]:
                                                details_html += f"<li>{ai_item}</li>"
                                            details_html += "</ul>"
                                        details_html += "</div>"
                                    elif isinstance(pa, str):
                                        details_html += f"<p>• {pa}</p>"
                            if "concepts_to_revise" in plan:
                                details_html += "<p><strong>📚 Concepts to Revise:</strong> "
                                details_html += ", ".join(plan["concepts_to_revise"]) + "</p>"
                            if "practice_exercises" in plan:
                                details_html += "<p><strong>🏋️ Practice Exercises:</strong></p><ul>"
                                for ex in plan["practice_exercises"]:
                                    details_html += f"<li>{ex}</li>"
                                details_html += "</ul>"
                            if "recommended_next_interview" in plan:
                                details_html += (
                                    f'<p><strong>➡️ Recommended Next:</strong> '
                                    f'{plan["recommended_next_interview"]}</p>'
                                )
                            details_html += "</div>"

                    # Written assessment details
                    if written_assessment and written_assessment.evaluations:
                        details_html += '<div class="report-section"><h3>✍️ Written Assessment Details</h3>'
                        for ev in written_assessment.evaluations:
                            details_html += (
                                f'<div style="margin:12px 0;padding:16px;background:#f8fafc;'
                                f'border-radius:8px;border:1px solid #e2e8f0;">'
                                f'<strong>Q: {ev.question_text}</strong><br>'
                                f'<div style="margin:8px 0;padding:8px;background:#fff;border-radius:6px;'
                                f'border:1px solid #e2e8f0;font-style:italic;color:var(--text-secondary);">'
                                f'{ev.answer_text[:500]}{"…" if len(ev.answer_text) > 500 else ""}</div>'
                                f'<strong>Score: {ev.overall_score:.0f}/100</strong>'
                            )
                            if ev.rubric_scores:
                                details_html += '<div style="margin-top:8px;display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:8px;">'
                                for rs in ev.rubric_scores:
                                    sc = rs.score
                                    sc_color = "#10b981" if sc >= 75 else "#f59e0b" if sc >= 50 else "#ef4444"
                                    details_html += (
                                        f'<div style="padding:8px;background:#fff;border-radius:6px;'
                                        f'border:1px solid #e2e8f0;">'
                                        f'<div style="font-weight:600;font-size:0.85rem;">{rs.domain}</div>'
                                        f'<div style="color:{sc_color};font-weight:700;font-size:1.1rem;">'
                                        f'{sc:.0f}/100</div></div>'
                                    )
                                details_html += '</div>'
                            if ev.grammar_errors:
                                details_html += '<div style="margin-top:8px;"><strong>Grammar Corrections:</strong><ul>'
                                for ge in ev.grammar_errors:
                                    details_html += (
                                        f'<li style="margin:4px 0;">'
                                        f'<span style="color:#ef4444;text-decoration:line-through;">{ge.original}</span> → '
                                        f'<span style="color:#10b981;">{ge.corrected}</span>'
                                        f'<br><span style="color:var(--text-muted);font-size:0.85rem;">{ge.explanation}</span></li>'
                                    )
                                details_html += '</ul></div>'
                            details_html += "</div>"
                        details_html += "</div>"

                    # ── Answer review ──
                    answers_html = '<div class="report-section"><h3>📝 MCQ Answer Review</h3>'
                    mcq_set = state.get("mcq_set")
                    user_answers = state.get("user_answers", {})
                    if mcq_set:
                        for i, q in enumerate(mcq_set.questions):
                            user_ans = user_answers.get(q.id, -1)
                            is_correct = user_ans == q.correct_answer
                            status_icon = "✅" if is_correct else ("❌" if user_ans >= 0 else "⬜")
                            user_text = q.options[user_ans] if 0 <= user_ans < len(q.options) else "Not answered"
                            correct_text = q.options[q.correct_answer] if 0 <= q.correct_answer < len(q.options) else "N/A"

                            bg = "#ecfdf5" if is_correct else ("#fef2f2" if user_ans >= 0 else "#f8fafc")
                            border_color = "#a7f3d0" if is_correct else ("#fecaca" if user_ans >= 0 else "#e2e8f0")

                            answers_html += (
                                f'<div style="margin:8px 0;padding:14px;background:{bg};'
                                f'border-radius:8px;border:1px solid {border_color};">'
                                f'<div style="display:flex;justify-content:space-between;align-items:start;">'
                                f'<div style="flex:1;">'
                                f'<strong>{status_icon} Q{i+1}.</strong> {q.question_text}<br>'
                                f'<span style="color:var(--text-secondary);font-size:0.9rem;">'
                                f'Your answer: <strong>{user_text}</strong></span><br>'
                            )
                            if not is_correct:
                                answers_html += (
                                    f'<span style="color:#059669;font-size:0.9rem;">'
                                    f'Correct answer: <strong>{correct_text}</strong></span><br>'
                                )
                            answers_html += (
                                f'<span style="color:var(--text-muted);font-size:0.85rem;font-style:italic;">'
                                f'{q.explanation}</span>'
                                f'</div>'
                                f'<div><span class="badge badge-{q.difficulty}">{q.difficulty.upper()}</span></div>'
                                f'</div></div>'
                            )
                    answers_html += "</div>"

                    return (
                        "", summary_html,
                        chart_d, chart_diff, chart_t,
                        details_html, answers_html,
                    )

                tabs.select(
                    load_report,
                    inputs=[session_state],
                    outputs=[
                        report_status, report_summary,
                        chart_domain, chart_difficulty, chart_topic,
                        report_details, report_answers,
                    ],
                )

                def handle_download_json(state):
                    feedback = state.get("feedback_report")
                    mcq_results = state.get("mcq_results")
                    if mcq_results is None:
                        return gr.File(visible=False)
                    try:
                        if feedback:
                            json_str = report_generator.generate_json_report(feedback)
                        else:
                            # Create a minimal FeedbackReport for export
                            minimal_report = FeedbackReport(
                                session_id=state.get("session_id", ""),
                                timestamp=datetime.now().isoformat(),
                                mcq_results=mcq_results,
                                mcq_score=mcq_results.accuracy,
                            )
                            json_str = report_generator.generate_json_report(minimal_report)
                        path = report_generator.save_report(
                            json_str, f"interview_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "json"
                        )
                        return gr.File(value=path, visible=True)
                    except Exception as e:
                        print(f"JSON export error: {e}")
                        return gr.File(visible=False)

                def handle_download_pdf(state):
                    feedback = state.get("feedback_report")
                    mcq_results = state.get("mcq_results")
                    if mcq_results is None:
                        return gr.File(visible=False)
                    try:
                        if feedback:
                            report_obj = feedback
                        else:
                            report_obj = FeedbackReport(
                                session_id=state.get("session_id", ""),
                                timestamp=datetime.now().isoformat(),
                                mcq_results=mcq_results,
                                mcq_score=mcq_results.accuracy,
                            )
                        pdf_path = os.path.join(
                            "reports",
                            f"interview_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        )
                        path = report_generator.generate_pdf_report(report_obj, pdf_path)
                        return gr.File(value=path, visible=True)
                    except Exception as e:
                        print(f"PDF export error: {e}")
                        return gr.File(visible=False)

                download_json_btn.click(
                    handle_download_json,
                    inputs=[session_state],
                    outputs=[download_file],
                )
                download_pdf_btn.click(
                    handle_download_pdf,
                    inputs=[session_state],
                    outputs=[download_file],
                )

            # ─────────────────────────────────────────────────────────
            # TAB 7: INTERVIEW HISTORY
            # ─────────────────────────────────────────────────────────
            with gr.Tab("📋 History", id=6):
                gr.HTML(
                    '<div class="card"><h2 style="margin:0 0 8px 0;color:var(--text-primary);">'
                    '📋 Interview History</h2>'
                    '<p style="color:var(--text-secondary);margin:0;">'
                    'View your past interview sessions and track your progress over time.</p></div>'
                )

                history_html = gr.HTML(value="")
                with gr.Row():
                    refresh_history_btn = gr.Button(
                        "🔄 Refresh", elem_classes=["secondary-btn"],
                    )
                    clear_history_btn = gr.Button(
                        "🗑️ Clear All History", elem_classes=["danger-btn"],
                    )
                history_action_status = gr.HTML(value="")

                def load_history():
                    if not config.enable_history:
                        return (
                            '<div class="info-box">ℹ️ Interview history is disabled. '
                            'Set ENABLE_HISTORY=true in your .env file to enable it.</div>'
                        )
                    sessions = session_manager.get_all_sessions()
                    if not sessions:
                        return (
                            '<div class="empty-state">'
                            '<div class="empty-state-icon">📋</div>'
                            '<div class="empty-state-text">No interview history yet. '
                            'Complete an interview to see it here.</div></div>'
                        )
                    html = '<div style="overflow-x:auto;">'
                    html += ('<table style="width:100%;border-collapse:collapse;'
                             'background:white;border-radius:8px;overflow:hidden;'
                             'box-shadow:0 1px 3px rgba(0,0,0,0.1);">')
                    html += ('<thead><tr style="background:#f1f5f9;">'
                             '<th style="padding:12px 16px;text-align:left;font-size:0.85rem;'
                             'color:var(--text-secondary);text-transform:uppercase;">Date</th>'
                             '<th style="padding:12px 16px;text-align:left;font-size:0.85rem;'
                             'color:var(--text-secondary);text-transform:uppercase;">Role</th>'
                             '<th style="padding:12px 16px;text-align:left;font-size:0.85rem;'
                             'color:var(--text-secondary);text-transform:uppercase;">Type</th>'
                             '<th style="padding:12px 16px;text-align:center;font-size:0.85rem;'
                             'color:var(--text-secondary);text-transform:uppercase;">MCQ</th>'
                             '<th style="padding:12px 16px;text-align:center;font-size:0.85rem;'
                             'color:var(--text-secondary);text-transform:uppercase;">Written</th>'
                             '<th style="padding:12px 16px;text-align:center;font-size:0.85rem;'
                             'color:var(--text-secondary);text-transform:uppercase;">Combined</th>'
                             '<th style="padding:12px 16px;text-align:center;font-size:0.85rem;'
                             'color:var(--text-secondary);text-transform:uppercase;">Rating</th>'
                             '</tr></thead><tbody>')
                    for s in sessions:
                        mcq_s = s.get("mcq_score", 0)
                        written_s = s.get("written_score", 0)
                        combined_s = s.get("combined_score")
                        label = get_performance_label(combined_s if combined_s else mcq_s)
                        label_color = (
                            "#059669" if label == "Excellent"
                            else "#2563eb" if label == "Good"
                            else "#d97706" if label == "Average"
                            else "#dc2626"
                        )
                        html += (
                            f'<tr style="border-bottom:1px solid #e2e8f0;">'
                            f'<td style="padding:12px 16px;">{s.get("created_at", "")[:10]}</td>'
                            f'<td style="padding:12px 16px;font-weight:500;">{s.get("target_role", "N/A")}</td>'
                            f'<td style="padding:12px 16px;">{s.get("interview_type", "N/A").title()}</td>'
                            f'<td style="padding:12px 16px;text-align:center;font-weight:600;">{mcq_s:.0f}%</td>'
                            f'<td style="padding:12px 16px;text-align:center;font-weight:600;">'
                            f'{written_s:.0f}%</td>'
                            f'<td style="padding:12px 16px;text-align:center;font-weight:600;">'
                            f'{combined_s:.0f}%' if combined_s else 'N/A'
                            f'</td>'
                            f'<td style="padding:12px 16px;text-align:center;font-weight:700;'
                            f'color:{label_color};">{label}</td>'
                            f'</tr>'
                        )
                    html += "</tbody></table></div>"
                    return html

                def handle_clear_history():
                    session_manager.delete_all_sessions()
                    return (
                        load_history(),
                        '<div class="success-box">✅ All history cleared.</div>',
                    )

                refresh_history_btn.click(load_history, outputs=[history_html])
                clear_history_btn.click(
                    handle_clear_history,
                    outputs=[history_html, history_action_status],
                )
                tabs.select(load_history, outputs=[history_html])

    return app


# ═══════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    # Force UTF-8 stdout on Windows to avoid cp1252 encoding errors
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 60)
    print("  AI Interview Practice Platform")
    print("=" * 60)
    if config.demo_mode:
        print("  [!] DEMO MODE - No OpenAI API key configured.")
        print("      Set OPENAI_API_KEY in .env for full AI features.")
    else:
        print(f"  [OK] AI Mode - Using model: {config.openai_model}")
    print(f"  Server: http://{config.gradio_server_name}:{config.gradio_server_port}")
    print("=" * 60)

    app = create_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=config.gradio_server_port,
        share=True,
        show_error=True,
        css=CUSTOM_CSS,
        theme=gr.themes.Soft(
            primary_hue="indigo",
            secondary_hue="cyan",
            neutral_hue="slate",
            font=gr.themes.GoogleFont("Inter"),
        ),
    )

