import logging

import importlib

_a_sync_function = importlib.import_module("a_sync.a_sync.function")
from a_sync.a_sync.function import ASyncFunction, im_a_fuckin_pro_dont_worry


class BadSignatureCallable:
    __name__ = "bad_signature_callable"

    def __call__(self, value):
        return value

    @property
    def __signature__(self):
        raise TypeError("unsupported callable")


def _trigger_argspec_warning() -> None:
    ASyncFunction(BadSignatureCallable())


def test_im_a_fuckin_pro_dont_worry_suppresses_warnings(caplog) -> None:
    logger_name = _a_sync_function.__name__
    caplog.set_level(logging.WARNING, logger=logger_name)

    _trigger_argspec_warning()
    messages = [record.getMessage() for record in caplog.records if record.name == logger_name]
    assert any("inspect." in message and "does not support" in message for message in messages)
    assert "we will allow you to proceed but cannot guarantee things will work" in messages
    assert "hopefully you know what you're doing..." in messages

    caplog.clear()
    with im_a_fuckin_pro_dont_worry():
        _trigger_argspec_warning()
    messages = [record.getMessage() for record in caplog.records if record.name == logger_name]
    assert not messages

    caplog.clear()
    _trigger_argspec_warning()
    messages = [record.getMessage() for record in caplog.records if record.name == logger_name]
    assert any("inspect." in message and "does not support" in message for message in messages)
