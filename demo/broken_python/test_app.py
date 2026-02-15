"""Tests for the calculator module."""

from app import add, subtract, multiply, divide


def test_add():
    assert add(2, 3) == 5


def test_subtract():
    assert subtract(10, 4) == 6


def test_multiply():
    assert multiply(3, 4) == 12


def test_divide():
    assert divide(10, 3) == 3  # Fails: 10/3 = 3.333..., expects 3


def test_divide_zero():
    try:
        divide(1, 0)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
