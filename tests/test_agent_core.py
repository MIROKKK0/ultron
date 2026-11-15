from backend.agent_core import (
    SELF_MODEL,
    improvement_proposal,
    review_response,
    system_instructions,
)


def test_self_model_is_honest_about_limits():
    model = SELF_MODEL.public_dict()
    assert model["name"] == "ULTRON"
    assert any("não treina pesos" in item for item in model["limitations"])


def test_system_instructions_include_relevant_memory():
    prompt = system_instructions(["Prefere respostas em português"])
    assert "Prefere respostas em português" in prompt
    assert "Não modifique o próprio código de produção" in prompt


def test_review_is_explicitly_heuristic():
    result = review_response("resolver bug", "A solução é esta.")
    assert result["passed"] is True
    assert "não comprova" in result["note"]


def test_improvement_proposal_never_applies_itself():
    proposal = improvement_proposal("O endpoint /chat está lento")
    assert proposal["status"] == "proposal_only"
    assert proposal["production_changes"] is False
    assert "executar testes" in proposal["plan"][3]


def test_empty_improvement_problem_is_rejected():
    try:
        improvement_proposal(" ")
    except ValueError:
        return
    raise AssertionError("Expected empty proposal to fail")
