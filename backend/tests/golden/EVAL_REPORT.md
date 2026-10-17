# Evaluation report (B7)

- Generated: `2026-10-17T11:51:23.637975+00:00`
- Result: **PASS** (exit code 0)

## Scope

- Golden main-query IDs
- API auth (401 / 404 cross-workspace)
- Viewer read access
- Search does not return notes/email
- Draft lifecycle + idempotent send
- Agent main query + empty-search anti-hallucination (if GROQ_API_KEY set)

## Pytest output

```
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.7.0 -- /home/khaled/Downloads/ai-business-assistant/backend/.venv/bin/python
cachedir: .pytest_cache
rootdir: /home/khaled/Downloads/ai-business-assistant/backend
configfile: pyproject.toml
plugins: logfire-5.2.0, anyio-4.15.1, platformdirs-4.13.0, asyncio-1.4.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
collecting ... collected 24 items

tests/test_eval_suite.py::test_golden_main_query_ids PASSED              [  4%]
tests/test_eval_suite.py::test_api_main_query_matches_golden PASSED      [  8%]
tests/test_eval_suite.py::test_cross_workspace_404 PASSED                [ 12%]
tests/test_eval_suite.py::test_unauthenticated_401 PASSED                [ 16%]
tests/test_eval_suite.py::test_viewer_can_read_main_query PASSED         [ 20%]
tests/test_eval_suite.py::test_injection_customer_search_does_not_leak_notes PASSED [ 25%]
tests/test_eval_suite.py::test_agent_main_query_tool_and_ids PASSED      [ 29%]
tests/test_eval_suite.py::test_agent_empty_search_no_hallucinated_emails PASSED [ 33%]
tests/test_eval_suite.py::test_agent_injection_prompt PASSED             [ 37%]
tests/test_main_query.py::test_month_boundaries PASSED                   [ 41%]
tests/test_main_query.py::test_main_query_edge_cases PASSED              [ 45%]
tests/test_main_query.py::test_viewer_can_run_main_query PASSED          [ 50%]
tests/test_main_query.py::test_permissions_map PASSED                    [ 54%]
tests/test_main_query.py::test_search_does_not_return_notes_or_email PASSED [ 58%]
tests/test_api_auth.py::test_health PASSED                               [ 62%]
tests/test_api_auth.py::test_login_success PASSED                        [ 66%]
tests/test_api_auth.py::test_login_fail PASSED                           [ 70%]
tests/test_api_auth.py::test_me_without_token PASSED                     [ 75%]
tests/test_api_auth.py::test_me_with_token PASSED                        [ 79%]
tests/test_api_auth.py::test_main_query_authenticated PASSED             [ 83%]
tests/test_api_auth.py::test_foreign_customer_returns_404 PASSED         [ 87%]
tests/test_drafts.py::test_draft_lifecycle_and_idempotent_send PASSED    [ 91%]
tests/test_drafts.py::test_viewer_cannot_create_draft PASSED             [ 95%]
tests/test_drafts.py::test_forced_failure PASSED                         [100%]

============================== 24 passed in 9.86s ==============================
```
