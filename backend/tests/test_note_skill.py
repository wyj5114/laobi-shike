"""笔记生成 Skill 的结构与注入测试。"""
from app.gpt.prompt_builder import generate_base_prompt, load_note_skill
from app.gpt.style_prompts import STYLE_PROMPTS


def test_note_skill_uses_langgpt_structure():
    skill = load_note_skill()
    assert "# Role:" in skill
    assert "## Profile" in skill
    assert "## Goal" in skill
    assert "## Skills" in skill
    assert "## Rules" in skill
    assert "## Workflow" in skill
    assert "## Output Template" in skill


def test_note_skill_is_injected_only_when_selected():
    prompt = generate_base_prompt(
        title="测试课程",
        segment_text="00:00 这是转写内容",
        tags=["测试"],
        style="skill",
    )
    assert "视频笔记生成 Skill" in prompt
    assert "课程笔记整理师" in prompt
    assert "公式必须用 LaTeX" in prompt


def test_note_skill_is_not_default():
    prompt = generate_base_prompt(
        title="测试课程",
        segment_text="00:00 这是转写内容",
        tags=["测试"],
        style="detailed",
    )
    assert "视频笔记生成 Skill" not in prompt


def test_original_bilinote_style_mapping_is_restored():
    expected = {
        "minimal",
        "detailed",
        "academic",
        "tutorial",
        "xiaohongshu",
        "life_journal",
        "task_oriented",
        "business",
        "meeting_minutes",
        "skill",
    }
    assert expected.issubset(STYLE_PROMPTS.keys())
    assert STYLE_PROMPTS["minimal"].startswith("1. **精简信息**")
    assert STYLE_PROMPTS["detailed"].startswith("2. **详细记录**")
    assert STYLE_PROMPTS["academic"].startswith("3. **学术风格**")
    assert STYLE_PROMPTS["tutorial"].startswith("9.**教程笔记**")
    assert "课程笔记（Skill）" in STYLE_PROMPTS["skill"]
