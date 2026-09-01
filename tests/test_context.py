from codeloop.context import ContextManager


def test_tool_call_arguments_are_compacted_in_context():
    context = ContextManager("Create a file.")
    context.add_assistant_tool_call("write_file", {"path": "big.py", "content": "x" * 5000})

    snapshot = context.snapshot()

    assert snapshot[-1]["tool_call"]["arguments"]["content"] == "<5000 chars>"
