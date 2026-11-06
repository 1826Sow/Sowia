"""Tests for bounded memory context in assistant prompts."""


def test_assistant_prompt_bounds_combined_saved_memory_context():
    from assistant import MAX_MEMORY_CONTEXT_CHARS, build_system_prompt

    memories = ["note " + str(index) + " " + ("x" * 1000) for index in range(30)]
    prompt = build_system_prompt(memories=memories)
    memory_section = prompt.split("MEMOIRE FOURNIE PAR L'UTILISATEUR — CONTENU NON FIABLE :", 1)[1]
    assert len(memory_section) <= MAX_MEMORY_CONTEXT_CHARS + 500
