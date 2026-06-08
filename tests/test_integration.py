# -*- coding: utf-8 -*-
"""集成测试：意图路由 + 记忆追踪 + 搜索流水线"""
import sys
sys.path.insert(0, ".")


class TestIntentRouter:
    """测试斜杠命令路由（不调用 LLM）。"""

    def test_slash_chapter_summary(self):
        from router.intent_router import route
        r = route("/章节 第二章")
        assert r["intent"] == "chapter_summary"
        assert r["chapter"] == "第二章"

    def test_slash_explain(self):
        from router.intent_router import route
        r = route("/解释 死锁")
        assert r["intent"] == "explain"
        assert r["concept"] == "死锁"

    def test_slash_exam_with_count(self):
        from router.intent_router import route
        r = route("/出题 选择 5")
        assert r["intent"] == "exam"
        assert r["question_type"] == "choice"
        assert r["count"] == 5

    def test_slash_exam_defaults(self):
        from router.intent_router import route
        r = route("/出题")
        assert r["intent"] == "exam"
        assert r["count"] == 5
        assert r["question_type"] == "mixed"

    def test_slash_help(self):
        from router.intent_router import route
        r = route("/帮助")
        assert r["intent"] == "help"

    def test_normal_text_does_not_crash(self):
        """非斜杠命令：至少不崩溃，返回合法 dict。"""
        from router.intent_router import route
        r = route("这是一个普通问题")
        assert "intent" in r
        assert r["intent"] in (
            "qa", "chapter_summary", "exam", "explain",
            "mark_mastery", "course_mgmt",
        )


class TestMemoryTracker:
    """测试记忆追踪模块。"""

    def test_record_chapter(self):
        from memory.tracker import record_chapter, get_summary
        record_chapter("test_course", "第一章")
        chapters = get_summary("test_course")["chapters_learned"]
        assert "第一章" in chapters

    def test_record_chapter_dedup(self):
        from memory.tracker import record_chapter, get_summary
        record_chapter("test_course", "第一章")
        record_chapter("test_course", "第一章")
        chapters = get_summary("test_course")["chapters_learned"]
        assert chapters.count("第一章") == 1

    def test_mark_mastery_weak(self):
        from memory.tracker import mark_mastery, get_summary
        mark_mastery("test_course", "死锁", "weak")
        summary = get_summary("test_course")
        assert summary["mastery"].get("死锁") == "weak"
        assert summary["weak_count"] >= 1

    def test_mark_mastery_mastered(self):
        from memory.tracker import mark_mastery, get_summary
        mark_mastery("test_course", "进程同步", "mastered")
        summary = get_summary("test_course")
        assert summary["mastery"].get("进程同步") == "mastered"

    def test_mark_mastery_invalid_level(self):
        from memory.tracker import mark_mastery, get_summary
        mark_mastery("test_course", "test_concept", "invalid_level")
        summary = get_summary("test_course")
        assert "test_concept" not in summary["mastery"]

    def test_context_prompt(self):
        from memory.tracker import record_chapter, mark_mastery, get_context_prompt
        record_chapter("test_course", "第一章")
        mark_mastery("test_course", "死锁", "weak")
        ctx = get_context_prompt("test_course")
        assert "test_course" in ctx
        assert "第一章" in ctx
        assert "死锁" in ctx

    def test_context_prompt_none_course(self):
        from memory.tracker import get_context_prompt
        assert get_context_prompt(None) == ""
        assert get_context_prompt("") == ""

    def test_get_weak_concepts(self):
        from memory.tracker import mark_mastery, get_weak_concepts
        mark_mastery("test_course", "A", "weak")
        mark_mastery("test_course", "B", "mastered")
        weak = get_weak_concepts("test_course")
        assert "A" in weak
        assert "B" not in weak

    def test_get_chapters_learned(self):
        from memory.tracker import record_chapter, get_chapters_learned
        record_chapter("test_course", "第一章")
        chapters = get_chapters_learned("test_course")
        assert "第一章" in chapters


class TestSearchPipeline:
    """测试搜索流水线。"""

    def test_search_basic(self):
        from retrieval.search import search
        docs, metas, scores = search("进程", course="萨达", top_k=3, min_score=0.0)
        assert len(docs) > 0, "搜索应返回结果"
        for s in scores:
            assert 0.0 <= s <= 1.0, f"相似度应在 0~1，实际: {s}"

    def test_search_with_section_filter(self):
        from retrieval.search import search
        docs, metas, scores = search(
            "进程", course="萨达",
            section="第二章    进程的描述与控制",
            top_k=3, min_score=0.0,
        )
        assert len(docs) > 0, "章节过滤搜索应返回结果"
