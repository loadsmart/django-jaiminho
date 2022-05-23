import pytest

from jaiminho.kwargs_handler import format_kwargs, load_kwargs

from jaiminho_django_project.send import InternalDecoder


@pytest.mark.parametrize(
    ("parameters", "formatted_kwargs"),
    (
        (
            (
                {
                    "decoder": InternalDecoder,
                    "x": 2,
                },
                "jaiminho_django_project.send.InternalDecoder decoder=NotUsed|int x=2",
            )
        ),
        (
            {
                "decoder": InternalDecoder,
                "x": 2.0,
            },
            "jaiminho_django_project.send.InternalDecoder decoder=NotUsed|float x=2.0",
        ),
    ),
)
def test_format_kwargs(parameters, formatted_kwargs):
    assert format_kwargs(**parameters) == formatted_kwargs


@pytest.mark.parametrize(
    ("parameters", "formatted_kwargs"),
    (
        (
            (
                {
                    "decoder": InternalDecoder,
                    "x": 2,
                },
                "jaiminho_django_project.send.InternalDecoder decoder=NotUsed|int x=2",
            )
        ),
        (
            {
                "decoder": InternalDecoder,
                "x": 2.0,
            },
            "jaiminho_django_project.send.InternalDecoder decoder=NotUsed|float x=2.0",
        ),
    ),
)
def test_load_kwargs(parameters, formatted_kwargs):
    loaded_parameters = load_kwargs(formatted_kwargs)
    assert loaded_parameters.keys() == parameters.keys()
    for loaded_parameter, parameter in zip(
        loaded_parameters.values(), parameters.values()
    ):
        assert str(loaded_parameter) == str(parameter)
        assert type(loaded_parameter) == type(parameter)
